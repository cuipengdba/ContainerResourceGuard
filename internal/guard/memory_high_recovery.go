package guard

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

const memoryHighBackoff = 10 * time.Minute
const memoryHighHistoryLimit = 16

var errMemoryHighCancelled = errors.New("memory.high recovery cancelled")

func CancelMemoryHighRecovery(err error) error {
	if err == nil {
		return nil
	}
	return fmt.Errorf("%w: %s", errMemoryHighCancelled, err)
}

type MemoryHighEvent struct {
	TimeUTC    string `json:"time_utc"`
	Generation uint64 `json:"generation"`
	Expected   string `json:"expected"`
	Reason     string `json:"reason"`
}

type MemoryHighHistory struct {
	Verified    string            `json:"verified"`
	LastAttempt string            `json:"last_attempt,omitempty"`
	Events      []MemoryHighEvent `json:"events,omitempty"`
}

func (h MemoryHighHistory) valid() bool {
	if _, err := strconv.ParseUint(h.Verified, 10, 64); err != nil || len(h.Events) > memoryHighHistoryLimit {
		return false
	}
	if h.LastAttempt != "" {
		if _, err := time.Parse(time.RFC3339Nano, h.LastAttempt); err != nil {
			return false
		}
	}
	for _, event := range h.Events {
		_, timeErr := time.Parse(time.RFC3339Nano, event.TimeUTC)
		_, valueErr := strconv.ParseUint(event.Expected, 10, 64)
		if timeErr != nil || valueErr != nil || eventReason(event.Reason) != event.Reason || !strings.HasPrefix(event.Reason, "memory_high_") {
			return false
		}
	}
	return true
}

type memoryHighJob struct {
	done    chan struct{}
	initial Status
	final   ItemStatus
	journal Journal
	started time.Time
}

func (e *Engine) MemoryHighRecoveryDone() <-chan struct{} {
	if e.highJob == nil {
		return nil
	}
	return e.highJob.done
}

// While the job owns the journal, the check loop is free to publish status
// and receive control requests. Only this loop adopts the completed journal.
func (e *Engine) PollMemoryHighRecovery() (Status, bool) {
	job := e.highJob
	if job == nil {
		return Status{}, false
	}
	status := job.initial
	status.TimeUTC = time.Now().UTC().Format(time.RFC3339)
	select {
	case <-job.done:
		e.Journal = job.journal
		e.highJob = nil
		status.Items[0] = job.final
		status.State = job.final.State
		if status.State == "applied" {
			status.State = "managed"
		} else {
			status.State = "degraded"
		}
	default:
		if time.Since(job.started) >= 5*time.Second {
			status.Items[0] = highItem(status.Items[0].Setting, "conflict", "memory_high_recovery_slow", "recovery has not finished; journal and single writer remain reserved")
		}
	}
	return status, true
}

func highItem(setting Setting, state, reason, detail string) ItemStatus {
	return ItemStatus{Setting: setting, State: state, ReasonCode: reason, Detail: detail}
}

// ReconcileLive adds one narrowly scoped transaction to the regular loop.
// The proof, existing journal entry and current plan must all agree.
func (e *Engine) ReconcileLive(p Plan, generation uint64, recheck func() error) Status {
	if status, busy := e.PollMemoryHighRecovery(); busy {
		return status
	}
	if !e.Config.MemoryHighRecovery || e.Config.Mode != "enforce" {
		return e.Reconcile(p)
	}
	for _, setting := range p.Settings {
		if setting.File != "memory.high" {
			continue
		}
		mutation := e.Journal.Mutations[setting.Key()]
		if mutation == nil || mutation.Conflict || mutation.HighRecovery == nil {
			break
		}
		current, err := e.current(setting)
		if err != nil || current != "max" {
			break
		}
		history := mutation.HighRecovery
		if e.Config.MemoryHighPaused && mutation.Pending == "" &&
			history.Verified == mutation.Applied && mutation.Applied != "max" {
			item := highItem(setting, "conflict", "memory_high_recovery_paused", "memory.high is max; automatic recovery is paused")
			return e.reconcile(p, &item)
		}
		if mutation.Pending == "" && (history.Verified != mutation.Applied || mutation.Applied == "max") {
			break
		}
		return e.startMemoryHighRecovery(p, setting, generation, recheck)
	}
	return e.Reconcile(p)
}

func (e *Engine) startMemoryHighRecovery(p Plan, setting Setting, generation uint64, recheck func() error) Status {
	worker := *e
	worker.Journal.Mutations = make(map[string]*Mutation, len(e.Journal.Mutations))
	for key, mutation := range e.Journal.Mutations {
		copyMutation := *mutation
		if mutation.HighRecovery != nil {
			history := *mutation.HighRecovery
			history.Events = append([]MemoryHighEvent(nil), history.Events...)
			copyMutation.HighRecovery = &history
		}
		worker.Journal.Mutations[key] = &copyMutation
	}
	status := Status{TimeUTC: time.Now().UTC().Format(time.RFC3339), Mode: e.Config.Mode, State: "degraded", Plan: p,
		Items: []ItemStatus{highItem(setting, "pending", "memory_high_recovery_started", "detected memory.high drift to max; verifying recovery conditions")}}
	job := &memoryHighJob{initial: status, done: make(chan struct{}), started: time.Now()}
	e.highJob = job
	go func() {
		defer close(job.done)
		job.final = worker.recoverMemoryHigh(setting, generation, recheck)
		job.journal = worker.Journal
	}()
	// Polling mutates its own item slice, including the final result.
	status.Items = append([]ItemStatus(nil), status.Items...)
	return status
}

func (e *Engine) recoverMemoryHigh(setting Setting, generation uint64, recheck func() error) ItemStatus {
	mutation := e.Journal.Mutations[setting.Key()]
	history := mutation.HighRecovery
	now := time.Now
	if e.Now != nil {
		now = e.Now
	}
	expected := history.Verified
	record := func(reason string) {
		history.Events = append(history.Events, MemoryHighEvent{
			TimeUTC: now().UTC().Format(time.RFC3339Nano), Generation: generation, Expected: expected, Reason: reason,
		})
		if len(history.Events) > memoryHighHistoryLimit {
			history.Events = history.Events[len(history.Events)-memoryHighHistoryLimit:]
		}
	}
	finish := func(state, reason, detail string) ItemStatus {
		if state == "conflict" {
			mutation.Conflict = true
		}
		record(reason)
		if err := e.save(); err != nil {
			mutation.Conflict = true
			return highItem(setting, "conflict", "memory_high_recovery_failed", detail+"; cannot persist journal: "+err.Error())
		}
		return highItem(setting, state, reason, detail)
	}
	for _, entry := range e.Journal.Mutations {
		if entry.Pending != "" {
			return finish("conflict", "memory_high_recovery_blocked", "unresolved journal intent; external value retained")
		}
	}
	if last, err := time.Parse(time.RFC3339Nano, history.LastAttempt); err == nil && now().Sub(last) < memoryHighBackoff {
		return finish("conflict", "memory_high_recovery_backoff", "memory.high drift repeated within 10 minutes; automatic writes suspended for this journal entry")
	}
	if mutation.Applied != expected || mutation.Value != expected || setting.Value != expected {
		return finish("conflict", "memory_high_recovery_blocked", "current plan differs from the last verified value; external value retained")
	}
	if err := recheck(); err != nil {
		if errors.Is(err, errMemoryHighCancelled) {
			return finish("skipped", "memory_high_recovery_cancelled", err.Error())
		}
		return finish("conflict", "memory_high_recovery_blocked", err.Error())
	}
	if err := e.checkMemoryHighCaps(expected); err != nil {
		return finish("conflict", "memory_high_recovery_blocked", err.Error())
	}
	lastAttempt := history.LastAttempt
	mutation.Pending = expected
	history.LastAttempt = now().UTC().Format(time.RFC3339Nano)
	record("memory_high_recovery_intent")
	if err := e.save(); err != nil {
		mutation.Conflict = true
		return highItem(setting, "conflict", "memory_high_recovery_failed", "cannot save recovery intent: "+err.Error())
	}
	beforeWrite := func() error {
		if err := e.checkMemoryHighCaps(expected); err != nil {
			return err
		}
		if err := recheck(); err != nil {
			return err
		}
		actual, err := e.current(setting)
		if err != nil {
			return err
		}
		if actual != "max" {
			return errors.New("memory.high changed while preparing recovery; external value retained")
		}
		return nil
	}
	attempted, err := e.writeRecoveredHigh(setting, beforeWrite)
	if err != nil {
		if !attempted {
			mutation.Pending = ""
			history.LastAttempt = lastAttempt
			if errors.Is(err, errMemoryHighCancelled) {
				return finish("skipped", "memory_high_recovery_cancelled", err.Error())
			}
			return finish("conflict", "memory_high_recovery_blocked", err.Error())
		}
		return finish("conflict", "memory_high_recovery_failed", "write failed; intent retained: "+err.Error())
	}
	if e.group != nil {
		if err := VerifyIdentity(e.Env); err != nil {
			return finish("conflict", "memory_high_recovery_failed", err.Error())
		}
	}
	actual, err := e.current(setting)
	if err != nil || actual != expected {
		return finish("conflict", "memory_high_recovery_failed", "kernel readback differs or is unavailable; intent retained")
	}
	mutation.Pending = ""
	result := finish("applied", "memory_high_recovered", "restored from max and verified by kernel readback")
	if result.State != "applied" {
		mutation.Pending = expected
	}
	return result
}

func (e *Engine) writeRecoveredHigh(setting Setting, beforeWrite func() error) (bool, error) {
	if e.group == nil { // In-memory Files used by engine tests.
		if err := beforeWrite(); err != nil {
			return false, err
		}
		return true, e.write(setting, setting.Value)
	}
	control, err := openLockedMemoryHigh(e.group)
	if err != nil {
		return true, err
	}
	if err := beforeWrite(); err != nil {
		control.Close()
		return false, err
	}
	return true, writeControlFile(control, setting.Value)
}

// Read the visible v2 hierarchy, including the local hard cap. A cgroup
// namespace or bind mount that hides ancestors cannot establish safety.
func (e *Engine) checkMemoryHighCaps(expected string) error {
	check := e.verifyHierarchy
	if check == nil {
		check = verifyCgroup
	}
	return checkVisibleMemoryCaps(e.Env.Target, expected, e.Files, check)
}

func checkVisibleMemoryCaps(target, expected string, files Files, isCgroup func(string) error) error {
	for dir := target; ; dir = filepath.Dir(dir) {
		parent := filepath.Dir(dir)
		if parent == dir || isCgroup(parent) != nil {
			if dir == target {
				return errors.New("cannot verify ancestor memory restrictions")
			}
			if _, err := files.Read(filepath.Join(dir, "memory.max")); !os.IsNotExist(err) {
				return errors.New("cgroup mount hides ancestor memory restrictions")
			}
			return nil
		}
		controls := []string{"memory.max"}
		if dir != target {
			controls = append(controls, "memory.high")
		}
		for _, file := range controls {
			value, err := files.Read(filepath.Join(dir, file))
			if err != nil || !validControl(Setting{File: file}, value) {
				return fmt.Errorf("cannot check external %s", file)
			}
			if maxNumber(value) < maxNumber(expected) {
				return fmt.Errorf("stricter external %s; value retained", file)
			}
		}
	}
}
