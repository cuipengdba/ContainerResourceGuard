//go:build !linux

package guard

import "errors"

func SelectCalibrationDirectory() (CalibrationSelection, error) {
	return CalibrationSelection{}, errors.New("Linux required")
}
