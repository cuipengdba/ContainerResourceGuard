// Package runlog writes private per-container daily logs. Every failure is
// reported on stderr and is deliberately independent of resource mutations.
package runlog

import (
	"encoding/json"
	"fmt"
	"io"
	"sort"
	"strings"
	"sync"
	"time"
)

const DefaultDirectory = "/var/log/crg"
const RetentionDays = 30
const MaximumBytes int64 = 1_000_000_000
const MaximumEntryBytes = 64 * 1024

type record struct {
	Time   string `json:"time"`
	Level  string `json:"level"`
	Event  string `json:"event"`
	Fields any    `json:"fields,omitempty"`
}

type Logger struct {
	mu              sync.Mutex
	directory       string
	stderr          io.Writer
	now             func() time.Time
	maximumBytes    int64
	retentionDays   int
	lastDay         string
	nextMaintenance time.Time
	lastHeartbeat   time.Time
	lastWarning     string
	nextWarning     time.Time
}

func New(directory string, stderr io.Writer) *Logger {
	if directory == "" {
		directory = DefaultDirectory
	}
	if stderr == nil {
		stderr = io.Discard
	}
	return &Logger{directory: directory, stderr: stderr, now: time.Now, maximumBytes: MaximumBytes, retentionDays: RetentionDays}
}

func (l *Logger) SetDirectory(directory string) {
	if directory == "" {
		directory = DefaultDirectory
	}
	l.mu.Lock()
	defer l.mu.Unlock()
	if l.directory != directory {
		l.directory = directory
		l.lastDay = ""
		l.nextMaintenance = time.Time{}
	}
}

func encode(now time.Time, level, event string, fields any) []byte {
	r := record{Time: now.Format(time.RFC3339Nano), Level: level, Event: event, Fields: fields}
	b, err := json.Marshal(r)
	if err != nil || len(b) >= MaximumEntryBytes {
		r.Fields = map[string]any{"details_omitted": true, "encoded_bytes": len(b)}
		b, _ = json.Marshal(r)
	}
	return append(b, '\n')
}

func (l *Logger) Event(level, event string, fields any) {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.eventLocked(l.now(), level, event, fields)
}

func (l *Logger) eventLocked(now time.Time, level, event string, fields any) {
	b := encode(now, level, event, fields)
	_, _ = l.stderr.Write(b)
	l.persistLocked(now, b)
	if l.lastHeartbeat.IsZero() {
		l.lastHeartbeat = now
	}
}

// Tick runs at most once a minute and also rotates a quiet Agent at midnight.
// No extra daemon or external logrotate dependency is required.
func (l *Logger) Tick() {
	l.mu.Lock()
	defer l.mu.Unlock()
	now := l.now()
	day := now.Format("2006-01-02")
	if day == l.lastDay && now.Before(l.nextMaintenance) {
		return
	}
	if day != l.lastDay {
		l.eventLocked(now, "INFO", "log_day_started", nil)
	} else if now.Sub(l.lastHeartbeat) >= 5*time.Minute {
		l.eventLocked(now, "INFO", "agent_heartbeat", nil)
		l.lastHeartbeat = now
	} else {
		l.persistLocked(now, nil)
	}
}

type dailyFile struct {
	name, day string
	size      int64
}

func dailyDate(name string) (string, bool) {
	if len(name) != len("crg-2006-01-02.log") || !strings.HasPrefix(name, "crg-") || !strings.HasSuffix(name, ".log") {
		return "", false
	}
	day := name[4:14]
	d, err := time.Parse("2006-01-02", day)
	return day, err == nil && d.Format("2006-01-02") == day
}

func (l *Logger) persistLocked(now time.Time, b []byte) {
	day := now.Format("2006-01-02")
	l.lastDay = day
	l.nextMaintenance = now.Add(time.Minute)
	if err := l.persist(now, b); err != nil {
		message := err.Error()
		if message != l.lastWarning || !now.Before(l.nextWarning) {
			_, _ = l.stderr.Write(encode(now, "WARN", "file_logging_unavailable", map[string]any{"error": message, "fallback": "stderr", "business_action": "none"}))
			l.lastWarning = message
			l.nextWarning = now.Add(5 * time.Minute)
		}
	} else if l.lastWarning != "" {
		_, _ = l.stderr.Write(encode(now, "INFO", "file_logging_recovered", nil))
		l.lastWarning = ""
	}
}

func (l *Logger) persist(now time.Time, b []byte) error {
	s, err := openSink(l.directory)
	if err != nil {
		return err
	}
	defer s.close()
	files, err := s.files()
	if err != nil {
		return err
	}
	sort.Slice(files, func(i, j int) bool { return files[i].name < files[j].name })
	cutoff := now.AddDate(0, 0, -(l.retentionDays - 1)).Format("2006-01-02")
	today := "crg-" + now.Format("2006-01-02") + ".log"
	var kept []dailyFile
	var total int64
	for _, f := range files {
		if f.day < cutoff {
			if err := s.remove(f.name); err != nil {
				return err
			}
			continue
		}
		if f.size < 0 || f.size > 1<<62 || total > 1<<62-f.size {
			return fmt.Errorf("invalid managed log size")
		}
		total += f.size
		kept = append(kept, f)
	}
	for _, f := range kept {
		if total+int64(len(b)) <= l.maximumBytes {
			break
		}
		if f.name == today {
			continue
		}
		if err := s.remove(f.name); err != nil {
			return err
		}
		total -= f.size
	}
	reset := total+int64(len(b)) > l.maximumBytes
	if reset {
		marker := encode(now, "WARN", "daily_file_reset_size_limit", map[string]any{"maximum_bytes": l.maximumBytes})
		if int64(len(marker)+len(b)) > l.maximumBytes {
			return fmt.Errorf("log entry exceeds available daily budget")
		}
		b = append(marker, b...)
	}
	return s.append(today, b, reset)
}
