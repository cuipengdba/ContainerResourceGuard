//go:build linux

package guard

import (
	"errors"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"syscall"
)

// SelectCalibrationDirectory reads only this process's mount namespace. It does
// not walk directory trees, enumerate containers, or mount any device.
func SelectCalibrationDirectory() (CalibrationSelection, error) {
	data, err := os.ReadFile("/proc/self/mountinfo")
	if err != nil {
		return CalibrationSelection{}, err
	}
	return selectCalibrationDirectory(string(data), inspectCalibrationMount)
}

func selectCalibrationDirectory(mountinfo string, inspect func(string, string, string) (CalibrationSelection, error)) (CalibrationSelection, error) {
	var candidates []CalibrationSelection
	seen := map[string]bool{}
	for _, line := range strings.Split(mountinfo, "\n") {
		sides := strings.SplitN(line, " - ", 2)
		if len(sides) != 2 {
			continue
		}
		f, g := strings.Fields(sides[0]), strings.Fields(sides[1])
		if len(f) < 6 || len(g) < 3 || !validDevice(f[2]) || !hasMountOption(f[5], "rw") || hasMountOption(g[2], "ro") {
			continue
		}
		// Only known local block-backed filesystems. Network/pseudo/overlay
		// filesystems cannot supply a trustworthy io.max block-device baseline.
		switch g[0] {
		case "ext2", "ext3", "ext4", "xfs", "btrfs", "f2fs":
		default:
			continue
		}
		mp := unescape(f[4])
		if !filepath.IsAbs(mp) || filepath.Clean(mp) != mp || seen[mp] {
			continue
		}
		v, err := inspect(mp, f[2], g[0])
		if err == nil && v.TotalBytes > 0 && v.AvailableBytes >= 384<<20 {
			seen[mp] = true
			candidates = append(candidates, v)
		}
	}
	if len(candidates) == 0 {
		return CalibrationSelection{}, errors.New("no writable local block-backed directory with stable identity and at least 384MiB available")
	}
	sort.Slice(candidates, func(i, j int) bool {
		if candidates[i].TotalBytes != candidates[j].TotalBytes {
			return candidates[i].TotalBytes > candidates[j].TotalBytes
		}
		return candidates[i].Directory < candidates[j].Directory
	})
	return candidates[0], nil
}

func hasMountOption(options, want string) bool {
	for _, s := range strings.Split(options, ",") {
		if s == want {
			return true
		}
	}
	return false
}

func inspectCalibrationMount(directory, device, fsType string) (CalibrationSelection, error) {
	v := CalibrationSelection{Directory: directory, Device: device, Filesystem: fsType}
	real, err := filepath.EvalSymlinks(directory)
	if err != nil || real != directory {
		return v, errors.New("mount directory changed or resolves through a symlink")
	}
	st, err := os.Stat(directory)
	if err != nil || !st.IsDir() {
		return v, errors.New("mount is not a directory")
	}
	current, err := fileDevice(directory)
	if err != nil || current != device {
		return v, errors.New("mount is hidden or device changed")
	}
	var fs syscall.Statfs_t
	if err = syscall.Statfs(directory, &fs); err != nil {
		return v, err
	}
	if fs.Flags&1 != 0 || fs.Bsize <= 0 || fs.Blocks > math.MaxUint64/uint64(fs.Bsize) || fs.Bavail > math.MaxUint64/uint64(fs.Bsize) {
		return v, errors.New("read-only filesystem or invalid capacity")
	}
	if err = syscall.Access(directory, 3); err != nil { // W_OK | X_OK
		return v, err
	}
	v.TotalBytes, v.AvailableBytes = fs.Blocks*uint64(fs.Bsize), fs.Bavail*uint64(fs.Bsize)
	binding, err := ResolveIOBlockDevice(device)
	if err != nil {
		return v, fmt.Errorf("device has no stable identity: %w", err)
	}
	v.Identity, v.ControlDevice = binding.Identity, binding.ControlDevice
	return v, nil
}
