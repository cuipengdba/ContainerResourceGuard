//go:build linux

package guard

import (
	"encoding/json"
	"os"
	"path/filepath"
	"syscall"
	"testing"
)

func TestUpgradeExistingLockNeverCreatesAndRejectsOtherWriter(t *testing.T) {
	root := t.TempDir()
	path := filepath.Join(root, "agent.lock")
	if _, err := lockExistingState(path); !os.IsNotExist(err) {
		t.Fatal(err)
	}
	if _, err := os.Stat(path); !os.IsNotExist(err) {
		t.Fatal("preview created lock")
	}
	writer, err := lockFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if reader, err := lockExistingState(path); err == nil {
		reader.Close()
		t.Fatal("active state writer ignored")
	}
	writer.Close()
	reader, err := lockExistingState(path)
	if err != nil {
		t.Fatal(err)
	}
	reader.Close()
	for _, special := range []string{"fifo", "directory", "link"} {
		path = filepath.Join(root, special)
		switch special {
		case "fifo":
			err = syscall.Mkfifo(path, 0600)
		case "directory":
			err = os.Mkdir(path, 0700)
		case "link":
			err = os.Symlink(filepath.Join(root, "agent.lock"), path)
		}
		if err != nil {
			t.Fatal(err)
		}
		if f, err := lockExistingState(path); err == nil {
			f.Close()
			t.Fatal("accepted special lock", special)
		}
	}
}

func TestPrivateBackupOutsideStateExclusiveAndAliasProtection(t *testing.T) {
	root := t.TempDir()
	state := filepath.Join(root, "state")
	os.Mkdir(state, 0700)
	alias := filepath.Join(root, "alias")
	os.Symlink(state, alias)
	for _, path := range []string{filepath.Join(state, "backup.json"), filepath.Join(alias, "backup.json"), "relative.json"} {
		if err := writePrivateBackup(path, state, []byte("private")); err == nil {
			t.Fatal("unsafe destination accepted", path)
		}
	}
	out := filepath.Join(root, "private.json")
	if err := writePrivateBackup(out, state, []byte("original")); err != nil {
		t.Fatal(err)
	}
	if err := writePrivateBackup(out, state, []byte("replace")); err == nil {
		t.Fatal("existing backup replaced")
	}
	st, _ := os.Stat(out)
	b, _ := os.ReadFile(out)
	if st.Mode().Perm() != 0600 || string(b) != "original" {
		t.Fatal(st, string(b))
	}
	link := filepath.Join(root, "link.json")
	os.Symlink(out, link)
	if err := writePrivateBackup(link, state, []byte("replace")); err == nil {
		t.Fatal("symlink backup replaced")
	}
}

func TestOpenDoesNotArchiveUnsupportedForeignMutations(t *testing.T) {
	c, env, _ := upgradeFixture(t)
	os.Mkdir(env.Target, 0700)
	s := Setting{File: "future.controller", Value: "max"}
	j := Journal{Version: 1, Identity: "foreign", Target: env.Target, Mutations: map[string]*Mutation{s.Key(): {Setting: s, Original: "max", Applied: "max"}}}
	b, _ := json.Marshal(j)
	path := filepath.Join(c.StateDir, "journal.json")
	os.WriteFile(path, b, 0600)
	if _, locks, err := OpenEngine(c, env); err == nil {
		locks.Close()
		t.Fatal("future foreign journal archived and ignored")
	}
	after, _ := os.ReadFile(path)
	if string(after) != string(b) {
		t.Fatal("incompatible originals lost")
	}
	if _, err := os.Stat(filepath.Join(c.StateDir, "journal.previous.json")); !os.IsNotExist(err) {
		t.Fatal("incompatible journal archived")
	}
}
