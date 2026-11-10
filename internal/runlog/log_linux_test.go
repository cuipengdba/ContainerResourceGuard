//go:build linux

package runlog

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"syscall"
	"testing"
	"time"
)

func testLogger(t *testing.T) (*Logger, *time.Time, *bytes.Buffer) {
	t.Helper()
	now := time.Date(2026, 11, 10, 23, 59, 59, 0, time.FixedZone("CST", 8*3600))
	stderr := &bytes.Buffer{}
	l := New(t.TempDir(), stderr)
	l.now = func() time.Time { return now }
	return l, &now, stderr
}

func TestDateRotationRestartAndQuietCleanup(t *testing.T) {
	l, now, _ := testLogger(t)
	l.Event("INFO", "first", nil)
	l.Event("INFO", "second", nil)
	first := filepath.Join(l.directory, "crg-2026-11-10.log")
	b, err := os.ReadFile(first)
	if err != nil || bytes.Count(b, []byte("\n")) != 2 {
		t.Fatal(string(b), err)
	}
	restarted := New(l.directory, l.stderr)
	restarted.now = l.now
	restarted.Event("INFO", "restarted", nil)
	b, _ = os.ReadFile(first)
	if bytes.Count(b, []byte("\n")) != 3 {
		t.Fatal(string(b))
	}
	*now = now.Add(2 * time.Second)
	l.Tick()
	if _, err := os.Stat(filepath.Join(l.directory, "crg-2026-11-11.log")); err != nil {
		t.Fatal(err)
	}
	for name := range map[string]bool{"crg-2026-10-12.log": true, "crg-2026-10-13.log": true, "business.log": true, "crg-2026-02-30.log": true} {
		if err := os.WriteFile(filepath.Join(l.directory, name), []byte("sentinel"), 0600); err != nil {
			t.Fatal(err)
		}
	}
	*now = now.Add(time.Minute)
	l.Tick()
	if _, err := os.Stat(filepath.Join(l.directory, "crg-2026-10-12.log")); !os.IsNotExist(err) {
		t.Fatal("did not expire day30", err)
	}
	for _, name := range []string{"crg-2026-10-13.log", "business.log", "crg-2026-02-30.log"} {
		if _, err := os.Stat(filepath.Join(l.directory, name)); err != nil {
			t.Fatal(name, err)
		}
	}
}

func TestActualOneGBBudgetDeletesOldestThenResetsOnlyDailyFile(t *testing.T) {
	l, _, stderr := testLogger(t)
	for _, name := range []string{"crg-2026-11-08.log", "crg-2026-11-09.log"} {
		f, err := os.Create(filepath.Join(l.directory, name))
		if err != nil {
			t.Fatal(err)
		}
		if err = f.Truncate(600_000_000); err != nil {
			t.Fatal(err)
		}
		f.Close()
	}
	l.Event("INFO", "budget", nil)
	if _, err := os.Stat(filepath.Join(l.directory, "crg-2026-11-08.log")); !os.IsNotExist(err) {
		t.Fatal("oldest remains", err)
	}
	if _, err := os.Stat(filepath.Join(l.directory, "crg-2026-11-09.log")); err != nil {
		t.Fatal("removed newer unnecessarily", err)
	}
	_ = os.Remove(filepath.Join(l.directory, "crg-2026-11-09.log"))
	today := filepath.Join(l.directory, "crg-2026-11-10.log")
	f, err := os.OpenFile(today, os.O_WRONLY, 0)
	if err != nil {
		t.Fatal(err)
	}
	if err = f.Truncate(MaximumBytes); err != nil {
		t.Fatal(err)
	}
	f.Close()
	l.Event("INFO", "newest", nil)
	b, err := os.ReadFile(today)
	if err != nil {
		t.Fatal(err)
	}
	if len(b) > 1024 || !bytes.Contains(b, []byte("daily_file_reset_size_limit")) || !bytes.Contains(b, []byte("newest")) {
		t.Fatal(len(b), string(b), stderr.String())
	}
	names, _ := os.ReadDir(l.directory)
	count := 0
	for _, n := range names {
		if _, ok := dailyDate(n.Name()); ok {
			count++
		}
	}
	if count != 1 {
		t.Fatal("more than one daily file", count)
	}
}

func TestUnwritableUnsafeAndReplacedPathsFallbackWithoutTouchingOthers(t *testing.T) {
	for _, kind := range []string{"parent-symlink", "daily-symlink", "daily-hardlink", "daily-fifo", "not-directory"} {
		t.Run(kind, func(t *testing.T) {
			l, _, stderr := testLogger(t)
			outside := filepath.Join(t.TempDir(), "sentinel")
			if err := os.WriteFile(outside, []byte("keep"), 0600); err != nil {
				t.Fatal(err)
			}
			today := filepath.Join(l.directory, "crg-2026-11-10.log")
			var err error
			switch kind {
			case "parent-symlink":
				target := l.directory
				l.directory = filepath.Join(t.TempDir(), "link")
				err = os.Symlink(target, l.directory)
			case "daily-symlink":
				err = os.Symlink(outside, today)
			case "daily-hardlink":
				err = os.Link(outside, today)
			case "daily-fifo":
				err = syscall.Mkfifo(today, 0600)
			case "not-directory":
				l.directory = outside
			}
			if err != nil {
				t.Fatal(err)
			}
			done := make(chan struct{})
			go func() { l.Event("INFO", "still-running", nil); close(done) }()
			select {
			case <-done:
			case <-time.After(2 * time.Second):
				t.Fatal("blocked on unsafe log destination")
			}
			b, _ := os.ReadFile(outside)
			if string(b) != "keep" || !strings.Contains(stderr.String(), "file_logging_unavailable") || !strings.Contains(stderr.String(), "still-running") {
				t.Fatal(string(b), stderr.String())
			}
		})
	}
}

func TestConcurrentEventsRemainWholeJSONLines(t *testing.T) {
	l, _, _ := testLogger(t)
	var jobs sync.WaitGroup
	for i := 0; i < 8; i++ {
		jobs.Add(1)
		go func() {
			defer jobs.Done()
			for n := 0; n < 25; n++ {
				l.Event("INFO", "concurrent", map[string]int{"n": n})
			}
		}()
	}
	jobs.Wait()
	b, err := os.ReadFile(filepath.Join(l.directory, "crg-2026-11-10.log"))
	if err != nil {
		t.Fatal(err)
	}
	lines := bytes.Split(bytes.TrimSpace(b), []byte("\n"))
	if len(lines) != 200 {
		t.Fatal(len(lines))
	}
	for _, line := range lines {
		if !json.Valid(line) {
			t.Fatal(string(line))
		}
	}
}
