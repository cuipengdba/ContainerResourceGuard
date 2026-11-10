package main

import (
	"encoding/json"
	"os"

	"github.com/cuipengdba/ContainerResourceGuard/internal/guard"
	"github.com/cuipengdba/ContainerResourceGuard/internal/runlog"
)

// Called before discovery, locks, journal writes, calibration and resource writes.
// Unsupported versions are an explained no-op, not a reason to restart business.
func checkCgroupSupport(log *runlog.Logger, detect func() (guard.CgroupCheck, error)) (bool, error) {
	check, err := detect()
	level := "INFO"
	details := map[string]any{"check": check, "business_action": "none"}
	if err != nil {
		level = "ERROR"
		details["error"] = err.Error()
	} else if !check.Allowed {
		level = "WARN"
	}
	if log != nil {
		log.Event(level, "cgroup_detected", details)
	} else {
		// Maintenance/diagnostic commands do not open the run log directory.
		b, _ := json.Marshal(map[string]any{"level": level, "event": "cgroup_detected", "details": details})
		_, _ = os.Stderr.Write(append(b, '\n'))
	}
	if err != nil {
		return false, err
	}
	if !check.Allowed {
		emit(map[string]any{"state": "skipped", "cgroup": check, "business_action": "none"})
	}
	return check.Allowed, nil
}
