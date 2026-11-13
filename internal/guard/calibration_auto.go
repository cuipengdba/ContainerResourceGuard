package guard

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// CalibrationSelection describes one filesystem visible to this container.
// Capacity is filesystem total size, not available space or raw disk capacity.
type CalibrationSelection struct {
	Directory      string `json:"directory"`
	Filesystem     string `json:"filesystem"`
	Device         string `json:"device"`
	Identity       string `json:"identity"`
	ControlDevice  string `json:"control_device,omitempty"`
	TotalBytes     uint64 `json:"total_bytes"`
	AvailableBytes uint64 `json:"available_bytes"`
}

type AutomaticIOStatus struct {
	State      string                `json:"state"`
	ReasonCode string                `json:"reason_code,omitempty"`
	Detail     string                `json:"detail,omitempty"`
	Selection  *CalibrationSelection `json:"selection,omitempty"`
	Profile    string                `json:"profile"`
	Quality    *ProfileQuality       `json:"quality,omitempty"`
}

// PrepareAutomaticIO is called once by the optional Agent, under its existing
// per-container writer locks and before it applies its first resource plan.
// It never runs in doctor/preflight/status, observe mode, or manual mode.
func PrepareAutomaticIO(ctx context.Context, c Config, env Environment) *AutomaticIOStatus {
	return prepareAutomaticIO(ctx, c, env, SelectCalibrationDirectory, CalibrateRepeated, ReadBoundedFile, AtomicJSON)
}

func prepareAutomaticIO(ctx context.Context, c Config, env Environment,
	selectDirectory func() (CalibrationSelection, error),
	measure func(context.Context, string, int, int) (Profile, error),
	readProfile func(string) ([]byte, error), save func(string, any) error) *AutomaticIOStatus {
	if c.ResourceMode != "percent" || c.Mode != "enforce" || c.IOCalibration == "off" {
		return nil
	}
	s := &AutomaticIOStatus{State: "degraded", Profile: c.IOProfile}
	fail := func(code string, err error) *AutomaticIOStatus {
		s.ReasonCode, s.Detail = code, err.Error()
		return s
	}
	selected, err := selectDirectory()
	if err != nil {
		return fail("calibration_no_eligible_filesystem", err)
	}
	s.Selection = &selected
	var prior Profile
	if data, err := readProfile(c.IOProfile); err == nil {
		if err = Decode(data, &prior); err == nil {
			err = ValidateProfile(prior)
		}
		if err != nil {
			return fail("calibration_cached_profile_invalid", err)
		}
		for _, d := range prior.Devices {
			if d.Identity == selected.Identity {
				quality := Quality(d)
				s.Quality = &quality
				s.State, s.Detail = "reused", "matching stable device identity; no benchmark performed"
				return s
			}
		}
	} else if !os.IsNotExist(err) {
		return fail("calibration_profile_unreadable", err)
	}
	// An existing cap would measure the inherited cap, rather than a useful
	// unconstrained baseline. Do not temporarily lift anyone's IO limits.
	control := selected.ControlDevice
	if control == "" {
		control = selected.Device
	}
	if err = calibrationUncapped(env.Target, control); err != nil {
		return fail("calibration_existing_io_limit", err)
	}
	if err = calibrationOutputReady(c.IOProfile); err != nil {
		return fail("calibration_output_unwritable", err)
	}
	// The 36 measured seconds exclude three direct-IO file population passes.
	// Allow bounded setup time without shortening samples or gating business.
	bounded, cancel := context.WithTimeout(ctx, 180*time.Second)
	defer cancel()
	p, err := measure(bounded, selected.Directory, 3, 3)
	if err != nil {
		return fail("calibration_measurement_failed", err)
	}
	if err = ValidateProfile(p); err != nil || len(p.Devices) != 1 || p.Devices[0].Identity != selected.Identity || p.Devices[0].Device != selected.Device {
		return fail("calibration_device_changed", errors.New("selected device differs from completed measurement; no profile accepted"))
	}
	quality := Quality(p.Devices[0])
	if len(prior.Devices) > 0 {
		p, err = MergeProfiles(prior, p, true)
		if err != nil {
			return fail("calibration_profile_merge_failed", err)
		}
	}
	if err = bounded.Err(); err != nil {
		return fail("calibration_measurement_failed", err)
	}
	if err = save(c.IOProfile, p); err != nil {
		return fail("calibration_profile_write_failed", err)
	}
	s.Quality = &quality
	s.State, s.Detail = "calibrated", "three samples saved atomically; subsequent starts reuse matching device identity"
	return s
}

func calibrationUncapped(target, device string) error {
	for dir := target; ; dir = filepath.Dir(dir) {
		value, err := read(filepath.Join(dir, "io.max"))
		if os.IsNotExist(err) && dir != target && verifyCgroup(filepath.Dir(dir)) != nil {
			return nil // The cgroup hierarchy root has no io.max of its own.
		}
		if err != nil {
			return fmt.Errorf("cannot verify inherited IO limits: %w", err)
		}
		for _, line := range strings.Split(value, "\n") {
			fields := strings.Fields(line)
			if len(fields) < 2 {
				continue
			}
			// Stack limits can account at a different block layer. Refuse any
			// finite inherited cap instead of guessing that it is unrelated.
			for _, f := range fields[1:] {
				pair := strings.SplitN(f, "=", 2)
				if len(pair) != 2 || pair[1] != "max" {
					return fmt.Errorf("existing IO cap on %s; selected %s is not benchmarked", fields[0], device)
				}
			}
		}
		if dir == filepath.Dir(dir) {
			return nil
		}
		parent := filepath.Dir(dir)
		if err := verifyCgroup(parent); err != nil {
			return nil // Reached the mount root; never read host filesystem io.max.
		}
	}
}

func calibrationOutputReady(path string) error {
	if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
		return err
	}
	f, err := os.CreateTemp(filepath.Dir(path), ".crg-profile-probe-*")
	if err != nil {
		return err
	}
	defer os.Remove(f.Name())
	err = f.Sync()
	closeErr := f.Close()
	if err != nil {
		return err
	}
	return closeErr
}

// CalibrationOutputReady checks the destination before any benchmark IO.
func CalibrationOutputReady(path string) error { return calibrationOutputReady(path) }
