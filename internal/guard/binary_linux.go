//go:build linux

package guard

import (
	"crypto/sha256"
	"hash"
	"os"
)

func newBinaryHash() hash.Hash             { return sha256.New() }
func openRunningBinary() (*os.File, error) { return os.Open("/proc/self/exe") }
