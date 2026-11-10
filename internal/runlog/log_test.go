package runlog

import (
	"encoding/json"
	"strings"
	"testing"
	"time"
)

func TestDailyNamesAndBoundedJSONLines(t *testing.T) {
	for _, s := range []string{"crg-2026-11-10.log", "crg-2024-02-29.log"} {
		if _, ok := dailyDate(s); !ok {
			t.Fatal(s)
		}
	}
	for _, s := range []string{"crg-2026-02-29.log", "other-2026-11-10.log", "crg-2026-11-10.log.1", "crg-2026-11-10.log/../x", "crg-2026-11-31.log"} {
		if _, ok := dailyDate(s); ok {
			t.Fatal(s)
		}
	}
	b := encode(time.Now(), "INFO", "status", map[string]string{"untrusted": "line1\nline2"})
	if !json.Valid(b) || strings.Count(string(b), "\n") != 1 {
		t.Fatal(string(b))
	}
	b = encode(time.Now(), "INFO", "status", strings.Repeat("x", MaximumEntryBytes*2))
	if !json.Valid(b) || len(b) > MaximumEntryBytes || !strings.Contains(string(b), "details_omitted") {
		t.Fatal(len(b))
	}
}
