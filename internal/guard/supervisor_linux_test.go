//go:build linux

package guard

import (
	"context"
	"os"
	"path/filepath"
	"syscall"
	"testing"
)

func TestSupervisorAtomicReplacementGuardsAndPreservesMode(t *testing.T) {
	dir := t.TempDir()
	os.Chmod(dir, 0700)
	path := filepath.Join(dir, "supervisor")
	old := []byte(testSupervisor)
	next := []byte(testSupervisor + "# next\n")
	if err := os.WriteFile(path, old, 0750); err != nil {
		t.Fatal(err)
	}
	if err := replaceSupervisor(path, next, 0750, digest([]byte("wrong"))); err == nil {
		t.Fatal("wrong source accepted")
	}
	if b, _ := os.ReadFile(path); string(b) != string(old) {
		t.Fatal("source changed on rejection")
	}
	if err := replaceSupervisor(path, next, 0755, digest(old)); err == nil {
		t.Fatal("changed mode ignored")
	}
	link := filepath.Join(dir, "link")
	os.Link(path, link)
	if err := replaceSupervisor(path, next, 0750, digest(old)); err == nil {
		t.Fatal("hardlinked script replaced")
	}
	os.Remove(link)
	if err := syscall.Setxattr(path, "user.crg-test", []byte("preserve"), 0); err == nil {
		if err := replaceSupervisor(path, next, 0750, digest(old)); err == nil {
			t.Fatal("extended attributes silently lost")
		}
		syscall.Removexattr(path, "user.crg-test")
	}
	if err := replaceSupervisor(path, next, 0750, digest(old)); err != nil {
		t.Fatal(err)
	}
	b, _ := os.ReadFile(path)
	st, _ := os.Stat(path)
	if string(b) != string(next) || st.Mode().Perm() != 0750 {
		t.Fatal("replacement bytes/mode differ")
	}
	entries, _ := os.ReadDir(dir)
	if len(entries) != 1 {
		t.Fatal("stage leaked")
	}
	os.Remove(path)
	os.Symlink(link, path)
	if err := replaceSupervisor(path, old, 0750, digest(next)); err == nil {
		t.Fatal("symlink accepted")
	}
}

func TestSupervisorSyntaxNeverRunsSourceOrBashEnvironment(t *testing.T) {
	marker := filepath.Join(t.TempDir(), "must-not-exist")
	body := []byte("#!/bin/bash\ntouch " + shellLiteral(marker) + "\n")
	if err := checkedShell(context.Background(), body); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(marker); !os.IsNotExist(err) {
		t.Fatal("syntax checker ran body")
	}
	if err := checkedShell(context.Background(), []byte("if then\n")); err == nil {
		t.Fatal("invalid syntax accepted")
	}
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if err := checkedShell(ctx, body); err == nil {
		t.Fatal("cancelled syntax check accepted")
	}
}
