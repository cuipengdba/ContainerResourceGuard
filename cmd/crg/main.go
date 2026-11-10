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
	"sort"
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
			emit(failureOutput(e))
		}
		os.Exit(1)
	}
}
func mainErr() (result error) {
	stage := "usage_invalid"
	defer func() {
		if result == nil {
			return
		}
		var reported reportedError
		if errors.As(result, &reported) {
			return
		}
		result = &commandError{commandFailureReason(result, stage), result}
	}()
	if len(os.Args) < 2 {
		return errors.New("usage: crg doctor|preflight|run|status|diagnose|upgrade-check|state-backup|quiesce|binary-install|binary-rollback|supervisor-plan|supervisor-install|supervisor-uninstall|reload|disable|enable|restore|calibrate|profile-check|profile-merge|version|build-info [options]")
	}
	cmd := os.Args[1]
	if cmd == "version" {
		fmt.Println(version)
		return nil
	}
	if cmd == "build-info" {
		emit(map[string]any{"version": version, "revision": revision, "os": runtime.GOOS, "arch": runtime.GOARCH, "go_version": runtime.Version(),
			"lock_protocol": guard.LockProtocol, "journal_versions": []int{1}, "io_profile_versions": []int{1, 2},
			"writer_controls": []string{"cpu.max", "cpu.weight", "io.max", "io.weight", "memory.max", "memory.high", "memory.swap.max", "pids.max"}})
		return nil
	}
	f := flag.NewFlagSet(cmd, flag.ContinueOnError)
	config := f.String("config", "", "JSON configuration file")
	percent := f.Float64("percent", 0, "shared CPU/memory/IO percent of host capacity/baseline")
	state := f.String("state-dir", "", "per-container writable state directory")
	profile := f.String("io-profile", "", "explicitly calibrated IO profile")
	once := f.Bool("once", false, "apply or observe once, then exit (limits remain)")
	dir := f.String("directory", "", "optional calibration directory override; default selects largest eligible filesystem")
	output := f.String("output", "/etc/crg/io-profile.json", "calibration JSON output")
	seconds := f.Int("seconds", 3, "seconds per calibration phase (1..30)")
	samples := f.Int("samples", 3, "calibration repetitions (1..9)")
	mergeProfile := f.String("merge-profile", "", "second explicit profile for offline merge")
	replaceProfile := f.Bool("replace", false, "explicitly replace matching identities during profile merge")
	format := f.String("format", "json", "output format: json or human (status, doctor, preflight)")
	installDir := f.String("install-dir", "", "dedicated per-container existing CRG installation directory")
	backupDir := f.String("backup-dir", "", "private binary recovery directory; fresh for installation")
	previousSHA := f.String("previous-sha256", "", "trusted expected installed binary SHA256")
	candidateSHA := f.String("candidate-sha256", "", "trusted expected running candidate SHA256")
	supervisorPath := f.String("supervisor", "", "explicit existing supervisor file in this container")
	supervisorSHA := f.String("supervisor-sha256", "", "trusted expected original supervisor SHA256")
	helperPath := f.String("helper", "", "existing optional helper file")
	helperSHA := f.String("helper-sha256", "", "trusted expected optional helper SHA256")
	agentPath := f.String("agent-binary", "", "existing per-container CRG binary")
	agentSHA := f.String("agent-sha256", "", "trusted expected CRG binary SHA256")
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
	if cmd == "profile-check" || cmd == "profile-merge" {
		stage = "profile_operation_failed"
		path := *profile
		if path == "" {
			path = "/etc/crg/io-profile.json"
		}
		p, err := guard.LoadProfile(path)
		if err != nil {
			return err
		}
		if cmd == "profile-check" {
			v, err := guard.InspectProfile(p)
			if err != nil {
				return err
			}
			emit(v)
			return nil
		}
		if *mergeProfile == "" {
			return errors.New("profile-merge requires --merge-profile; default is preview without writes")
		}
		addition, err := guard.LoadProfile(*mergeProfile)
		if err != nil {
			return err
		}
		merged, err := guard.MergeProfiles(p, addition, *replaceProfile)
		if err != nil {
			return err
		}
		persist := false
		f.Visit(func(v *flag.Flag) {
			if v.Name == "output" {
				persist = true
			}
		})
		if persist {
			if err = guard.AtomicJSON(*output, merged); err != nil {
				return err
			}
		}
		emit(map[string]any{"profile": merged, "persisted": persist})
		return nil
	}
	if cmd == "calibrate" {
		stage = "calibration_failed"
		if *dir == "" {
			selection, err := guard.SelectCalibrationDirectory()
			if err != nil {
				return err
			}
			*dir = selection.Directory
		}
		if e := guard.CalibrationOutputReady(*output); e != nil {
			return e
		}
		p, e := guard.CalibrateRepeated(ctx, *dir, *seconds, *samples)
		if e != nil {
			return e
		}
		if b, x := guard.ReadBoundedFile(*output); x == nil {
			var prior guard.Profile
			if x = guard.Decode(b, &prior); x != nil {
				return fmt.Errorf("existing profile invalid; refusing replacement: %w", x)
			}
			p, x = guard.MergeProfiles(prior, p, true)
			if x != nil {
				return fmt.Errorf("existing profile rejected; refusing replacement: %w", x)
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
	if cmd != "run" && cmd != "doctor" && cmd != "preflight" && cmd != "status" && cmd != "diagnose" && cmd != "upgrade-check" && cmd != "state-backup" && cmd != "binary-install" && cmd != "binary-rollback" && cmd != "supervisor-plan" && cmd != "supervisor-install" && cmd != "supervisor-uninstall" && cmd != "quiesce" && cmd != "reload" && cmd != "restore" && cmd != "disable" && cmd != "enable" {
		return errors.New("unknown command")
	}
	var c guard.Config
	var e error
	stage = "config_invalid"
	if cmd == "reload" || ((cmd == "restore" || cmd == "status" || cmd == "diagnose" || cmd == "upgrade-check" || cmd == "state-backup" || cmd == "quiesce" || cmd == "disable" || cmd == "enable") && *config == "") {
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
	stage = "discovery_failed"
	env, e := guard.Discover()
	if e != nil {
		return e
	}
	if cmd == "supervisor-plan" || cmd == "supervisor-install" || cmd == "supervisor-uninstall" {
		stage = "supervisor_maintenance_failed"
		if *config == "" || *supervisorPath == "" {
			return errors.New("supervisor maintenance requires explicit --config and --supervisor")
		}
		o := guard.SupervisorOptions{Path: *supervisorPath, SourceSHA256: *supervisorSHA, Helper: *helperPath, HelperSHA256: *helperSHA, Binary: *agentPath, BinarySHA256: *agentSHA, Config: *config, BackupDir: *backupDir}
		var plan guard.SupervisorPlan
		var err error
		switch cmd {
		case "supervisor-plan":
			plan, err = guard.PreviewSupervisor(ctx, c, o)
		case "supervisor-install":
			plan, err = guard.InstallSupervisor(ctx, c, env, o)
		case "supervisor-uninstall":
			plan, err = guard.UninstallSupervisor(ctx, c, env, *supervisorPath, *backupDir)
		}
		if err != nil {
			return err
		}
		emit(map[string]any{"plan": plan, "business_action": "none", "limits_action": "none", "detail": "maintenance never starts/stops business, never restores/deletes resource state; private supervisor backup may contain secrets"})
		return nil
	}
	if cmd == "binary-install" || cmd == "binary-rollback" {
		stage = "binary_maintenance_failed"
		if *config == "" || *installDir == "" || *backupDir == "" {
			return errors.New("binary maintenance requires explicit --config, --install-dir and --backup-dir")
		}
		var receipt guard.BinaryReceipt
		var err error
		if cmd == "binary-install" {
			receipt, err = guard.InstallOwnBinary(ctx, c, env, *installDir, *backupDir, *previousSHA, *candidateSHA)
		} else {
			receipt, err = guard.RollbackBinary(c, env, *installDir, *backupDir)
		}
		if err != nil {
			return err
		}
		emit(map[string]any{"state": receipt.State, "previous_sha256": receipt.PreviousSHA256, "candidate_sha256": receipt.CandidateSHA256, "limits_action": "retained", "business_action": "none", "detail": "remains quiescent; explicitly enable after verification; recovery receipt and state backup are private"})
		return nil
	}
	if cmd == "upgrade-check" || cmd == "state-backup" {
		stage = "upgrade_check_failed"
		if cmd == "state-backup" {
			stage = "state_backup_failed"
		}
		if cmd == "upgrade-check" {
			check, err := guard.CheckUpgrade(c, env)
			if err != nil {
				return err
			}
			emit(check)
			return nil
		}
		explicitOutput := false
		f.Visit(func(v *flag.Flag) {
			if v.Name == "output" {
				explicitOutput = true
			}
		})
		if !explicitOutput {
			return errors.New("state-backup requires explicit --output outside the state directory; private originals and identities are included")
		}
		check, err := guard.BackupUpgradeState(c, env, *output)
		if err != nil {
			return err
		}
		emit(map[string]any{"state": "written", "maximum_bytes": 4 * guard.MaxJSONBytes, "check": check, "content": "private journal/disable marker/profile; keep existing configuration and supervisor backups separately"})
		return nil
	}
	if cmd == "diagnose" {
		stage = "diagnostic_failed"
		var snapshot *guard.StatusView
		if v, err := guard.ReadStatus(c, env); err == nil {
			snapshot = &v
		}
		bundle := guard.BuildDiagnosticBundle(env, snapshot, guard.RealFiles{})
		encoded, err := guard.EncodeDiagnosticBundle(bundle)
		if err != nil {
			return err
		}
		persist := false
		f.Visit(func(v *flag.Flag) {
			if v.Name == "output" {
				persist = true
			}
		})
		if !persist {
			fmt.Print(string(encoded))
			return nil
		}
		if err = guard.WriteDiagnosticFile(*output, c, bundle); err != nil {
			return err
		}
		emit(map[string]any{"state": "written", "bytes": len(encoded), "maximum_bytes": guard.DiagnosticMaxBytes, "included": guard.DiagnosticContents()})
		return nil
	}
	if cmd == "reload" {
		stage = "reload_request_failed"
		request, err := guard.RequestReload(c, env, *config)
		if err != nil {
			return err
		}
		emit(map[string]any{"state": "requested", "request_id": request.RequestID, "detail": "inspect status.configuration and individual resource results for acceptance and application"})
		return nil
	}
	if cmd == "status" {
		stage = "status_unavailable"
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
		stage = "preflight_failed"
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
		stage = "plan_failed"
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
	stage = cmd + "_failed"
	if cmd == "run" {
		stage = "runtime_failed"
		disabled, err := guard.IsDisabled(c, env)
		if err != nil {
			return fmt.Errorf("cannot check disable marker; refusing writes: %w", err)
		}
		if disabled {
			emit(map[string]any{"state": "disabled", "business_action": "none"})
			return nil
		}
	}
	if cmd == "disable" || cmd == "quiesce" {
		stage = cmd + "_failed"
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
		if (cmd != "disable" && cmd != "quiesce") || !errors.Is(e, guard.ErrLocked) || time.Now().After(deadline) {
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
	if cmd == "quiesce" {
		// OpenEngine holds both existing writer locks. Leave every original,
		// applied/pending value and kernel control untouched for the upgrade.
		// Do not replace the last resource snapshot with an invented plan.
		emit(map[string]any{"state": "quiesced", "owned_mutations": len(engine.Journal.Mutations), "limits_action": "retained", "business_action": "none", "detail": "current-identity disable marker persisted and writer locks acquired; last resource snapshot/journal retained; enable resumes the optional helper on its next retry"})
		return nil
	}
	if cmd == "enable" {
		stage = "enable_failed"
		if err := guard.Enable(c); err != nil {
			return err
		}
		emit(map[string]any{"state": "enabled", "detail": "optional helper may restart CRG on its next retry; business is unchanged"})
		return nil
	}
	if cmd == "restore" || cmd == "disable" {
		stage = "restore_failed"
		r := engine.Restore()
		// Explicit restore/disable may wait a bounded period for an opt-in
		// stability window. This command is never a business startup gate.
		windowDeadline := time.Now().Add(time.Duration(c.MemoryStableSeconds+3) * time.Second)
		for guard.MemoryWindowPending(r) && time.Now().Before(windowDeadline) {
			select {
			case <-ctx.Done():
				return ctx.Err()
			case <-time.After(time.Second):
			}
			if err := guard.VerifyIdentity(env); err != nil {
				return err
			}
			r = engine.Restore()
		}
		if cmd == "disable" {
			r.Mode = "disable"
		}
		if err := guard.AtomicJSON(filepath.Join(c.StateDir, "status.json"), r); err != nil {
			r.State, r.Error = "degraded", err.Error()
		}
		if r.State != "restored" {
			emitIncompleteRestore(r)
			return reportedError{"restore incomplete; external values or permissions retained"}
		}
		emit(r)
		return nil
	}
	// This process is optional and started asynchronously by the existing
	// supervisor. Calibration never gates business/cache startup or their exit.
	automaticIO := guard.PrepareAutomaticIO(ctx, c, env)
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
	metrics := guard.MetricsWriter{}
	events := guard.EventWriter{}
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
		if c.ResourceMode == "percent" && c.Mode == "enforce" && c.IOCalibration == "auto" && automaticIO != nil && c.IOProfile == automaticIO.Profile {
			r.AutomaticIO = automaticIO
			if automaticIO.State == "degraded" {
				r.State = "degraded"
				if r.Error != "" {
					r.Error += "; "
				}
				r.Error += automaticIO.Detail
			}
		}
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
		r.Metrics = metrics.Write(c, engine, r, time.Now())
		r.Events = events.Write(c, r, time.Now())
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
	if v.Events != nil {
		fmt.Printf("Local events: %s (%s)\n", v.Events.State, v.Events.Detail)
	}
	fmt.Printf("State: %s; mode: %s; snapshot age: %ds; writer lock held: %t\n", v.State, v.Mode, v.SnapshotAgeSeconds, v.WriterLockHeld)
	if v.Metrics != nil {
		fmt.Printf("Local metrics: %s (%s)\n", v.Metrics.State, v.Metrics.Detail)
	}
	if v.Mode == "restore" || v.Mode == "disable" {
		fmt.Printf("Cgroup: %s\n", v.Plan.Environment.Target)
	} else {
		humanPlan(v.Plan)
	}
	for _, i := range v.Items {
		fmt.Printf("Result %s %s: %s [%s] (%s)\n", i.File, i.Device, i.State, i.ReasonCode, i.Detail)
	}
	for _, i := range v.Actual {
		fmt.Printf("Actual %s %s: %s %s\n", i.File, i.Device, i.Value, i.Detail)
	}
	if v.Memory != nil {
		fmt.Printf("Live memory sample: %s (overlapping counters; do not sum)\n", v.Memory.SampledUTC)
		for name, value := range map[string]*uint64{"memory.current": v.Memory.CurrentBytes, "memory.swap.current": v.Memory.SwapCurrentBytes} {
			if value != nil {
				fmt.Printf("%s: %d bytes\n", name, *value)
			}
		}
		names := make([]string, 0, len(v.Memory.StatBytes))
		for name := range v.Memory.StatBytes {
			names = append(names, name)
		}
		sort.Strings(names)
		for _, name := range names {
			fmt.Printf("memory.stat.%s: %d bytes\n", name, v.Memory.StatBytes[name])
		}
		for _, name := range []string{"low", "high", "max", "oom", "oom_kill", "oom_group_kill", "sock_throttled"} {
			if value, ok := v.Memory.Events[name]; ok {
				fmt.Printf("memory.events.%s: %d\n", name, value)
			}
		}
		for _, name := range []string{"some", "full"} {
			if value, ok := v.Memory.Pressure[name]; ok {
				fmt.Printf("memory.pressure.%s: avg10=%.2f%% avg60=%.2f%% avg300=%.2f%% total=%d us\n", name, value.Avg10, value.Avg60, value.Avg300, value.TotalMicros)
			}
		}
		for _, name := range v.Memory.Unavailable {
			fmt.Printf("Memory statistic unavailable: %s\n", name)
		}
	}
}
