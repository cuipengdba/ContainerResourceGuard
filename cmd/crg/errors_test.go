package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"syscall"
	"testing"
	"time"

	"github.com/cuipengdba/ContainerResourceGuard/internal/guard"
)

func TestCommandReasonsUseTypedCausesInsteadOfMessageText(t *testing.T) {
	for _, tc := range []struct {
		err  error
		want string
	}{
		{fmt.Errorf("wrapped: %w", guard.ErrLocked), "lock_unavailable"},
		{fmt.Errorf("wrapped: %w", os.ErrPermission), "permission_denied"},
		{syscall.EROFS, "filesystem_read_only"}, {syscall.ENOSPC, "storage_full"},
		{syscall.EDQUOT, "storage_full"}, {context.Canceled, "cancelled"},
		{context.DeadlineExceeded, "operation_timed_out"},
		{errors.New("permission denied; lock unavailable; context canceled"), "state_backup_failed"},
	} {
		if got := commandFailureReason(tc.err, "state_backup_failed"); got != tc.want {
			t.Fatalf("%q: %s != %s", tc.err, got, tc.want)
		}
	}
}

func TestCLIContractHelper(t *testing.T) {
	if os.Getenv("CRG_TEST_CLI_HELPER") != "1" {
		return
	}
	for i, v := range os.Args {
		if v == "--" {
			os.Args = append([]string{"crg"}, os.Args[i+1:]...)
			main()
			os.Exit(0)
		}
	}
	os.Exit(99)
}

func TestCLICommandFailureJSONAndLegacyBuildFields(t *testing.T) {
	exe, err := os.Executable()
	if err != nil {
		t.Fatal(err)
	}
	dir := t.TempDir()
	invalid := filepath.Join(dir, "invalid.json")
	if err = os.WriteFile(invalid, []byte(`{"percent":20,"percent":30}`), 0600); err != nil {
		t.Fatal(err)
	}
	for _, tc := range []struct {
		args []string
		want string
	}{
		{nil, "usage_invalid"}, {[]string{"unknown"}, "usage_invalid"},
		{[]string{"run", "--percent", "0"}, "usage_invalid"},
		{[]string{"run", "--config", invalid}, "config_invalid"},
	} {
		ctx, cancel := context.WithTimeout(context.Background(), 5e9)
		cmd := exec.CommandContext(ctx, exe, append([]string{"-test.run=^TestCLIContractHelper$", "--"}, tc.args...)...)
		cmd.Env = append(os.Environ(), "CRG_TEST_CLI_HELPER=1")
		started := time.Now()
		out, runErr := cmd.Output()
		elapsed, contextErr := time.Since(started), ctx.Err()
		cancel()
		var exit *exec.ExitError
		if !errors.As(runErr, &exit) || exit.ExitCode() != 1 {
			var stderr []byte
			if exit != nil {
				stderr = exit.Stderr
			}
			t.Fatalf("%v: unexpected exit %v; context=%v elapsed=%s stdout=%q stderr=%q", tc.args, runErr, contextErr, elapsed, out, stderr)
		}
		var object map[string]any
		decoder := json.NewDecoder(bytes.NewReader(out))
		if err = decoder.Decode(&object); err != nil {
			t.Fatalf("%v: %q %v", tc.args, out, err)
		}
		if object["schema"] != "crg-command-error-v1" || object["state"] != "degraded" || object["reason_code"] != tc.want || object["business_action"] != "none" || object["error"] == "" {
			t.Fatal(object)
		}
		if err = decoder.Decode(&object); err != io.EOF {
			t.Fatal("multiple stdout objects", string(out))
		}
	}
	cmd := exec.Command(exe, "-test.run=^TestCLIContractHelper$", "--", "build-info")
	cmd.Env = append(os.Environ(), "CRG_TEST_CLI_HELPER=1")
	out, err := cmd.Output()
	if err != nil {
		t.Fatal(err)
	}
	var info map[string]any
	if json.Unmarshal(out, &info) != nil {
		t.Fatal(string(out))
	}
	for _, key := range []string{"version", "revision", "os", "arch", "lock_protocol", "journal_versions", "io_profile_versions", "writer_controls", "go_version"} {
		if _, ok := info[key]; !ok {
			t.Fatal("compatibility field missing", key)
		}
	}
}
