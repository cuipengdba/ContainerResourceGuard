//go:build linux && amd64

package main

// A deterministic half-installed pair is available only for a directly owned
// disposable probe. It cannot be enabled for any vendor fixture.
func validPairAttachPause(p Plan) bool {
	if p.PairAttachPause == 0 {
		return true
	}
	return p.PairAttachPause == 500 && p.Vendor == nil && p.Duration == 15 && p.ReaderDelay == 0
}
