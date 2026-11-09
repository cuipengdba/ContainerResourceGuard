package guard

import (
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"syscall"
)

type ReloadRuntime struct {
	Version  int    `json:"version"`
	Identity string `json:"identity"`
	Target   string `json:"target"`
	Source   string `json:"source"`
	Session  string `json:"session"`
}

type ReloadRequest struct {
	ReloadRuntime
	RequestID string `json:"request_id"`
}

func nonce() (string, error) {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	return hex.EncodeToString(b), nil
}

func validNonce(s string) bool {
	b, err := hex.DecodeString(s)
	return err == nil && len(b) == 16 && hex.EncodeToString(b) == s
}

// A new session prevents an earlier process's pending requests from being
// replayed, even if the process restarts within the same container cgroup.
func StartReload(c Config, env Environment, source string) (ReloadRuntime, error) {
	r := ReloadRuntime{Version: 1, Identity: env.Identity, Target: env.Target, Source: source}
	if source == "" {
		return r, nil
	}
	var err error
	r.Session, err = nonce()
	if err != nil {
		return r, err
	}
	err = AtomicJSON(filepath.Join(c.StateDir, "runtime.json"), r)
	return r, err
}

// Requested is only an acknowledgement of durable delivery. status.json is the
// authority for accepted policy and individual kernel readbacks.
func RequestReload(c Config, env Environment, source string) (ReloadRequest, error) {
	var r ReloadRequest
	b, err := ReadBoundedFile(filepath.Join(c.StateDir, "runtime.json"))
	if err != nil {
		return r, err
	}
	if err = Decode(b, &r.ReloadRuntime); err != nil {
		return r, err
	}
	if r.Version != 1 || r.Identity != env.Identity || r.Target != env.Target || r.Source == "" || !validNonce(r.Session) {
		return r, errors.New("reload runtime belongs to another cgroup/process or has no configuration source")
	}
	if source != "" {
		absolute, err := filepath.Abs(source)
		if err != nil {
			return r, err
		}
		if absolute != r.Source {
			return r, errors.New("reload only accepts the running Agent's existing configuration path")
		}
	}
	if lock, err := lockGroup(env.Target); err == nil {
		lock.Close()
		return r, errors.New("no writer currently holds this container's cgroup lock")
	} else if !errors.Is(err, syscall.EWOULDBLOCK) {
		return r, err
	}
	r.RequestID, err = nonce()
	if err != nil {
		return r, err
	}
	err = AtomicJSON(filepath.Join(c.StateDir, "reload.json"), r)
	return r, err
}

func (r ReloadRuntime) PollRequest(c Config, seen string) (string, error) {
	if r.Source == "" {
		return "", nil
	}
	b, err := ReadBoundedFile(filepath.Join(c.StateDir, "reload.json"))
	if os.IsNotExist(err) {
		return "", nil
	}
	if err != nil {
		return "", err
	}
	var request ReloadRequest
	if err = Decode(b, &request); err != nil {
		return "", fmt.Errorf("invalid reload request; policy retained: %w", err)
	}
	if request.ReloadRuntime != r {
		return "", nil
	}
	if !validNonce(request.RequestID) {
		return "", errors.New("invalid reload request ID; policy retained")
	}
	if request.RequestID == seen {
		return "", nil
	}
	return request.RequestID, nil
}
