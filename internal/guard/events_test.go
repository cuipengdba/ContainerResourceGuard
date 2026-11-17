package guard

import (
	"bytes"
	"errors"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"
)

func TestEventsDefaultOffCoalescesBoundedPrivateHistory(t *testing.T) {
	c := Config{StateDir: t.TempDir()}
	w := EventWriter{}
	now := time.Unix(1000, 0)
	s := Status{State: "managed", Mode: "enforce", Plan: Plan{ResourceMode: "percent"}, Items: []ItemStatus{{State: "applied", ReasonCode: "applied", Detail: "private-token-/path", Setting: Setting{File: "cpu.max", DeviceIdentity: "secret-device"}}}}
	if w.Write(c, s, now) != nil {
		t.Fatal("enabled by default")
	}
	path := filepath.Join(c.StateDir, "events.jsonl")
	if _, err := os.Stat(path); !os.IsNotExist(err) {
		t.Fatal(err)
	}
	c.EventsEnabled = true
	if r := w.Write(c, s, now); r.State != "ready" {
		t.Fatal(r)
	}
	first, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	for i := 1; i < 60; i++ {
		if i%2 == 0 {
			s.State = "managed"
		} else {
			s.State = "degraded"
		}
		w.Write(c, s, now.Add(time.Duration(i)*time.Second))
	}
	if b, _ := os.ReadFile(path); !bytes.Equal(b, first) {
		t.Fatal("high-frequency transitions wrote per cycle")
	}
	w.Write(c, s, now.Add(time.Minute))
	b, _ := os.ReadFile(path)
	if bytes.Count(b, []byte{'\n'}) != 2 || !bytes.Contains(b, []byte(`"coalesced_changes":59`)) {
		t.Fatal(string(b))
	}
	for i := 2; i < 100; i++ {
		s.State = "managed"
		if i%2 != 0 {
			s.State = "degraded"
		}
		if r := w.Write(c, s, now.Add(time.Duration(i)*time.Minute)); r.State != "ready" {
			t.Fatal(r)
		}
	}
	b, _ = os.ReadFile(path)
	if len(b) > EventsMaxBytes || bytes.Count(b, []byte{'\n'}) != EventsMaxRecords {
		t.Fatal(len(b), bytes.Count(b, []byte{'\n'}))
	}
	if strings.Contains(string(b), "private-token") || strings.Contains(string(b), "secret-device") || strings.Contains(string(b), "cpu.max") || strings.Contains(string(b), c.StateDir) {
		t.Fatal("non-allowlisted data leaked")
	}
	st, _ := os.Stat(path)
	if runtime.GOOS == "linux" && st.Mode().Perm() != 0600 {
		t.Fatal(st.Mode())
	}
	w.Write(c, s, now.Add(100*time.Minute))
	last, _ := os.ReadFile(path)
	if !bytes.Equal(b, last) {
		t.Fatal("stable history was needlessly rewritten")
	}
	c.EventsEnabled = false
	if w.Write(c, s, now.Add(101*time.Minute)) != nil {
		t.Fatal("disable failed")
	}
	if b, _ := os.ReadFile(path); !bytes.Equal(b, last) {
		t.Fatal("disable removed or changed history")
	}
}

func TestEventsRejectInvalidExistingFileAndDoNotControlResources(t *testing.T) {
	for _, bad := range []string{`{"schema":"wrong"}`, strings.Repeat("x", EventsMaxBytes+1)} {
		e, _ := fixture(t)
		c := Config{StateDir: t.TempDir(), EventsEnabled: true}
		path := filepath.Join(c.StateDir, "events.jsonl")
		os.WriteFile(path, []byte(bad), 0600)
		w := EventWriter{}
		now := time.Now()
		s := e.Apply(Plan{Settings: []Setting{{File: "cpu.max", Value: "100000 100000"}}})
		if r := w.Write(c, s, now); r.State != "unavailable" {
			t.Fatal(r)
		}
		for i := 1; i < 60; i++ {
			w.Write(c, s, now.Add(time.Duration(i)*time.Second))
		}
		if b, _ := os.ReadFile(path); string(b) != bad {
			t.Fatal("damaged history overwritten")
		}
		if r := e.Apply(Plan{Settings: []Setting{{File: "cpu.max", Value: "200000 100000"}}}); r.State != "managed" {
			t.Fatal(r)
		}
		os.Remove(path)
		if r := w.Write(c, s, now.Add(time.Minute)); r.State != "ready" {
			t.Fatal("optional export did not recover", r)
		}
	}
}

func TestEventsFailureRetriesAreBoundedAndStatusIsStable(t *testing.T) {
	c := Config{EventsEnabled: true, StateDir: t.TempDir()}
	attempts, statusWrites := 0, 0
	w := EventWriter{Save: func(string, []byte) error { attempts++; return errors.New("private-path: full filesystem") }}
	statusWriter := StatusWriter{Save: func(string, any) error { statusWrites++; return nil }}
	now := time.Now()
	for i := 0; i < 120; i++ {
		at := now.Add(time.Duration(i) * time.Second)
		s := Status{State: "managed", TimeUTC: at.Format(time.RFC3339)}
		s.Events = w.Write(c, s, at)
		if s.Events.State != "unavailable" || strings.Contains(s.Events.Detail, "private-path") {
			t.Fatal(s)
		}
		if _, err := statusWriter.Write(s, at); err != nil {
			t.Fatal(err)
		}
	}
	if attempts != 2 || statusWrites != 1 {
		t.Fatal(attempts, statusWrites)
	}
}

func TestEventsUnknownReasonNeverCopiesArbitraryStrings(t *testing.T) {
	s := eventSummary(Status{State: "private-token", Items: []ItemStatus{{ReasonCode: "/secret/token"}}})
	if s.State != "unknown" || s.Reasons["unknown"] != 1 || len(s.Reasons) != 1 {
		t.Fatal(s)
	}
	s.TimeUTC = time.Now().UTC().Format(time.RFC3339)
	if !validEvent(s) {
		t.Fatal(s)
	}
	s.Reasons["/secret/token"] = 1
	if validEvent(s) {
		t.Fatal("allowed arbitrary reason")
	}
}
