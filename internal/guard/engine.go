package guard

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

type Files interface {
	Read(string) (string, error)
	Write(string, string) error
}
type RealFiles struct{}

func (RealFiles) Read(p string) (string, error) { return read(p) }
func (RealFiles) Write(p, v string) error {
	f, e := os.OpenFile(p, os.O_WRONLY, 0)
	if e != nil {
		return e
	}
	n, e := f.WriteString(v + "\n")
	closeErr := f.Close()
	if e != nil {
		return e
	}
	if n != len(v)+1 {
		return errors.New("short cgroup write")
	}
	return closeErr
}

type Mutation struct {
	Setting
	Original string `json:"original"`
	Applied  string `json:"applied"`
	Pending  string `json:"pending,omitempty"`
	Conflict bool   `json:"conflict,omitempty"`
}
type Journal struct {
	Version   int                  `json:"version"`
	Identity  string               `json:"identity"`
	Target    string               `json:"target"`
	Mutations map[string]*Mutation `json:"mutations"`
}
type ItemStatus struct {
	Setting
	State  string `json:"state"`
	Detail string `json:"detail,omitempty"`
}
type Status struct {
	TimeUTC string       `json:"time_utc"`
	Mode    string       `json:"mode"`
	State   string       `json:"state"`
	Plan    Plan         `json:"plan"`
	Items   []ItemStatus `json:"items"`
	Error   string       `json:"error,omitempty"`
}
type Engine struct {
	Config  Config
	Env     Environment
	Files   Files
	Journal Journal
	Persist func(Journal) error
}

func AtomicJSON(path string, v any) error {
	b, e := json.MarshalIndent(v, "", "  ")
	if e != nil {
		return e
	}
	dir := filepath.Dir(path)
	if e = os.MkdirAll(dir, 0700); e != nil {
		return e
	}
	if st, x := os.Lstat(path); x == nil && (!st.Mode().IsRegular() || st.Mode()&os.ModeSymlink != 0) {
		return errors.New("refusing non-regular state destination")
	}
	f, e := os.CreateTemp(dir, ".crg-*")
	if e != nil {
		return e
	}
	tmp := f.Name()
	defer os.Remove(tmp)
	if e = f.Chmod(0600); e == nil {
		_, e = f.Write(append(b, '\n'))
	}
	if e == nil {
		e = f.Sync()
	}
	closeErr := f.Close()
	if e != nil {
		return e
	}
	if closeErr != nil {
		return closeErr
	}
	if e = os.Rename(tmp, path); e != nil {
		return e
	}
	if d, x := os.Open(dir); x == nil {
		e = d.Sync()
		d.Close()
		return e
	}
	return nil
}

func OpenEngine(c Config, env Environment) (*Engine, *os.File, error) {
	if e := os.MkdirAll(c.StateDir, 0700); e != nil {
		return nil, nil, e
	}
	st, e := os.Lstat(c.StateDir)
	if e != nil || !st.IsDir() || st.Mode()&os.ModeSymlink != 0 {
		return nil, nil, errors.New("state directory must be a real directory")
	}
	lock, e := lockFile(filepath.Join(c.StateDir, "agent.lock"))
	if e != nil {
		return nil, nil, fmt.Errorf("one agent per container: lock unavailable: %w", e)
	}
	fail := func(err error) (*Engine, *os.File, error) { lock.Close(); return nil, nil, err }
	j := Journal{Version: 1, Identity: env.Identity, Target: env.Target, Mutations: map[string]*Mutation{}}
	path := filepath.Join(c.StateDir, "journal.json")
	if b, e := os.ReadFile(path); e == nil {
		if e = Decode(b, &j); e != nil {
			return fail(fmt.Errorf("invalid journal; refusing writes: %w", e))
		}
		if j.Version != 1 || j.Mutations == nil {
			return fail(errors.New("unsupported journal"))
		}
		if j.Identity != env.Identity || j.Target != env.Target {
			// A new container never reuses the old cgroup or its values.
			if e = os.Rename(path, filepath.Join(c.StateDir, "journal.previous.json")); e != nil {
				return fail(e)
			}
			j = Journal{Version: 1, Identity: env.Identity, Target: env.Target, Mutations: map[string]*Mutation{}}
		}
	} else if !os.IsNotExist(e) {
		return fail(e)
	}
	for key, m := range j.Mutations {
		if m == nil || !allowed(m.Setting) || key != m.Key() {
			return fail(errors.New("journal contains an invalid mutation"))
		}
	}
	engine := &Engine{Config: c, Env: env, Files: RealFiles{}, Journal: j, Persist: func(j Journal) error { return AtomicJSON(path, j) }}
	return engine, lock, nil
}
func allowed(s Setting) bool {
	return (s.File == "cpu.max" || s.File == "memory.max") && s.Device == "" || s.File == "io.max" && validDevice(s.Device)
}
func (e *Engine) current(s Setting) (string, error) {
	if !allowed(s) {
		return "", errors.New("setting outside self controller allowlist")
	}
	v, x := e.Files.Read(filepath.Join(e.Env.Target, s.File))
	if x != nil {
		return "", x
	}
	if s.File == "io.max" {
		v = ioValue(v, s.Device)
	}
	return strings.TrimSpace(v), nil
}
func (e *Engine) write(s Setting, value string) error {
	if !allowed(s) {
		return errors.New("invalid setting")
	}
	if s.Device != "" {
		value = s.Device + " " + value
	}
	return e.Files.Write(filepath.Join(e.Env.Target, s.File), value)
}
func (e *Engine) Originals() map[string]string {
	r := map[string]string{}
	for k, m := range e.Journal.Mutations {
		r[k] = m.Original
	}
	return r
}
func (e *Engine) save() error { return e.Persist(e.Journal) }

func (e *Engine) Apply(p Plan) Status {
	status := Status{TimeUTC: time.Now().UTC().Format(time.RFC3339), Mode: e.Config.Mode, State: "managed", Plan: p}
	if len(p.Warnings) > 0 {
		status.State = "degraded"
	}
	for _, s := range p.Settings {
		item := ItemStatus{Setting: s}
		if e.Config.Mode == "observe" {
			item.State = "observe"
			status.Items = append(status.Items, item)
			continue
		}
		item.State, item.Detail = e.applyOne(s)
		if item.State != "applied" {
			status.State = "degraded"
		}
		status.Items = append(status.Items, item)
	}
	if e.Config.Mode == "observe" {
		status.State = "observe"
	}
	return status
}
func (e *Engine) applyOne(s Setting) (string, string) {
	current, err := e.current(s)
	if err != nil {
		return "skipped", err.Error()
	}
	m, exists := e.Journal.Mutations[s.Key()]
	if !exists {
		m = &Mutation{Setting: s, Original: current, Applied: current}
		e.Journal.Mutations[s.Key()] = m
	}
	if m.Conflict {
		return "conflict", "external change detected previously; explicit restore/review required"
	}
	if m.Pending != "" {
		if current == m.Pending {
			m.Applied = m.Pending
			m.Pending = ""
		} else if current == m.Applied {
			m.Pending = ""
		} else {
			m.Conflict = true
			_ = e.save()
			return "conflict", "interrupted write and external value differ"
		}
	}
	if current != m.Applied {
		m.Conflict = true
		_ = e.save()
		return "conflict", "current value differs from the last owned value; refusing overwrite"
	}
	if s.File == "memory.max" && maxNumber(s.Value) < maxNumber(current) {
		used, x := e.Files.Read(filepath.Join(e.Env.Target, "memory.current"))
		if x != nil {
			return "skipped", "cannot read current memory: " + x.Error()
		}
		n, x := strconv.ParseUint(strings.TrimSpace(used), 10, 64)
		if x != nil {
			return "skipped", "invalid current memory"
		}
		// Avoid a synchronous forced reclaim/OOM during an already busy workload.
		if maxNumber(s.Value) < n+n/20+(16<<20) {
			return "skipped", "memory target too close to/below current usage (5% + 16 MiB headroom required)"
		}
	}
	if current == s.Value {
		return "applied", "already at desired value"
	}
	m.Setting = s
	m.Pending = s.Value
	if err = e.save(); err != nil {
		m.Pending = ""
		return "skipped", "cannot persist write intent: " + err.Error()
	}
	if err = e.write(s, s.Value); err != nil {
		return "skipped", "write failed; intent retained for recovery: " + err.Error()
	}
	after, err := e.current(s)
	if err != nil {
		return "skipped", "cannot verify write; intent retained: " + err.Error()
	}
	if after != s.Value {
		m.Conflict = true
		_ = e.save()
		return "conflict", "readback differs from requested limit"
	}
	m.Applied = s.Value
	m.Pending = ""
	if err = e.save(); err != nil {
		return "degraded", "limit written but journal finalization failed: " + err.Error()
	}
	return "applied", "written and verified"
}

func (e *Engine) Restore() Status {
	r := Status{TimeUTC: time.Now().UTC().Format(time.RFC3339), Mode: "restore", State: "restored", Plan: Plan{Environment: e.Env}}
	for key, m := range e.Journal.Mutations {
		item := ItemStatus{Setting: m.Setting, State: "restored"}
		cur, err := e.current(m.Setting)
		if err == nil && cur == m.Original {
			delete(e.Journal.Mutations, key)
		} else if err != nil {
			item.State = "skipped"
			item.Detail = err.Error()
		} else if m.Conflict || cur != m.Applied && (m.Pending == "" || cur != m.Pending) {
			item.State = "conflict"
			item.Detail = "external value retained"
		} else {
			// Persist restore intent BEFORE writing, just like normal application.
			m.Applied = cur
			m.Pending = m.Original
			if err = e.save(); err == nil {
				err = e.write(m.Setting, m.Original)
			}
			if err == nil {
				var actual string
				actual, err = e.current(m.Setting)
				if err == nil && actual != m.Original {
					err = errors.New("restore readback mismatch")
				}
			}
			if err == nil {
				delete(e.Journal.Mutations, key)
			} else {
				item.State = "skipped"
				item.Detail = err.Error()
			}
		}
		if item.State != "restored" {
			r.State = "degraded"
		}
		r.Items = append(r.Items, item)
	}
	if err := e.save(); err != nil {
		r.State = "degraded"
		r.Error = err.Error()
	}
	return r
}

func VerifyIdentity(env Environment) error {
	now, e := Discover()
	if e != nil {
		return e
	}
	if now.Identity != env.Identity || now.Target != env.Target {
		return errors.New("cgroup identity changed; no further writes allowed")
	}
	return nil
}
