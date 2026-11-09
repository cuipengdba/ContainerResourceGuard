package guard

import (
	"bytes"
	"encoding/json"
	"errors"
	"io"
	"math"
	"os"
	"path"
	"path/filepath"
	"strconv"
	"strings"
)

type Config struct {
	Percent         float64 `json:"percent"`
	Mode            string  `json:"mode,omitempty"`
	IOProfile       string  `json:"io_profile,omitempty"`
	StateDir        string  `json:"state_dir,omitempty"`
	IntervalSeconds int     `json:"interval_seconds,omitempty"`
}

func Decode(data []byte, out any) error {
	d := json.NewDecoder(bytes.NewReader(data))
	d.DisallowUnknownFields()
	if err := d.Decode(out); err != nil {
		return err
	}
	var extra any
	if err := d.Decode(&extra); err != io.EOF {
		return errors.New("expected exactly one JSON object")
	}
	return nil
}

func (c *Config) Validate() error {
	if math.IsNaN(c.Percent) || math.IsInf(c.Percent, 0) || c.Percent <= 0 || c.Percent > 100 {
		return errors.New("percent must be greater than 0 and at most 100")
	}
	if c.Mode == "" {
		c.Mode = "enforce"
	}
	if c.Mode != "enforce" && c.Mode != "observe" {
		return errors.New("mode must be enforce or observe")
	}
	if c.IOProfile == "" {
		c.IOProfile = "/etc/crg/io-profile.json"
	}
	if c.StateDir == "" {
		c.StateDir = filepath.Join(os.TempDir(), "containerresourceguard")
	}
	if (!filepath.IsAbs(c.StateDir) && !path.IsAbs(c.StateDir)) || (!filepath.IsAbs(c.IOProfile) && !path.IsAbs(c.IOProfile)) {
		return errors.New("state_dir and io_profile must be absolute paths")
	}
	if c.IntervalSeconds == 0 {
		c.IntervalSeconds = 15
	}
	if c.IntervalSeconds < 1 || c.IntervalSeconds > 3600 {
		return errors.New("interval_seconds must be 1..3600")
	}
	return nil
}

func ReadConfig(path string, percent float64) (Config, error) {
	var c Config
	if path != "" {
		b, e := os.ReadFile(path)
		if e != nil {
			return c, e
		}
		if e = Decode(b, &c); e != nil {
			return c, e
		}
	}
	if percent != 0 {
		c.Percent = percent
	}
	return c, c.Validate()
}

func CountCPUs(s string) (int, error) {
	var n int
	seen := map[int]bool{}
	for _, part := range splitCPU(s) {
		f := strings.Split(part, "-")
		if len(f) > 2 {
			return 0, errors.New("invalid CPU range")
		}
		a, e := strconv.Atoi(f[0])
		if e != nil {
			return 0, e
		}
		b := a
		if len(f) == 2 {
			b, e = strconv.Atoi(f[1])
			if e != nil {
				return 0, e
			}
		}
		if a < 0 || b < a || b > 1048575 {
			return 0, errors.New("invalid CPU range")
		}
		for k := a; k <= b; k++ {
			if !seen[k] {
				seen[k] = true
				n++
			}
		}
	}
	if n == 0 {
		return 0, errors.New("empty CPU list")
	}
	return n, nil
}
