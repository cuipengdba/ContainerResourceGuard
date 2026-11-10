package main

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"syscall"

	"github.com/cuipengdba/ContainerResourceGuard/internal/guard"
)

type commandError struct {
	code string
	err  error
}

func (e *commandError) Error() string { return e.err.Error() }
func (e *commandError) Unwrap() error { return e.err }

func commandFailureReason(err error, stage string) string {
	switch {
	case errors.Is(err, context.Canceled):
		return "cancelled"
	case errors.Is(err, context.DeadlineExceeded):
		return "operation_timed_out"
	case errors.Is(err, guard.ErrLocked):
		return "lock_unavailable"
	case errors.Is(err, syscall.EROFS):
		return "filesystem_read_only"
	case errors.Is(err, os.ErrPermission):
		return "permission_denied"
	case errors.Is(err, syscall.ENOSPC), errors.Is(err, syscall.EDQUOT):
		return "storage_full"
	}
	return stage
}

type commandFailure struct {
	Schema         string `json:"schema"`
	State          string `json:"state"`
	ReasonCode     string `json:"reason_code"`
	Error          string `json:"error"`
	BusinessAction string `json:"business_action"`
}

func failureOutput(err error) commandFailure {
	code := "command_failed"
	var typed *commandError
	if errors.As(err, &typed) {
		code = typed.code
	}
	return commandFailure{"crg-command-error-v1", "degraded", code, err.Error(), "none"}
}

// Restore's complete per-resource response remains the only JSON object on
// stdout. Add an overall reason without modifying its persisted Status format.
func emitIncompleteRestore(v guard.Status) {
	b, err := json.Marshal(v)
	if err != nil {
		return
	}
	var out map[string]json.RawMessage
	if json.Unmarshal(b, &out) != nil {
		return
	}
	out["reason_code"] = json.RawMessage(`"restore_incomplete"`)
	emit(out)
}
