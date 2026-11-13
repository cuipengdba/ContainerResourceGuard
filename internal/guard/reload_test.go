package guard

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestReloadRejectsBadFileWithoutDiscardingGoodPolicy(t *testing.T) {
	file := filepath.Join(t.TempDir(), "config.json")
	old := Config{ResourceMode: "manual", Limits: &ManualLimits{MemoryMax: "1GiB"}}
	w, err := NewConfigWatcher(file, old, ConfigOverrides{})
	if err != nil {
		t.Fatal(err)
	}
	for _, raw := range []string{`{"resource_mode":"manual","limits":{"memory_max":"2GiB"}}`, `{"resource_mode":"manual","limits":{"memory_max":"3GiB"}}`} {
		os.WriteFile(file, []byte(raw), 0600)
		if !w.Poll(Environment{}, nil, false) || w.Revision.State != "accepted" {
			t.Fatal(w.Revision)
		}
	}
	if w.Current.Limits.MemoryMax != "3GiB" || w.Revision.Generation != 3 {
		t.Fatal(w.Current, w.Revision)
	}
	hash := w.Revision.AcceptedHash
	for _, raw := range []string{`{`, `{"percent":0}`, `{"percent":20,"percent":30}`, `{"resource_mode":"manual","limits":{"memory_max":"99999999999999999TiB"}}`} {
		os.WriteFile(file, []byte(raw), 0600)
		w.Poll(Environment{}, nil, false)
		if w.Current.Limits.MemoryMax != "3GiB" || w.Revision.Generation != 3 || w.Revision.AcceptedHash != hash || w.Revision.State != "rejected" {
			t.Fatal(w.Revision)
		}
		if w.Poll(Environment{}, nil, false) {
			t.Fatal("unchanged bad configuration caused repeated status changes")
		}
	}
}

func TestReloadModeSwitchWhitespaceAndStateDirectory(t *testing.T) {
	root := t.TempDir()
	file := filepath.Join(root, "config.json")
	w, err := NewConfigWatcher(file, Config{Percent: 20, StateDir: root}, ConfigOverrides{})
	if err != nil {
		t.Fatal(err)
	}
	for _, raw := range []string{`{"percent":20,"state_dir":` + quote(root) + `}`, `{ "percent" : 20, "state_dir" : ` + quote(root) + ` }`} {
		os.WriteFile(file, []byte(raw), 0600)
		w.Poll(Environment{}, nil, false)
		if w.Revision.Generation != 1 {
			t.Fatal("whitespace generated a new policy", w.Revision)
		}
	}
	os.WriteFile(file, []byte(`{"resource_mode":"manual","limits":{"cpu_cores":2},"state_dir":`+quote(root)+`}`), 0600)
	w.Poll(Environment{}, nil, false)
	if w.Current.ResourceMode != "manual" || w.Revision.Generation != 2 {
		t.Fatal(w.Revision)
	}
	os.WriteFile(file, []byte(`{"percent":30}`), 0600)
	w.Poll(Environment{}, nil, false)
	if w.Revision.State != "rejected" || w.Current.ResourceMode != "manual" {
		t.Fatal("accepted changed journal directory", w.Revision)
	}
}

func quote(s string) string { b, _ := json.Marshal(s); return string(b) }

func TestReloadPreservesExplicitCLIOverridesAndRecoversAfterReadFailure(t *testing.T) {
	root := t.TempDir()
	file := filepath.Join(root, "config.json")
	w, err := NewConfigWatcher(file, Config{Percent: 25, StateDir: root}, ConfigOverrides{Percent: 25, StateDir: root})
	if err != nil {
		t.Fatal(err)
	}
	if !w.Poll(Environment{}, nil, false) || w.Revision.State != "rejected" {
		t.Fatal("missing file not reported")
	}
	if w.Poll(Environment{}, nil, false) {
		t.Fatal("repeated missing-file status write")
	}
	os.WriteFile(file, []byte(`{"percent":40}`), 0600)
	w.Poll(Environment{}, nil, false)
	if w.Current.Percent != 25 || w.Revision.State != "accepted" {
		t.Fatal("CLI override lost", w.Current)
	}
	os.Remove(file)
	w.Poll(Environment{}, nil, false)
	os.WriteFile(file, []byte(`{"percent":40}`), 0600)
	w.Poll(Environment{}, nil, false)
	if w.Revision.State != "accepted" || w.Current.Percent != 25 {
		t.Fatal("unchanged file restored after outage did not recover", w.Revision)
	}
	os.WriteFile(file, []byte(`{"resource_mode":"manual","limits":{"cpu_cores":2}}`), 0600)
	w.Poll(Environment{}, nil, false)
	if w.Current.Percent != 25 || w.Revision.State != "rejected" {
		t.Fatal("mixed CLI percent/manual accepted")
	}
}

func TestReloadReaderBoundsAndRejectsNonRegularFiles(t *testing.T) {
	root := t.TempDir()
	p := filepath.Join(root, "too-large.json")
	os.WriteFile(p, []byte(strings.Repeat(" ", MaxJSONBytes+1)), 0600)
	if _, err := ReadBoundedFile(p); err == nil {
		t.Fatal("oversized JSON accepted")
	}
	if _, err := ReadBoundedFile(root); err == nil {
		t.Fatal("directory accepted as JSON")
	}
}
