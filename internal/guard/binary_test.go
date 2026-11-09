//go:build linux

package guard

import (
	"bytes"
	"os"
	"path/filepath"
	"testing"
)

func TestBinaryTrustAndPathBoundaries(t *testing.T) {
	for _, s := range []string{"", "abc", string(bytes.Repeat([]byte("A"), 64)), string(bytes.Repeat([]byte("0"), 63)), string(bytes.Repeat([]byte("g"), 64))} {
		if validSHA(s) {
			t.Fatal("accepted invalid expected SHA", s)
		}
	}
	if !validSHA(string(bytes.Repeat([]byte("a"), 64))) {
		t.Fatal("valid SHA rejected")
	}
	root := t.TempDir()
	if err := os.Chmod(root, 0700); err != nil {
		t.Fatal(err)
	}
	if err := realInstallDirectory(root); err != nil {
		t.Fatal(err)
	}
	if err := realInstallDirectory(filepath.Join(root, "missing")); err == nil {
		t.Fatal("missing directory accepted")
	}
	if err := realInstallDirectory("relative"); err == nil {
		t.Fatal("relative directory accepted")
	}
	if !pathWithin(root, filepath.Join(root, "child")) || pathWithin(root, root+"-sibling") {
		t.Fatal("path boundary broken")
	}
	if err := os.Symlink(root, root+"-alias"); err == nil {
		defer os.Remove(root + "-alias")
		if realInstallDirectory(root+"-alias") == nil {
			t.Fatal("symlink directory accepted")
		}
	}
}

func TestBinaryCopyVerifiesDigestAndNeverOverwrites(t *testing.T) {
	root := t.TempDir()
	source := filepath.Join(root, "source")
	out := filepath.Join(root, "copy")
	data := append([]byte("\x7fELF"), bytes.Repeat([]byte("payload"), 64)...)
	if err := os.WriteFile(source, data, 0700); err != nil {
		t.Fatal(err)
	}
	f, err := os.Open(source)
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()
	got, err := binaryDigest(f)
	if err != nil || got != digest(data) {
		t.Fatal(got, err)
	}
	if err = copyBinary(f, out, got); err != nil {
		t.Fatal(err)
	}
	if err = copyBinary(f, out, got); err == nil {
		t.Fatal("existing recovery binary overwritten")
	}
	if err = copyBinary(f, filepath.Join(root, "mismatch"), string(bytes.Repeat([]byte("0"), 64))); err == nil {
		t.Fatal("changed candidate accepted")
	}
	b, _ := os.ReadFile(out)
	if !bytes.Equal(data, b) {
		t.Fatal("source/copy mismatch")
	}
}

func TestBinarySnapshotCannotAuthorizeOtherIdentityOrChangedState(t *testing.T) {
	c, env, _ := upgradeFixture(t)
	if err := AtomicJSON(filepath.Join(c.StateDir, "disabled.json"), DisableMarker{Version: 1, Identity: env.Identity}); err != nil {
		t.Fatal(err)
	}
	s, err := inspectUpgrade(c, env)
	if err != nil {
		t.Fatal(err)
	}
	s.Check.QuiescentSnapshot = true
	if err = requireSwapSnapshot(s); err != nil {
		t.Fatal(err)
	}
	before := binarySnapshot(c, s)
	changed := c
	changed.IntervalSeconds = 30
	if binarySnapshot(changed, s) == before {
		t.Fatal("changed config retains rollback authorization")
	}
	s.Disable = []byte(`{"version":1,"identity":"foreign"}`)
	if binarySnapshot(c, s) == before {
		t.Fatal("changed disable marker retains authorization")
	}
	s.Check.JournalIdentityMatches = false
	if requireSwapSnapshot(s) == nil {
		t.Fatal("foreign journal accepted")
	}
	s.Check.JournalIdentityMatches = true
	s.Check.QuiescentSnapshot = false
	if requireSwapSnapshot(s) == nil {
		t.Fatal("live writer accepted")
	}
}
