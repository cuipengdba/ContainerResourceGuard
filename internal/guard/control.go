package guard

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"syscall"
	"time"
)

type DisableMarker struct {
	Version  int    `json:"version"`
	Identity string `json:"identity"`
	TimeUTC  string `json:"time_utc"`
}

// A marker belongs to a cgroup incarnation. A replacement container starts with
// its own policy even when an emptyDir survives the old container process.
func IsDisabled(c Config, env Environment) (bool, error) {
	b, err := os.ReadFile(filepath.Join(c.StateDir, "disabled.json"))
	if os.IsNotExist(err) {
		return false, nil
	}
	if err != nil {
		return false, err
	}
	var m DisableMarker
	if err := Decode(b, &m); err != nil {
		return false, err
	}
	if m.Version != 1 || m.Identity == "" {
		return false, errors.New("invalid disable marker")
	}
	return m.Identity == env.Identity, nil
}

func Disable(c Config, env Environment) error {
	return AtomicJSON(filepath.Join(c.StateDir, "disabled.json"), DisableMarker{1, env.Identity, time.Now().UTC().Format(time.RFC3339)})
}

func Enable(c Config) error {
	err := os.Remove(filepath.Join(c.StateDir, "disabled.json"))
	if os.IsNotExist(err) {
		return nil
	}
	if err != nil {
		return err
	}
	d, err := os.Open(c.StateDir)
	if err != nil {
		return err
	}
	defer d.Close()
	return d.Sync()
}

// Status is expendable; the write-ahead journal remains synchronous and is never
// throttled. Unchanged snapshots are saved at most once every five minutes.
type StatusWriter struct {
	Path    string
	Save    func(string, any) error
	last    string
	written time.Time
}

func StableStatus(s Status) string {
	s.TimeUTC = ""
	b, _ := json.Marshal(s)
	return string(b)
}

func (w *StatusWriter) Write(s Status, now time.Time) (bool, error) {
	stable := StableStatus(s)
	if stable == w.last && now.Sub(w.written) < 5*time.Minute {
		return false, nil
	}
	save := w.Save
	if save == nil {
		save = AtomicJSON
	}
	if err := save(w.Path, s); err != nil {
		return false, err
	}
	w.last, w.written = stable, now
	return true, nil
}

type StatusView struct {
	Status
	Memory             *MemorySnapshot `json:"memory,omitempty"`
	SnapshotAgeSeconds int64           `json:"snapshot_age_seconds"`
	WriterLockHeld     bool            `json:"writer_lock_held"`
	Actual             []ItemStatus    `json:"actual"`
	LockCheckError     string          `json:"lock_check_error,omitempty"`
}

func ReadStatus(c Config, env Environment) (StatusView, error) {
	var v StatusView
	b, err := os.ReadFile(filepath.Join(c.StateDir, "status.json"))
	if err != nil {
		return v, err
	}
	if err = Decode(b, &v.Status); err != nil {
		return v, err
	}
	if v.Plan.Environment.Identity != env.Identity || v.Plan.Environment.Target != env.Target {
		return v, errors.New("status belongs to an earlier/different cgroup; refusing stale snapshot")
	}
	t, err := time.Parse(time.RFC3339, v.TimeUTC)
	if err != nil {
		return v, err
	}
	v.SnapshotAgeSeconds = int64(time.Since(t).Seconds())
	if lock, err := lockGroup(env.Target); err == nil {
		lock.Close()
	} else {
		v.WriterLockHeld = errors.Is(err, syscall.EWOULDBLOCK)
		if !v.WriterLockHeld {
			v.LockCheckError = err.Error()
		}
	}
	e := Engine{Env: env, Files: RealFiles{}}
	memory := ReadMemorySnapshot(env, e.Files)
	v.Memory = &memory
	settings := append([]Setting(nil), v.Plan.Settings...)
	seen := map[string]bool{}
	for _, s := range settings {
		seen[s.Key()] = true
	}
	for _, i := range v.Items {
		if !seen[i.Key()] {
			settings = append(settings, i.Setting)
			seen[i.Key()] = true
		}
	}
	for _, s := range settings {
		actual, err := e.current(s)
		i := ItemStatus{Setting: s, State: "read"}
		if err != nil {
			i.State, i.Detail = "unavailable", err.Error()
			i.Value = ""
		} else {
			i.Value = actual
		}
		v.Actual = append(v.Actual, i)
	}
	return v, nil
}
