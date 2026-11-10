package guard

import (
	"errors"
	"strconv"
	"strings"
)

// Only own the default line. A write of this line leaves administrator/device
// overrides intact. Presence/readback does not prove a weight controller is active.
func defaultIOWeight(text string) (string, error) {
	value := ""
	for _, line := range strings.Split(text, "\n") {
		fields := strings.Fields(line)
		if len(fields) == 0 || fields[0] != "default" {
			continue
		}
		if len(fields) != 2 || value != "" {
			return "", errors.New("invalid or duplicate io.weight default")
		}
		n, err := strconv.ParseUint(fields[1], 10, 64)
		if err != nil || n < 1 || n > 10000 {
			return "", errors.New("invalid io.weight default range")
		}
		value = "default " + strconv.FormatUint(n, 10)
	}
	if value == "" {
		return "", errors.New("io.weight default unavailable; no fallback controller is changed")
	}
	return value, nil
}
