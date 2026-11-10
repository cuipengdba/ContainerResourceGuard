//go:build linux

package guard

import (
	"context"
	"os"
	"path/filepath"
	"strings"
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
	// An inherited private umask may narrow creation permissions. Establish
	// the explicit fixture mode before testing preservation of that mode.
	if err := os.Chmod(path, 0750); err != nil {
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
	envFile := filepath.Join(t.TempDir(), "bash-env")
	if err := os.WriteFile(envFile, []byte("touch "+shellLiteral(marker)+"\n"), 0600); err != nil {
		t.Fatal(err)
	}
	t.Setenv("BASH_ENV", envFile)
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

func TestSupervisorPlanRejectsAliasedStateBeforeAnyInputOrBackup(t *testing.T) {
	dir := t.TempDir()
	state := filepath.Join(dir, "state")
	alias := filepath.Join(dir, "alias")
	if err := os.Mkdir(state, 0700); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(state, alias); err != nil {
		t.Fatal(err)
	}
	c := Config{Percent: 20, StateDir: alias}
	if err := c.Validate(); err != nil {
		t.Fatal(err)
	}
	sha := strings.Repeat("0", 64)
	o := SupervisorOptions{Path: filepath.Join(dir, "missing"), Config: filepath.Join(dir, "config"), Helper: filepath.Join(dir, "helper"), Binary: filepath.Join(dir, "binary"), SourceSHA256: sha, HelperSHA256: sha, BinarySHA256: sha}
	if _, err := PreviewSupervisor(context.Background(), c, o); err == nil || !strings.Contains(err.Error(), "real clean state directory") {
		t.Fatal(err)
	}
	entries, _ := os.ReadDir(state)
	if len(entries) != 0 {
		t.Fatal("preview wrote to state through alias")
	}
}
