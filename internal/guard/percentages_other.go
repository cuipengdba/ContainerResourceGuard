//go:build !linux

package guard

import "errors"

func readPercentCapacity(string) (string, error) { return "", errors.New("Linux procfs required") }
