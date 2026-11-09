package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	"github.com/cuipengdba/ContainerResourceGuard/internal/guard"
)

var version = "dev"

func emit(v any) {
	b, e := json.MarshalIndent(v, "", "  ")
	if e == nil {
		fmt.Println(string(b))
	}
}
func main() {
	if e := mainErr(); e != nil {
		emit(map[string]any{"state": "degraded", "error": e.Error(), "business_action": "none"})
		os.Exit(1)
	}
}
func mainErr() error {
	if len(os.Args) < 2 {
		return errors.New("usage: crg doctor|run|status|restore|calibrate|version [options]")
	}
	cmd := os.Args[1]
	if cmd == "version" {
		fmt.Println(version)
		return nil
	}
	f := flag.NewFlagSet(cmd, flag.ContinueOnError)
	config := f.String("config", "", "JSON configuration file")
	percent := f.Float64("percent", 0, "shared CPU/memory/IO percent of host capacity/baseline")
	state := f.String("state-dir", "", "per-container writable state directory")
	profile := f.String("io-profile", "", "explicitly calibrated IO profile")
	once := f.Bool("once", false, "apply or observe once, then exit (limits remain)")
	dir := f.String("directory", "", "existing block-backed directory for calibration")
	output := f.String("output", "/etc/crg/io-profile.json", "calibration JSON output")
	seconds := f.Int("seconds", 3, "seconds per calibration phase (1..30)")
	if e := f.Parse(os.Args[2:]); e != nil {
		return e
	}
	if f.NArg() != 0 {
		return errors.New("unexpected positional arguments; no target containers/PIDs/cgroups are accepted")
	}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	if cmd == "calibrate" {
		if *dir == "" {
			return errors.New("calibrate requires --directory; never benchmarks at business startup")
		}
		p, e := guard.Calibrate(ctx, *dir, *seconds)
		if e != nil {
			return e
		}
		if b, x := os.ReadFile(*output); x == nil {
			var prior guard.Profile
			if x = guard.Decode(b, &prior); x != nil {
				return fmt.Errorf("existing profile invalid; refusing replacement: %w", x)
			}
			if prior.Version != p.Version || prior.Method != p.Method {
				return errors.New("existing profile version/method mismatch")
			}
			for _, old := range prior.Devices {
				if old.Identity != p.Devices[0].Identity {
					p.Devices = append(p.Devices, old)
				}
			}
		} else if !os.IsNotExist(x) {
			return x
		}
		if e = guard.AtomicJSON(*output, p); e != nil {
			return e
		}
		emit(p)
		return nil
	}
	if cmd != "run" && cmd != "doctor" && cmd != "status" && cmd != "restore" {
		return errors.New("unknown command")
	}
	if cmd == "status" {
		path := *state
		if path == "" {
			path = filepath.Join(os.TempDir(), "containerresourceguard")
		}
		b, e := os.ReadFile(filepath.Join(path, "status.json"))
		if e != nil {
			return e
		}
		fmt.Print(string(b))
		return nil
	}
	var c guard.Config
	var e error
	if cmd == "restore" {
		c = guard.Config{Percent: 100}
		if *state != "" {
			c.StateDir = *state
		}
		if e = c.Validate(); e != nil {
			return e
		}
	} else {
		c, e = guard.ReadConfig(*config, *percent)
		if e != nil {
			return e
		}
	}
	if *state != "" {
		c.StateDir = *state
	}
	if *profile != "" {
		c.IOProfile = *profile
	}
	if e = c.Validate(); e != nil {
		return e
	}
	env, e := guard.Discover()
	if e != nil {
		return e
	}
	if cmd == "doctor" {
		p, e := guard.BuildPlan(c, env, nil)
		if e != nil {
			return e
		}
		emit(p)
		return nil
	}
	engine, lock, e := guard.OpenEngine(c, env)
	if e != nil {
		return e
	}
	defer lock.Close()
	if cmd == "restore" {
		r := engine.Restore()
		emit(r)
		_ = guard.AtomicJSON(filepath.Join(c.StateDir, "status.json"), r)
		if r.State != "restored" {
			return errors.New("restore incomplete; external values or permissions retained")
		}
		return nil
	}
	ticker := time.NewTicker(time.Duration(c.IntervalSeconds) * time.Second)
	defer ticker.Stop()
	lastOutput := ""
	for {
		if e = guard.VerifyIdentity(env); e != nil {
			return e
		}
		p, e := guard.BuildPlan(c, env, engine.Originals())
		if e != nil {
			return e
		}
		r := engine.Apply(p)
		if e = guard.AtomicJSON(filepath.Join(c.StateDir, "status.json"), r); e != nil {
			return fmt.Errorf("status persistence failed; no further writes: %w", e)
		}
		// Emit changes, not repeated permission errors every interval.
		stable := r
		stable.TimeUTC = ""
		b, _ := json.Marshal(stable)
		if string(b) != lastOutput {
			emit(r)
			lastOutput = string(b)
		}
		if *once {
			return nil
		}
		select {
		case <-ctx.Done():
			return nil
		case <-ticker.C:
		}
	}
}
