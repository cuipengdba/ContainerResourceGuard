//go:build linux

package guard

import (
	"os"
	"path/filepath"
	"testing"
)

func TestReloadRequestOnlyCurrentSessionAndSingleConsumption(t *testing.T) {
	c := Config{StateDir: t.TempDir()}
	env := Environment{Identity: "self", Target: "self-target"}
	r, err := StartReload(c, env, "/etc/crg/source.json")
	if err != nil {
		t.Fatal(err)
	}
	id, _ := nonce()
	request := ReloadRequest{ReloadRuntime: r, RequestID: id}
	path := filepath.Join(c.StateDir, "reload.json")
	if err = AtomicJSON(path, request); err != nil {
		t.Fatal(err)
	}
	if got, err := r.PollRequest(c, ""); err != nil || got != id {
		t.Fatal(got, err)
	}
	if got, err := r.PollRequest(c, id); err != nil || got != "" {
		t.Fatal("request repeated", got, err)
	}
	next, err := StartReload(c, env, r.Source)
	if err != nil {
		t.Fatal(err)
	}
	if got, err := next.PollRequest(c, ""); err != nil || got != "" {
		t.Fatal("earlier Agent request replayed", got, err)
	}
	request.ReloadRuntime = next
	request.RequestID = "bad"
	AtomicJSON(path, request)
	if _, err := next.PollRequest(c, ""); err == nil {
		t.Fatal("invalid nonce accepted")
	}
	os.WriteFile(path, []byte(`{"invalid":true}`), 0600)
	if _, err := next.PollRequest(c, ""); err == nil {
		t.Fatal("invalid request accepted")
	}
	request.RequestID, _ = nonce()
	request.Identity = "replacement-container"
	AtomicJSON(path, request)
	if got, err := next.PollRequest(c, ""); err != nil || got != "" {
		t.Fatal("different cgroup request accepted", got, err)
	}
}
