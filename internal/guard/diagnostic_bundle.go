package guard

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"time"
)

const DiagnosticMaxBytes = 64 << 10

type DiagnosticControl struct {
	File   string `json:"file"`
	Device string `json:"device,omitempty"`
	Value  string `json:"value,omitempty"`
	State  string `json:"state"`
}

// A positive allowlist: never embed config, paths, error text, environment,
// journal original values, command lines, business logs, or file contents.
type DiagnosticBundle struct {
	Percentages        *ResourcePercentages `json:"percentages,omitempty"`
	Schema             string               `json:"schema"`
	CreatedUTC         string               `json:"created_utc"`
	Included           []string             `json:"included"`
	OS                 string               `json:"os"`
	Arch               string               `json:"arch"`
	StatusAvailable    bool                 `json:"status_available"`
	SnapshotAgeSeconds int64                `json:"snapshot_age_seconds,omitempty"`
	WriterLockHeld     bool                 `json:"writer_lock_held"`
	State              string               `json:"state"`
	Mode               string               `json:"mode"`
	ResourceMode       string               `json:"resource_mode"`
	Percent            float64              `json:"percent"`
	HostCPUs           int                  `json:"host_cpus"`
	HostMemoryBytes    uint64               `json:"host_memory_bytes"`
	Controls           []DiagnosticControl  `json:"controls"`
	OmittedControls    int                  `json:"omitted_controls"`
	Memory             MemorySnapshot       `json:"memory"`
}

func diagnosticState(s string) string {
	switch s {
	case "managed", "degraded", "observe", "restored", "disabled", "applied", "skipped", "conflict", "read", "unavailable", "enforce", "restore", "disable", "percent", "manual":
		return s
	default:
		return "unknown"
	}
}

func BuildDiagnosticBundle(env Environment, status *StatusView, files Files) DiagnosticBundle {
	r := DiagnosticBundle{Schema: "crg-diagnostics-v1", CreatedUTC: time.Now().UTC().Format(time.RFC3339), Included: []string{"platform", "verified_host_totals", "bounded_controller_results", "live_memory_counters"}, OS: runtime.GOOS, Arch: runtime.GOARCH, State: "unavailable", Mode: "unknown", ResourceMode: "unknown", HostCPUs: env.OnlineCPUs, HostMemoryBytes: env.MemoryBytes, Controls: []DiagnosticControl{}, Memory: ReadMemorySnapshot(env, files)}
	if status == nil {
		return r
	}
	r.StatusAvailable, r.SnapshotAgeSeconds, r.WriterLockHeld = true, status.SnapshotAgeSeconds, status.WriterLockHeld
	r.State, r.Mode, r.ResourceMode = diagnosticState(status.State), diagnosticState(status.Mode), diagnosticState(status.Plan.ResourceMode)
	if status.Plan.Percent >= 0 && status.Plan.Percent <= 100 {
		r.Percent = status.Plan.Percent
	}
	if status.Plan.Percentages != nil {
		values := *status.Plan.Percentages
		valid := true
		for name, value := range values.fields() {
			if value == nil || *value < 0 || *value > 100 || *value != *value || *value == 0 && name != "memory_swap_percent" {
				valid = false
			}
		}
		if valid {
			r.Percentages = &values
		}
	}
	for _, item := range status.Actual {
		if len(r.Controls) >= 64 {
			r.OmittedControls++
			continue
		}
		if !allowed(item.Setting) {
			continue
		}
		c := DiagnosticControl{File: item.File, Device: item.Device, State: diagnosticState(item.State)}
		if len(item.Value) <= 256 && validControl(item.Setting, item.Value) {
			c.Value = item.Value
		}
		r.Controls = append(r.Controls, c)
	}
	return r
}

func EncodeDiagnosticBundle(bundle DiagnosticBundle) ([]byte, error) {
	b, err := json.MarshalIndent(bundle, "", "  ")
	if err != nil {
		return nil, err
	}
	if len(b)+1 > DiagnosticMaxBytes {
		return nil, &diagnosticSizeError{}
	}
	return append(b, '\n'), nil
}

type diagnosticSizeError struct{}

func (*diagnosticSizeError) Error() string {
	return "diagnostic exceeds fixed 64KiB limit; refusing output"
}

// Diagnostics create a new file, never replace journals or existing files.
// Errors may leave a private partial output for explicit manual removal.
func WriteDiagnosticFile(path string, c Config, bundle DiagnosticBundle) error {
	if !filepath.IsAbs(path) {
		return errors.New("diagnostic output must be an absolute local path")
	}
	parent, err := filepath.EvalSymlinks(filepath.Dir(path))
	if err != nil {
		return err
	}
	resolved := filepath.Join(parent, filepath.Base(path))
	state := resolveDiagnosticGuardPath(c.StateDir)
	rel, err := filepath.Rel(state, resolved)
	if err == nil && rel != ".." && !strings.HasPrefix(rel, ".."+string(filepath.Separator)) || resolved == resolveDiagnosticGuardPath(c.IOProfile) {
		return errors.New("diagnostic output cannot replace state files or the IO profile")
	}
	b, err := EncodeDiagnosticBundle(bundle)
	if err != nil {
		return err
	}
	f, err := os.OpenFile(resolved, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if err != nil {
		return err
	}
	n, writeErr := f.Write(b)
	if writeErr == nil && n != len(b) {
		writeErr = errors.New("short diagnostic write")
	}
	if writeErr == nil {
		writeErr = f.Sync()
	}
	closeErr := f.Close()
	if err = errors.Join(writeErr, closeErr); err != nil {
		return err
	}
	dir, err := os.Open(parent)
	if err != nil {
		return err
	}
	return errors.Join(dir.Sync(), dir.Close())
}

func resolveDiagnosticGuardPath(path string) string {
	path = filepath.Clean(path)
	var missing []string
	for {
		if resolved, err := filepath.EvalSymlinks(path); err == nil {
			for i := len(missing) - 1; i >= 0; i-- {
				resolved = filepath.Join(resolved, missing[i])
			}
			return resolved
		}
		parent := filepath.Dir(path)
		if parent == path {
			return path
		}
		missing = append(missing, filepath.Base(path))
		path = parent
	}
}

// Keep a narrow helper for CLI/documentation parity without importing any
// private paths or source revision from an untrusted status snapshot.
func DiagnosticContents() string {
	return strings.Join([]string{"platform", "verified host totals", "up to 64 controller results", "live memory counters"}, ", ")
}
