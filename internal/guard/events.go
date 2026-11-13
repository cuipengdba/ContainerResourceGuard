package guard

import (
	"bytes"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"time"
)

const EventsMaxBytes = 64 << 10
const EventsMaxRecords = 64
const EventsInterval = time.Minute

type EventRecord struct {
	Schema           string         `json:"schema"`
	TimeUTC          string         `json:"time_utc"`
	State            string         `json:"state"`
	Mode             string         `json:"mode"`
	ResourceMode     string         `json:"resource_mode"`
	Configuration    string         `json:"configuration"`
	Reasons          map[string]int `json:"reasons"`
	CoalescedChanges uint32         `json:"coalesced_changes"`
}

type EventsStatus struct {
	State  string `json:"state"`
	Detail string `json:"detail"`
}

type EventWriter struct {
	Save         func(string, []byte) error
	enabled      bool
	lastAttempt  time.Time
	lastError    error
	lastObserved string
	dirty        bool
	coalesced    uint32
}

func eventConfiguration(s string) string {
	switch s {
	case "accepted", "rejected", "unchanged":
		return s
	default:
		return "unknown"
	}
}

func eventSummary(s Status) EventRecord {
	r := EventRecord{Schema: "crg-events-v1", State: diagnosticState(s.State), Mode: diagnosticState(s.Mode), ResourceMode: diagnosticState(s.Plan.ResourceMode), Configuration: "unknown", Reasons: map[string]int{}}
	if s.Configuration != nil {
		r.Configuration = eventConfiguration(s.Configuration.State)
	}
	for _, item := range s.Items {
		code := eventReason(item.ReasonCode)
		if r.Reasons[code] < 1024 {
			r.Reasons[code]++
		}
	}
	return r
}

// A bounded, positive schema: arbitrary errors, paths, identities and config
// contents cannot be copied into an event, including from an older state file.
func eventReason(s string) string {
	switch s {
	case "observe", "applied", "unchanged", "invalid_request", "device_identity", "controller_read", "unrestorable_original", "external_conflict", "memory_safety", "memory_window", "task_safety", "swap_safety", "journal_intent", "controller_recheck", "controller_write", "controller_verify", "journal_finalize", "restored", "restore_incomplete", "observe_retained", "plan_unresolved":
		return s
	default:
		return "unknown"
	}
}

func validEvent(r EventRecord) bool {
	if r.Schema != "crg-events-v1" || diagnosticState(r.State) != r.State || diagnosticState(r.Mode) != r.Mode || diagnosticState(r.ResourceMode) != r.ResourceMode || eventConfiguration(r.Configuration) != r.Configuration || len(r.Reasons) > 32 {
		return false
	}
	if _, err := time.Parse(time.RFC3339, r.TimeUTC); err != nil {
		return false
	}
	for code, count := range r.Reasons {
		if eventReason(code) != code || count < 1 || count > 1024 {
			return false
		}
	}
	return true
}

func appendEvent(path string, record EventRecord) ([]byte, error) {
	b, err := ReadStateBoundedFile(path)
	if errors.Is(err, os.ErrNotExist) {
		b, err = nil, nil
	}
	if err != nil {
		return nil, err
	}
	if len(b) > EventsMaxBytes {
		return nil, errors.New("event file exceeds 64KiB")
	}
	records := []EventRecord{}
	for _, line := range bytes.Split(b, []byte{'\n'}) {
		if len(bytes.TrimSpace(line)) == 0 {
			continue
		}
		var previous EventRecord
		if err := Decode(line, &previous); err != nil || !validEvent(previous) {
			return nil, errors.New("invalid event schema; optional file retained for review")
		}
		records = append(records, previous)
		if len(records) > EventsMaxRecords {
			return nil, errors.New("too many existing events")
		}
	}
	if !validEvent(record) {
		return nil, errors.New("invalid new event")
	}
	records = append(records, record)
	if len(records) > EventsMaxRecords {
		records = records[len(records)-EventsMaxRecords:]
	}
	for {
		var out bytes.Buffer
		for _, item := range records {
			line, err := json.Marshal(item)
			if err != nil {
				return nil, err
			}
			out.Write(line)
			out.WriteByte('\n')
		}
		if out.Len() <= EventsMaxBytes {
			return out.Bytes(), nil
		}
		if len(records) == 1 {
			return nil, errors.New("single event exceeds fixed size bound")
		}
		records = records[1:]
	}
}

// At most one attempt per minute while continuously enabled. Transitions are
// coalesced, not queued without a bound. Failure never controls reconciliation.
func (w *EventWriter) Write(c Config, status Status, now time.Time) *EventsStatus {
	if !c.EventsEnabled {
		w.enabled = false
		return nil
	}
	summary := eventSummary(status)
	b, _ := json.Marshal(summary)
	signature := string(b)
	if !w.enabled {
		w.enabled, w.dirty = true, true
		w.lastObserved = signature
		w.coalesced = 0
		w.lastAttempt = time.Time{}
	} else if signature != w.lastObserved {
		w.dirty = true
		w.lastObserved = signature
		if w.coalesced < 65535 {
			w.coalesced++
		}
	}
	if (w.dirty || w.lastError != nil) && (w.lastAttempt.IsZero() || now.Sub(w.lastAttempt) >= EventsInterval) {
		w.lastAttempt = now
		summary.TimeUTC = now.UTC().Format(time.RFC3339)
		summary.CoalescedChanges = w.coalesced
		path := filepath.Join(c.StateDir, "events.jsonl")
		data, err := appendEvent(path, summary)
		if err == nil {
			save := w.Save
			if save == nil {
				save = volatileFile
			}
			err = save(path, data)
		}
		w.lastError = err
		if err == nil {
			w.dirty = false
			w.coalesced = 0
		}
	}
	if w.lastError != nil {
		return &EventsStatus{State: "unavailable", Detail: "local event export failed; retry at most once per minute; resource reconciliation continues"}
	}
	return &EventsStatus{State: "ready", Detail: "local events.jsonl: coalesced transitions, at most once per minute, 64 records and 64KiB; not a complete audit log"}
}
