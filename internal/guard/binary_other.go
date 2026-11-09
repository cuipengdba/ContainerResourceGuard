//go:build !linux

package guard

import (
	"crypto/sha256"
	"errors"
	"hash"
	"os"
)

func newBinaryHash() hash.Hash { return sha256.New() }
func openRunningBinary() (*os.File, error) {
	return nil, errors.New("binary installation requires Linux")
}
