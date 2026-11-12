package main

import (
	"os"

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

func logRunStatus(log *runlog.Logger, status guard.Status) {
	if log == nil {
		return
	}
	items := make([]map[string]string, 0, len(status.Items))
	for _, item := range status.Items {
		items = append(items, map[string]string{"controller": item.File, "state": item.State, "detail": item.Detail})
	}
	log.Event("INFO", "resource_status", map[string]any{"state": status.State, "mode": status.Mode, "error": status.Error, "percentages": status.Plan.Percentages, "legacy_percent": status.Plan.Percent, "memory_policy": status.Plan.MemoryPolicy, "warnings": status.Plan.Warnings, "items": items})
}
