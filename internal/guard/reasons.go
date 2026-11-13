package guard

import "errors"

// Machine-readable reasons are additive. Detail remains an explanation for
// people and must never be parsed to decide ownership, retries, or safety.
type ReasonError struct {
	Code string
	Err  error
}

func (e *ReasonError) Error() string { return e.Err.Error() }
func (e *ReasonError) Unwrap() error { return e.Err }

func reasonError(code string, err error) error {
	if err == nil {
		return nil
	}
	return &ReasonError{Code: code, Err: err}
}

func errorReason(err error, fallback string) string {
	var reason *ReasonError
	if errors.As(err, &reason) {
		return reason.Code
	}
	return fallback
}

// MemoryWindowPending distinguishes a safe wait from other failures without
// treating a mixed partial result as successful.
func MemoryWindowPending(status Status) bool {
	for _, item := range status.Items {
		if item.ReasonCode == "memory_window" {
			return true
		}
	}
	return false
}
