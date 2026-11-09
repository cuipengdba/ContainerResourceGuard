//go:build !linux

package guard

import (
	"errors"
	"os"
)

func verifyCgroup(string) error                    { return errors.New("Linux required") }
func groupIdentity(string) (string, error)         { return "", errors.New("Linux required") }
func lockFile(string) (*os.File, error)            { return nil, errors.New("Linux required") }
func lockGroup(string) (*os.File, error)           { return nil, errors.New("Linux required") }
func lockExistingState(string) (*os.File, error)   { return nil, errors.New("Linux required") }
func fileDevice(string) (string, error)            { return "", errors.New("Linux required") }
func openConfigFile(path string) (*os.File, error) { return os.Open(path) }

func openStateJSONFile(path string) (*os.File, error) {
	st, err := os.Lstat(path)
	if err != nil {
		return nil, err
	}
	if !st.Mode().IsRegular() {
		return nil, errors.New("state JSON must be a regular file")
	}
	return os.Open(path)
}

func verifyCapacitySource(string, string) error { return errors.New("Linux required") }
