package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"math"
	"os"
	"os/signal"
	"path/filepath"
	"runtime"
	"syscall"
	"time"

	"github.com/cuipengdba/ContainerResourceGuard/internal/guard"
)

var version = "dev"
var revision = "unknown"

type reportedError struct{ message string }

func (e reportedError) Error() string { return e.message }

func emit(v any) {
	b, e := json.MarshalIndent(v, "", "  ")
	if e == nil {
		fmt.Println(string(b))
	}
}
func main() {
	if e := mainErr(); e != nil {
		var reported reportedError
		if !errors.As(e, &reported) {
			emit(map[string]any{"state": "degraded", "error": e.Error(), "business_action": "none"})
		}
		os.Exit(1)
	}
}
func mainErr() error {
	if len(os.Args) < 2 {
		return errors.New("usage: crg doctor|preflight|run|status|reload|disable|enable|restore|calibrate|version|build-info [options]")
	}
	cmd := os.Args[1]
	if cmd == "version" {
		fmt.Println(version)
		return nil
	}
	if cmd == "build-info" {
		emit(map[string]string{"version": version, "revision": revision, "os": runtime.GOOS, "arch": runtime.GOARCH})
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
	format := f.String("format", "json", "output format: json or human (status, doctor, preflight)")
	if e := f.Parse(os.Args[2:]); e != nil {
		return e
	}
	percentProvided := false
	f.Visit(func(v *flag.Flag) {
		if v.Name == "percent" {
			percentProvided = true
		}
	})
	if percentProvided && (*percent <= 0 || *percent > 100 || math.IsNaN(*percent) || math.IsInf(*percent, 0)) {
		return errors.New("percent must be greater than 0 and at most 100")
	}
	if f.NArg() != 0 {
		return errors.New("unexpected positional arguments; no target containers/PIDs/cgroups are accepted")
	}
	if *format != "json" && *format != "human" {
		return errors.New("format must be json or human")
	}
	if *format == "human" && cmd != "status" && cmd != "doctor" && cmd != "preflight" {
		return errors.New("human format supported for status/doctor/preflight")
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
	if cmd != "run" && cmd != "doctor" && cmd != "preflight" && cmd != "status" && cmd != "reload" && cmd != "restore" && cmd != "disable" && cmd != "enable" {
		return errors.New("unknown command")
	}
	var c guard.Config
	var e error
	if cmd == "reload" || ((cmd == "restore" || cmd == "status" || cmd == "disable" || cmd == "enable") && *config == "") {
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
	if cmd == "reload" {
		request, err := guard.RequestReload(c, env, *config)
		if err != nil {
			return err
		}
		emit(map[string]any{"state": "requested", "request_id": request.RequestID, "detail": "inspect status.configuration and individual resource results for acceptance and application"})
		return nil
	}
	if cmd == "status" {
		v, err := guard.ReadStatus(c, env)
		if err != nil {
			return err
		}
		if *format == "human" {
			humanStatus(v)
		} else {
			emit(v)
		}
		return nil
	}
	if cmd == "preflight" {
		v, err := guard.CheckPreflight(c, env)
		if err != nil {
			return err
		}
		if *format == "human" {
			humanPlan(v.Plan)
			fmt.Printf("Disabled: %t\n", v.Disabled)
			for _, i := range v.Checks {
				fmt.Printf("%s open_writable=%t: %s\n", i.File, i.OpenWritable, i.Detail)
			}
		} else {
			emit(v)
		}
		return nil
	}
	if cmd == "doctor" {
		p, e := guard.BuildPlan(c, env, nil)
		if e != nil {
			return e
		}
		if *format == "human" {
			humanPlan(p)
		} else {
			emit(p)
		}
		return nil
	}
	if cmd == "run" {
		disabled, err := guard.IsDisabled(c, env)
		if err != nil {
			return fmt.Errorf("cannot check disable marker; refusing writes: %w", err)
		}
		if disabled {
			emit(map[string]any{"state": "disabled", "business_action": "none"})
			return nil
		}
	}
	if cmd == "disable" {
		if err := guard.Disable(c, env); err != nil {
			return fmt.Errorf("cannot persist disable marker: %w", err)
		}
	}
	var engine *guard.Engine
	var lock *guard.Locks
	deadline := time.Now().Add(5 * time.Second)
	for {
		engine, lock, e = guard.OpenEngine(c, env)
		if e == nil {
			break
		}
		if cmd != "disable" || !errors.Is(e, guard.ErrLocked) || time.Now().After(deadline) {
			return e
		}
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(100 * time.Millisecond):
		}
	}
	if e != nil {
		return e
	}
	defer lock.Close()
	if err := guard.VerifyIdentity(env); err != nil {
		return err
	}
	if cmd == "enable" {
		if err := guard.Enable(c); err != nil {
			return err
		}
		emit(map[string]any{"state": "enabled", "detail": "optional helper may restart CRG on its next retry; business is unchanged"})
		return nil
	}
	if cmd == "restore" || cmd == "disable" {
		r := engine.Restore()
		if cmd == "disable" {
			r.Mode = "disable"
		}
		if err := guard.AtomicJSON(filepath.Join(c.StateDir, "status.json"), r); err != nil {
			r.State, r.Error = "degraded", err.Error()
		}
		emit(r)
		if r.State != "restored" {
			return reportedError{"restore incomplete; external values or permissions retained"}
		}
		return nil
	}
	overrides := guard.ConfigOverrides{StateDir: *state, IOProfile: *profile}
	if percentProvided {
		overrides.Percent = *percent
	}
	watcher, err := guard.NewConfigWatcher(*config, c, overrides)
	if err != nil {
		return err
	}
	live, err := guard.StartReload(c, env, watcher.Path)
	if err != nil {
		return fmt.Errorf("cannot persist reload runtime; refusing writes: %w", err)
	}
	ticker := time.NewTicker(time.Duration(c.IntervalSeconds) * time.Second)
	defer ticker.Stop()
	control := time.NewTicker(time.Second)
	defer control.Stop()
	writer := guard.StatusWriter{Path: filepath.Join(c.StateDir, "status.json")}
	lastOutput := ""
	requestID, controlError := "", ""
	forceReload := false
	for {
		if disabled, err := guard.IsDisabled(c, env); err != nil {
			return err
		} else if disabled {
			return nil
		}
		if e = guard.VerifyIdentity(env); e != nil {
			return e
		}
		watcher.Poll(env, engine.Originals(), forceReload)
		forceReload = false
		if c.IntervalSeconds != watcher.Current.IntervalSeconds {
			ticker.Reset(time.Duration(watcher.Current.IntervalSeconds) * time.Second)
		}
		c = watcher.Current
		engine.Config = c
		p, e := guard.BuildPlan(c, env, engine.Originals())
		if e != nil {
			return e
		}
		r := engine.Reconcile(p)
		configuration := watcher.Revision
		configuration.RequestID = requestID
		r.Configuration = &configuration
		if configuration.State == "rejected" {
			r.State = "degraded"
			r.Error = configuration.Error
		}
		if controlError != "" {
			r.State = "degraded"
			if r.Error != "" {
				r.Error += "; "
			}
			r.Error += controlError
		}
		if _, e = writer.Write(r, time.Now()); e != nil {
			return fmt.Errorf("status persistence failed; no further writes: %w", e)
		}
		// Emit changes, not repeated permission errors every interval.
		stable := guard.StableStatus(r)
		if stable != lastOutput {
			emit(r)
			lastOutput = stable
		}
		if *once {
			return nil
		}
	waitLoop:
		for {
			select {
			case <-ctx.Done():
				return nil
			case <-control.C:
				if disabled, err := guard.IsDisabled(c, env); err != nil {
					return err
				} else if disabled {
					return nil
				}
				id, err := live.PollRequest(c, requestID)
				message := ""
				if err != nil {
					message = err.Error()
				}
				if message != controlError {
					controlError = message
					forceReload = id != ""
					if id != "" {
						requestID = id
					}
					break waitLoop
				}
				if id != "" {
					requestID, forceReload = id, true
					break waitLoop
				}
			case <-ticker.C:
				break waitLoop
			}
		}
	}
}

func humanPlan(p guard.Plan) {
	if p.ResourceMode == "manual" {
		fmt.Println("Requested: manual CPU / memory / per-device IO; omitted dimensions unmanaged")
	} else {
		fmt.Printf("Requested: %.4g%% CPU / memory / calibrated IO\n", p.Percent)
	}
	fmt.Printf("Cgroup: %s\nHost: %d online CPUs, %d bytes memory\n", p.Environment.Target, p.Environment.OnlineCPUs, p.Environment.MemoryBytes)
	for _, s := range p.Settings {
		fmt.Printf("Target %s %s: %s\n", s.File, s.Device, s.Value)
	}
	for _, w := range p.Warnings {
		fmt.Printf("Warning: %s\n", w)
	}
	for _, d := range p.Devices {
		fmt.Printf("IO device %s -> %s: %s (%s)\n", d.ProfileDevice, d.Device, d.State, d.Detail)
	}
	for _, d := range p.Paths {
		fmt.Printf("Data path %s device %s: %s (%s)\n", d.Path, d.Device, d.State, d.Detail)
	}
}

func humanStatus(v guard.StatusView) {
	fmt.Printf("State: %s; mode: %s; snapshot age: %ds; writer lock held: %t\n", v.State, v.Mode, v.SnapshotAgeSeconds, v.WriterLockHeld)
	if v.Mode == "restore" || v.Mode == "disable" {
		fmt.Printf("Cgroup: %s\n", v.Plan.Environment.Target)
	} else {
		humanPlan(v.Plan)
	}
	for _, i := range v.Items {
		fmt.Printf("Result %s %s: %s (%s)\n", i.File, i.Device, i.State, i.Detail)
	}
	for _, i := range v.Actual {
		fmt.Printf("Actual %s %s: %s %s\n", i.File, i.Device, i.Value, i.Detail)
	}
}
