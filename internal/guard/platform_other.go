//go:build !linux

package guard

import (
	"errors"
	"os"
)

func verifyCgroup(string) error            { return errors.New("Linux required") }
func groupIdentity(string) (string, error) { return "", errors.New("Linux required") }
func lockFile(string) (*os.File, error)    { return nil, errors.New("Linux required") }
func fileDevice(string) (string, error)    { return "", errors.New("Linux required") }
