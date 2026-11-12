//go:build linux && amd64

package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"io"
	"math"
	"strings"
	"testing"
)

type outputFake struct {
	bytes.Buffer
	short                       bool
	writeErr, syncErr, closeErr error
	writes, syncs, closes       int
}

func (f *outputFake) Write(p []byte) (int, error) {
	f.writes++
	if f.writeErr != nil {
		return 0, f.writeErr
	}
	if f.short {
		return len(p) - 1, nil
	}
	return f.Buffer.Write(p)
}
func (f *outputFake) Sync() error  { f.syncs++; return f.syncErr }
func (f *outputFake) Close() error { f.closes++; return f.closeErr }

func TestReportCompactEncodingRetainsEveryFieldAndRecord(t *testing.T) {
	value := map[string]any{"events": []any{map[string]any{"monotonic_ns": uint64(1455673947085467), "kind": "one"}, map[string]any{"kind": "two"}}, "incomplete": false}
	compact, e := json.Marshal(value)
	if e != nil {
		t.Fatal(e)
	}
	indented, e := json.MarshalIndent(value, "", "  ")
	if e != nil {
		t.Fatal(e)
	}
	f := &outputFake{}
	n, e := persistBoundedReport(f, value, len(compact)+1)
	if e != nil || n != len(compact)+1 || !bytes.Equal(f.Bytes(), append(compact, '\n')) || n >= len(indented) || f.writes != 1 || f.syncs != 1 || f.closes != 1 {
		t.Fatalf("report not exact, durable, compact: %d %v", n, e)
	}
	var decoded map[string]json.RawMessage
	if e = json.Unmarshal(f.Bytes(), &decoded); e != nil || len(decoded) != 2 {
		t.Fatal("incomplete JSON")
	}
}

func TestReportExact32MiBBoundAndOneByteOverflow(t *testing.T) {
	// JSON quotes and the newline account for the remaining three bytes.
	value := strings.Repeat("x", maximumReportBytes-3)
	f := &outputFake{}
	n, e := persistBoundedReport(f, value, maximumReportBytes)
	if e != nil || n != maximumReportBytes || f.Len() != n || f.syncs != 1 || f.closes != 1 {
		t.Fatal("exact bound rejected")
	}
	f = &outputFake{}
	n, e = persistBoundedReport(f, value+"x", maximumReportBytes)
	if e == nil || e.Error() != "REPORT_OUTPUT_BOUND" || n != maximumReportBytes+1 || f.Len() != 0 || f.writes != 0 || f.syncs != 0 || f.closes != 1 {
		t.Fatal("oversize silently succeeded or wrote partial JSON")
	}
}

func TestReportAllOutputFailuresAreExplicitAndCloseKeepsFirstError(t *testing.T) {
	primary := errors.New("first")
	secondary := errors.New("close")
	for _, v := range []struct {
		name  string
		f     outputFake
		value any
		limit int
		want  string
		cause error
	}{
		{"encode", outputFake{closeErr: secondary}, math.NaN(), 128, "REPORT_ENCODE", nil},
		{"bound", outputFake{closeErr: secondary}, "data", 2, "REPORT_OUTPUT_BOUND", nil},
		{"invalid-bound", outputFake{}, "data", 0, "REPORT_OUTPUT_BOUND", nil},
		{"short", outputFake{short: true, closeErr: secondary}, "data", 128, "REPORT_WRITE", io.ErrShortWrite},
		{"write", outputFake{writeErr: primary, closeErr: secondary}, "data", 128, "REPORT_WRITE", primary},
		{"sync", outputFake{syncErr: primary, closeErr: secondary}, "data", 128, "REPORT_SYNC", primary},
		{"close", outputFake{closeErr: primary}, "data", 128, "REPORT_CLOSE", primary},
	} {
		t.Run(v.name, func(t *testing.T) {
			_, e := persistBoundedReport(&v.f, v.value, v.limit)
			if e == nil || e.Error() != v.want || v.f.closes != 1 {
				t.Fatalf("failure hidden: %v", e)
			}
			if v.cause != nil && !errors.Is(e, v.cause) {
				t.Fatal("original output failure replaced")
			}
		})
	}
}
