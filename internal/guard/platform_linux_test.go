//go:build linux

package guard

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"testing"
)

func TestGroupLockAcrossStateDirectories(t *testing.T) {
	root := t.TempDir()
	group := filepath.Join(root, "self")
	os.Mkdir(group, 0700)
	env := Environment{Target: group, Identity: "self"}
	c := Config{StateDir: filepath.Join(root, "one")}
	_, lock, err := OpenEngine(c, env)
	if err != nil {
		t.Fatal(err)
	}
	c.StateDir = filepath.Join(root, "two")
	if _, other, err := OpenEngine(c, env); err == nil {
		other.Close()
		t.Fatal("second state_dir bypassed group lock")
	} else if !errors.Is(err, ErrLocked) {
		t.Fatal(err)
	}
	// A bind-mount alias is represented here by an alternate path to the same inode.
	alias := filepath.Join(root, "alias")
	os.Symlink(group, alias)
	if _, err := lockGroup(alias); err == nil {
		t.Fatal("symlink target accepted")
	}
	lock.Close()
	_, lock, err = OpenEngine(c, env)
	if err != nil {
		t.Fatal("lock not released", err)
	}
	lock.Close()
}

func TestOpenRefusesCorruptJournalAndReleasesLocks(t *testing.T) {
	for _, raw := range []string{`null`, `{}`, `{"version":1,"identity":"self","target":"bad","mutations":null}`} {
		root := t.TempDir()
		group := filepath.Join(root, "self")
		os.Mkdir(group, 0700)
		c := Config{StateDir: filepath.Join(root, "state")}
		os.Mkdir(c.StateDir, 0700)
		os.WriteFile(filepath.Join(c.StateDir, "journal.json"), []byte(raw), 0600)
		if _, lock, err := OpenEngine(c, Environment{Target: group, Identity: "self"}); err == nil {
			lock.Close()
			t.Fatalf("accepted %s", raw)
		}
		lock, err := lockGroup(group)
		if err != nil {
			t.Fatal("leaked group lock", err)
		}
		lock.Close()
	}
	root := t.TempDir()
	c := Config{StateDir: root}
	env := Environment{Target: root, Identity: "self"}
	s := Setting{File: "cpu.max", Value: "100000 100000"}
	j := Journal{Version: 1, Identity: env.Identity, Target: env.Target, Mutations: map[string]*Mutation{s.Key(): {Setting: s, Original: "../bad", Applied: s.Value}}}
	b, _ := json.Marshal(j)
	os.WriteFile(filepath.Join(root, "journal.json"), b, 0600)
	if _, lock, err := OpenEngine(c, env); err == nil {
		lock.Close()
		t.Fatal("invalid original value accepted")
	}
}

func TestDisableMarkerIdentity(t *testing.T) {
	c := Config{StateDir: t.TempDir()}
	env := Environment{Identity: "first"}
	if err := Disable(c, env); err != nil {
		t.Fatal(err)
	}
	if off, err := IsDisabled(c, env); err != nil || !off {
		t.Fatal(off, err)
	}
	if off, err := IsDisabled(c, Environment{Identity: "replacement"}); err != nil || off {
		t.Fatal("old marker leaked to replacement", off, err)
	}
	if err := Enable(c); err != nil {
		t.Fatal(err)
	}
	if off, err := IsDisabled(c, env); err != nil || off {
		t.Fatal(off, err)
	}
}
