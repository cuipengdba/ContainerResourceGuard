package main

import (
	"context"
	"errors"
	"os"
	"strings"

	"github.com/cuipengdba/ContainerResourceGuard/internal/guard"
	"github.com/cuipengdba/ContainerResourceGuard/internal/runlog"
)

func newRunLogger(command string) *runlog.Logger {
	if command != "run" {
		return nil
	}
	return runlog.New(runlog.DefaultDirectory, os.Stderr)
}

func finishRunLogging(log *runlog.Logger, result *error) {
	if log == nil {
		return
	}
	if *result != nil {
		log.Event("ERROR", "agent_exit", map[string]any{"error": (*result).Error(), "business_action": "none"})
	} else {
		log.Event("INFO", "agent_stop", map[string]string{"business_action": "none"})
	}
}

func logRunStatus(log *runlog.Logger, status guard.Status, highRecovery bool) {
	if log == nil {
		return
	}
	items := make([]map[string]string, 0, len(status.Items))
	for _, item := range status.Items {
		itemLog := map[string]string{"controller": item.File, "device": item.Device, "value": item.Value, "state": item.State, "detail": item.Detail, "reason_code": item.ReasonCode}
		items = append(items, itemLog)
		if item.File == "memory.high" && strings.HasPrefix(item.ReasonCode, "memory_high_") {
			level := "INFO"
			if item.State == "conflict" || item.State == "skipped" {
				level = "WARN"
			}
			log.Event(level, item.ReasonCode, itemLog)
		} else if highRecovery && item.File == "memory.high" && item.ReasonCode == "external_conflict" {
			log.Event("WARN", "memory_high_external_conflict", itemLog)
		}
	}
	log.Event("INFO", "resource_status", map[string]any{"state": status.State, "mode": status.Mode, "error": status.Error, "percentages": status.Plan.Percentages, "legacy_percent": status.Plan.Percent, "memory_policy": status.Plan.MemoryPolicy, "io_policy": status.Plan.IOPolicy, "warnings": status.Plan.Warnings, "items": items})
}

func memoryHighRecoveryCheck(ctx context.Context, watcher *guard.ConfigWatcher, env guard.Environment) func() error {
	config := watcher.Current
	checkGeneration := watcher.RecoveryCheck()
	return func() error {
		if err := guard.VerifyIdentity(env); err != nil {
			return err
		}
		if disabled, err := guard.IsDisabled(config, env); err != nil || disabled {
			return guard.CancelMemoryHighRecovery(errors.New("agent disabled or maintenance state unavailable"))
		}
		if err := checkGeneration(); err != nil {
			return guard.CancelMemoryHighRecovery(err)
		}
		return guard.CancelMemoryHighRecovery(ctx.Err())
	}
}
