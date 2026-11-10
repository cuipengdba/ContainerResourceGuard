package guard

import (
	"errors"
	"os"
	"path/filepath"
)

type DeviceCoverage struct {
	ProfileDevice    string `json:"profile_device"`
	FilesystemDevice string `json:"filesystem_device,omitempty"`
	Device           string `json:"resolved_device,omitempty"`
	State            string `json:"state"`
	Detail           string `json:"detail"`
}
type PathCoverage struct {
	Path          string `json:"path"`
	Device        string `json:"device,omitempty"`
	ControlDevice string `json:"control_device,omitempty"`
	State         string `json:"state"`
	Detail        string `json:"detail"`
}

func pathCoverage(paths []string, settings []Setting) []PathCoverage {
	var r []PathCoverage
	for _, path := range paths {
		i := PathCoverage{Path: path, State: "unmanaged", Detail: "no calibrated limit for the filesystem device; no limit inferred"}
		dev, err := fileDevice(path)
		if err != nil {
			i.Detail = err.Error()
		} else {
			i.Device = dev
			binding, err := ResolveIOBlockDevice(dev)
			if err != nil {
				i.Detail = err.Error()
				r = append(r, i)
				continue
			}
			i.ControlDevice = binding.ControlDevice
			for _, s := range settings {
				if s.File == "io.max" && s.Device == binding.ControlDevice && s.DeviceIdentity == binding.ControlIdentity {
					i.State, i.Detail = "planned", "whole-device shared cap present in plan; actual enforcement requires readback and workload verification"
				}
			}
		}
		r = append(r, i)
	}
	return r
}

func deviceParents(dev string) ([]string, error) {
	root, err := filepath.EvalSymlinks(filepath.Join("/sys/dev/block", dev))
	if err != nil {
		return nil, err
	}
	entries, err := os.ReadDir(filepath.Join(root, "slaves"))
	if err != nil && !os.IsNotExist(err) {
		return nil, err
	}
	var r []string
	for _, v := range entries {
		n, err := read(filepath.Join(root, "slaves", v.Name(), "dev"))
		if err != nil || !validDevice(n) {
			return nil, errors.New("unreadable device stack")
		}
		r = append(r, n)
	}
	if _, err := os.Stat(filepath.Join(root, "partition")); err == nil {
		n, err := read(filepath.Join(filepath.Dir(root), "dev"))
		if err != nil || !validDevice(n) {
			return nil, errors.New("unreadable partition parent")
		}
		r = append(r, n)
	}
	return r, nil
}

func reaches(from, to string, parents func(string) ([]string, error)) (bool, error) {
	seen := map[string]bool{}
	queue := []string{from}
	for len(queue) > 0 {
		v := queue[0]
		queue = queue[1:]
		if v == to {
			return true, nil
		}
		if seen[v] {
			continue
		}
		seen[v] = true
		if len(seen) > 128 {
			return false, errors.New("device stack too large")
		}
		next, err := parents(v)
		if err != nil {
			return false, err
		}
		queue = append(queue, next...)
	}
	return false, nil
}

func relatedDevices(a, b string) (bool, error) {
	if ok, err := reaches(a, b, deviceParents); ok || err != nil {
		return ok, err
	}
	return reaches(b, a, deviceParents)
}
