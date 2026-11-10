//go:build linux

package guard

import (
	"errors"
	"os"
	"syscall"
)

func readPercentCapacity(path string) (string, error) {
	var s syscall.Statfs_t
	if err := syscall.Statfs(path, &s); err != nil {
		return "", err
	}
	if s.Type != 0x9fa0 {
		return "", errors.New("percentage capacity requires real procfs")
	}
	b, err := os.ReadFile(path)
	return string(b), err
}
