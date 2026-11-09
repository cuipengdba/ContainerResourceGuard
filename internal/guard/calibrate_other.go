//go:build !linux

package guard

import (
	"context"
	"errors"
)

func Calibrate(context.Context, string, int) (Profile, error) {
	return Profile{}, errors.New("Linux required")
}
