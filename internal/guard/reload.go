package guard

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"path/filepath"
)

const MaxJSONBytes = 1 << 20

// ConfigMap symlinks are intentionally followed; their final target must be a
// bounded regular file. FIFOs/devices cannot stall the Agent's config reader.
func ReadBoundedFile(path string) ([]byte, error) {
	f, err := openConfigFile(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	s, err := f.Stat()
	if err != nil {
		return nil, err
	}
	if !s.Mode().IsRegular() {
		return nil, errors.New("JSON source must resolve to a regular file")
	}
	if s.Size() > MaxJSONBytes {
		return nil, errors.New("JSON source exceeds 1MiB")
	}
	b, err := io.ReadAll(io.LimitReader(f, MaxJSONBytes+1))
	if err != nil {
		return nil, err
	}
	if len(b) > MaxJSONBytes {
		return nil, errors.New("JSON source grew beyond 1MiB")
	}
	return b, nil
}

type ConfigOverrides struct {
	Percent   float64
	StateDir  string
	IOProfile string
}

type ConfigRevision struct {
	Generation   uint64 `json:"generation"`
	AcceptedHash string `json:"accepted_hash"`
	Source       string `json:"source"`
	State        string `json:"state"`
	Error        string `json:"error,omitempty"`
	RequestID    string `json:"request_id,omitempty"`
}

// Generations are scoped to this Agent run. AcceptedHash is stable across runs
// for the same effective configuration; file whitespace is not a new policy.
type ConfigWatcher struct {
	Path      string
	Overrides ConfigOverrides
	Current   Config
	Revision  ConfigRevision
	seen      string
}

func configHash(c Config) string {
	b, _ := json.Marshal(c)
	h := sha256.Sum256(b)
	return hex.EncodeToString(h[:])
}

func NewConfigWatcher(source string, current Config, overrides ConfigOverrides) (*ConfigWatcher, error) {
	if err := current.Validate(); err != nil {
		return nil, err
	}
	if source != "" {
		var err error
		source, err = filepath.Abs(source)
		if err != nil {
			return nil, err
		}
	}
	return &ConfigWatcher{Path: source, Overrides: overrides, Current: current, Revision: ConfigRevision{Generation: 1, AcceptedHash: configHash(current), Source: source, State: "accepted"}}, nil
}

func (w *ConfigWatcher) reject(err error) bool {
	message := err.Error()
	changed := w.Revision.State != "rejected" || w.Revision.Error != message
	w.Revision.State, w.Revision.Error = "rejected", message
	return changed
}

// Poll never discards Current on error. Validate and build the entire candidate
// before accepting it. No cgroup mutation or journal write happens here.
func (w *ConfigWatcher) Poll(env Environment, original map[string]string, force bool) bool {
	if w.Path == "" {
		return false
	}
	b, err := ReadBoundedFile(w.Path)
	if err != nil {
		w.seen = ""
		return w.reject(fmt.Errorf("configuration read failed; last good policy retained: %w", err))
	}
	h := sha256.Sum256(b)
	raw := hex.EncodeToString(h[:])
	if !force && raw == w.seen {
		return false
	}
	w.seen = raw
	var candidate Config
	if err = Decode(b, &candidate); err != nil {
		return w.reject(fmt.Errorf("configuration rejected; last good policy retained: %w", err))
	}
	if w.Overrides.Percent != 0 {
		candidate.Percent = w.Overrides.Percent
	}
	if w.Overrides.StateDir != "" {
		candidate.StateDir = w.Overrides.StateDir
	}
	if w.Overrides.IOProfile != "" {
		candidate.IOProfile = w.Overrides.IOProfile
	}
	if err = candidate.Validate(); err != nil {
		return w.reject(fmt.Errorf("configuration rejected; last good policy retained: %w", err))
	}
	if candidate.StateDir != w.Current.StateDir {
		return w.reject(errors.New("state_dir cannot change during reload; keep the original journal and use a controlled upgrade"))
	}
	if _, err = BuildPlan(candidate, env, original); err != nil {
		return w.reject(fmt.Errorf("candidate plan rejected; last good policy retained: %w", err))
	}
	fingerprint := configHash(candidate)
	changed := fingerprint != w.Revision.AcceptedHash || w.Revision.State != "accepted"
	if fingerprint != w.Revision.AcceptedHash {
		w.Revision.Generation++
	}
	w.Current = candidate
	w.Revision.AcceptedHash, w.Revision.State, w.Revision.Error = fingerprint, "accepted", ""
	return changed
}
