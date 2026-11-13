//go:build linux && amd64

package main

import (
	"encoding/json"
	"errors"
	"io"
)

const maximumReportBytes = 32 << 20

type reportFile interface {
	io.Writer
	Sync() error
	Close() error
}

type reportOutputError struct {
	stage string
	cause error
}

func (e *reportOutputError) Error() string { return e.stage }
func (e *reportOutputError) Unwrap() error { return e.cause }

// The byte bound includes the newline. Oversized reports write no partial JSON.
// A failed output is reported by the caller and never counts as a complete report.
func persistBoundedReport(f reportFile, value any, maximum int) (int, error) {
	data, err := json.Marshal(value)
	size := 0
	if err != nil {
		err = &reportOutputError{"REPORT_ENCODE", err}
	} else {
		size = len(data) + 1
		if maximum < 1 || size > maximum {
			err = &reportOutputError{"REPORT_OUTPUT_BOUND", errors.New("encoded JSON exceeds the fixed output bound")}
		} else {
			data = append(data, '\n')
			n, writeErr := f.Write(data)
			if writeErr != nil {
				err = &reportOutputError{"REPORT_WRITE", writeErr}
			} else if n != len(data) {
				err = &reportOutputError{"REPORT_WRITE", io.ErrShortWrite}
			}
		}
	}
	if err == nil {
		if syncErr := f.Sync(); syncErr != nil {
			err = &reportOutputError{"REPORT_SYNC", syncErr}
		}
	}
	if closeErr := f.Close(); err == nil && closeErr != nil {
		err = &reportOutputError{"REPORT_CLOSE", closeErr}
	}
	return size, err
}
