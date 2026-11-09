package guard

import (
	"os"
	"path/filepath"
)

type AccessCheck struct {
	File         string `json:"file"`
	OpenWritable bool   `json:"open_writable"`
	Detail       string `json:"detail"`
}

type Preflight struct {
	Plan
	Checks   []AccessCheck `json:"checks"`
	Disabled bool          `json:"disabled"`
}

// Opening/closing without writing is a preflight, never proof that a kernel
// limit write will succeed. Do not remount or enable ancestor controllers.
func CheckPreflight(c Config, env Environment) (Preflight, error) {
	p, err := BuildPlan(c, env, nil)
	r := Preflight{Plan: p}
	if err != nil {
		return r, err
	}
	r.Disabled, err = IsDisabled(c, env)
	if err != nil {
		return r, err
	}
	for _, name := range []string{"cpu.max", "memory.max", "io.max"} {
		i := AccessCheck{File: name, Detail: "open permitted; actual write/readback still required"}
		f, err := os.OpenFile(filepath.Join(env.Target, name), os.O_WRONLY, 0)
		if err != nil {
			i.Detail = err.Error()
		} else {
			i.OpenWritable = true
			f.Close()
		}
		r.Checks = append(r.Checks, i)
	}
	return r, nil
}
