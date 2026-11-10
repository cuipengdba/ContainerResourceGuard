package guard

import (
	"errors"
	"os"
	"syscall"
	"testing"
)

func TestLockFailureRetainsFilesystemCause(t *testing.T) {
	for _, cause := range []error{syscall.EROFS, syscall.ENOSPC, syscall.EDQUOT, os.ErrPermission} {
		err := lockFailure(&os.PathError{Op: "open", Path: "/private-state/agent.lock", Err: cause})
		if !errors.Is(err, cause) || errors.Is(err, ErrLocked) {
			t.Fatalf("filesystem failure misclassified as contention: %v", err)
		}
	}
	if err := lockFailure(syscall.EWOULDBLOCK); !errors.Is(err, ErrLocked) || !errors.Is(err, syscall.EWOULDBLOCK) {
		t.Fatalf("contention lost typed identity: %v", err)
	}
}
