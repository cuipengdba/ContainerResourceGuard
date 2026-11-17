//go:build linux

package guard

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"syscall"
	"testing"
)

func TestReloadReaderFIFOAndConfigMapLinkReplacement(t *testing.T) {
	root := t.TempDir()
	fifo := filepath.Join(root, "fifo")
	if err := syscall.Mkfifo(fifo, 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := ReadBoundedFile(fifo); err == nil {
		t.Fatal("FIFO accepted")
	}
	c := Config{Percent: 20, StateDir: root}
	w, err := NewConfigWatcher(filepath.Join(root, "source.json"), c, ConfigOverrides{})
	if err != nil {
		t.Fatal(err)
	}
	for _, value := range []string{"20", "30"} {
		file := filepath.Join(root, value+".json")
		os.WriteFile(file, []byte(`{"percent":`+value+`,"state_dir":`+quote(root)+`}`), 0600)
		next := filepath.Join(root, "next")
		if err := os.Symlink(file, next); err != nil {
			t.Fatal(err)
		}
		if err := os.Rename(next, w.Path); err != nil {
			t.Fatal(err)
		}
		w.Poll(Environment{}, nil, false)
	}
	if w.Current.Percent != 30 || w.Revision.Generation != 2 {
		t.Fatal(w.Revision)
	}
}

func TestRequestReloadRequiresOwnRunningWriterAndSource(t *testing.T) {
	root := t.TempDir()
	group := filepath.Join(root, "group")
	os.Mkdir(group, 0700)
	c := Config{StateDir: filepath.Join(root, "state")}
	env := Environment{Target: group, Identity: "self"}
	source := filepath.Join(root, "config.json")
	_, err := StartReload(c, env, source)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := RequestReload(c, env, source); err == nil {
		t.Fatal("request accepted without a writer")
	}
	lock, err := lockGroup(group)
	if err != nil {
		t.Fatal(err)
	}
	defer lock.Close()
	if _, err := RequestReload(c, env, source+"-other"); err == nil {
		t.Fatal("different source accepted")
	}
	if _, err := RequestReload(c, Environment{Target: group, Identity: "other"}, source); err == nil {
		t.Fatal("different container accepted")
	}
	request, err := RequestReload(c, env, source)
	if err != nil || !validNonce(request.RequestID) {
		t.Fatal(request, err)
	}
}

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

func TestCapacityFilesMustComeFromNativeFilesystem(t *testing.T) {
	file := filepath.Join(t.TempDir(), "fake-meminfo")
	if err := os.WriteFile(file, []byte("MemTotal: 1024 kB\n"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := verifyCapacitySource(file, "memory"); err == nil {
		t.Fatal("regular disk file accepted as host procfs")
	}
	if err := verifyCapacitySource("/proc/meminfo", "memory"); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat("/sys/devices/system/cpu/online"); err == nil {
		if err := verifyCapacitySource("/sys/devices/system/cpu/online", "cpu"); err != nil {
			t.Fatal(err)
		}
	}
}
