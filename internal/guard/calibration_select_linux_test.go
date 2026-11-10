//go:build linux

package guard

import (
	"errors"
	"fmt"
	"strings"
	"testing"
)

func TestLargestCalibrationFilesystemSelection(t *testing.T) {
	mount := func(id int, dev, mp, options, fs string) string {
		return fmt.Sprintf("%d 1 %s / %s %s shared:9 - %s /dev/example rw\n", id, dev, mp, options, fs)
	}
	input := mount(1, "0:1", "/", "rw", "overlay") + mount(2, "0:2", "/dev/shm", "rw", "tmpfs") +
		mount(3, "8:1", "/readonly", "ro", "xfs") + mount(4, "8:2", "/network", "rw", "nfs") +
		mount(5, "8:3", "/small", "rw", "ext4") + mount(6, "8:4", `/big\040data`, "rw", "xfs") +
		mount(7, "8:4", "/alias", "rw", "xfs") + mount(8, "8:5", "/full", "rw", "xfs") +
		mount(9, "8:6", "/denied", "rw", "xfs") + mount(10, "8:7", "/etc/hosts", "rw", "ext4")
	inspections := map[string]int{}
	inspect := func(path, dev, fs string) (CalibrationSelection, error) {
		inspections[path]++
		if path == "/denied" || path == "/etc/hosts" {
			return CalibrationSelection{}, errors.New("not writable directory")
		}
		total, free := uint64(10<<30), uint64(1<<30)
		if path == "/alias" || path == "/big data" {
			total, free = 100<<30, 512<<20
		}
		if path == "/full" {
			total, free = 200<<30, 383<<20
		}
		return CalibrationSelection{Directory: path, Device: dev, Filesystem: fs, Identity: strings.Repeat("a", 64), TotalBytes: total, AvailableBytes: free}, nil
	}
	v, err := selectCalibrationDirectory(input, inspect)
	if err != nil || v.Directory != "/alias" || v.Device != "8:4" {
		t.Fatalf("%+v %v", v, err)
	}
	for _, path := range []string{"/", "/dev/shm", "/readonly", "/network"} {
		if inspections[path] != 0 {
			t.Fatalf("ineligible mount inspected: %s", path)
		}
	}
	if _, err := selectCalibrationDirectory(mount(1, "0:1", "/", "rw", "overlay"), inspect); err == nil {
		t.Fatal("accepted overlay-only namespace")
	}
}

func TestCalibrationSelectionDoesNotHideVisibleStackedMount(t *testing.T) {
	input := "1 0 8:1 / /data rw - xfs /dev/a rw\n2 1 8:2 / /data rw - xfs /dev/b rw\n"
	v, err := selectCalibrationDirectory(input, func(path, dev, fs string) (CalibrationSelection, error) {
		if dev == "8:1" {
			return CalibrationSelection{}, errors.New("hidden mount")
		}
		return CalibrationSelection{Directory: path, Device: dev, Filesystem: fs, TotalBytes: 1 << 40, AvailableBytes: 1 << 39}, nil
	})
	if err != nil || v.Device != "8:2" {
		t.Fatalf("%+v %v", v, err)
	}
}
