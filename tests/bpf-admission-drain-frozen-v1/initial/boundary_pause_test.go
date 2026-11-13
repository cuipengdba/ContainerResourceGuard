//go:build linux && amd64

package main

import "testing"

func TestQualificationPairPauseRejectsVendorAndUnboundedInputs(t *testing.T) {
	for _, p := range []Plan{{PairAttachPause: 500, Duration: 15}} {
		if !validPairAttachPause(p) {
			t.Fatal("owned deterministic fixture rejected", p)
		}
	}
	for _, p := range []Plan{{PairAttachPause: -1, Duration: 15}, {PairAttachPause: 1, Duration: 15}, {PairAttachPause: 501, Duration: 15}, {PairAttachPause: 500, Duration: 14}, {PairAttachPause: 500, Duration: 1200}, {PairAttachPause: 500, Duration: 15, ReaderDelay: 1}, {PairAttachPause: 500, Duration: 15, Vendor: &VendorScope{}}} {
		if validPairAttachPause(p) {
			t.Fatal("unsafe qualification fixture accepted", p)
		}
	}
	if !validPairAttachPause(Plan{Vendor: &VendorScope{}, Duration: 600}) {
		t.Fatal("disabled hook changes original vendor contract")
	}
}
