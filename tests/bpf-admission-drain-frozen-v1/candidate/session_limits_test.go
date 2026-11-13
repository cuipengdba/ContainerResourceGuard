//go:build linux && amd64

package main

import "testing"

func TestLongDiagnosticDurationBoundaries(t *testing.T) {
	for _, n := range []int{1, 60, 180, 600, 660, 1200} {
		if !validDiagnosticSeconds(n) {
			t.Fatal("valid diagnostic duration rejected", n)
		}
	}
	for _, n := range []int{-1, 0, 1201, int(^uint(0) >> 1)} {
		if validDiagnosticSeconds(n) {
			t.Fatal("invalid diagnostic duration accepted", n)
		}
	}
}
