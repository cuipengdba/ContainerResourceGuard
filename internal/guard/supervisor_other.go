//go:build !linux

package guard

import "errors"

func verifySupervisorMetadata(string) error {
	return errors.New("supervisor maintenance requires Linux")
}
