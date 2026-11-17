package guard

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

// IOBlockDevice separates filesystem identity from the whole-disk io.max key.
// Resolving a device is read-only; it never opens /dev or changes a controller.
type IOBlockDevice struct {
	Device          string `json:"filesystem_device"`
	Identity        string `json:"filesystem_identity"`
	ControlDevice   string `json:"control_device"`
	ControlIdentity string `json:"control_identity"`
	Partition       uint64 `json:"partition_number,omitempty"`
	StartSectors    uint64 `json:"start_sectors,omitempty"`
	SizeSectors     uint64 `json:"size_sectors"`
	devicePath      string
	controlPath     string
}

func ResolveIOBlockDevice(device string) (IOBlockDevice, error) {
	return resolveIOBlockDevice("/sys", device)
}

func DeviceIdentity(device string) (string, error) {
	d, err := ResolveIOBlockDevice(device)
	return d.Identity, err
}

func below(root, candidate string) bool {
	rel, err := filepath.Rel(root, candidate)
	return err == nil && rel != "." && rel != ".." && !filepath.IsAbs(rel) && !strings.HasPrefix(rel, ".."+string(filepath.Separator))
}

func blockNode(sysfs, device string) (string, error) {
	if !validDevice(device) {
		return "", errors.New("invalid block device number")
	}
	for _, value := range strings.Split(device, ":") {
		n, err := strconv.ParseUint(value, 10, 32)
		if err != nil || strconv.FormatUint(n, 10) != value {
			return "", errors.New("noncanonical block device number")
		}
	}
	root, err := filepath.EvalSymlinks(filepath.Join(sysfs, "dev/block", device))
	if err != nil {
		return "", err
	}
	if !below(filepath.Join(sysfs, "devices"), root) {
		return "", errors.New("block index leaves the sysfs device tree")
	}
	n, err := read(filepath.Join(root, "dev"))
	if err != nil || n != device {
		return "", errors.New("block index and device number differ")
	}
	subsystem, err := filepath.EvalSymlinks(filepath.Join(root, "subsystem"))
	if err != nil || !below(sysfs, subsystem) || filepath.Base(subsystem) != "block" {
		return "", errors.New("unverified block subsystem")
	}
	return root, nil
}

func sectorValue(root, name string, positive bool) (uint64, error) {
	v, err := read(filepath.Join(root, name))
	if err != nil {
		return 0, err
	}
	n, err := strconv.ParseUint(v, 10, 64)
	if err != nil || strconv.FormatUint(n, 10) != v || positive && n == 0 {
		return 0, fmt.Errorf("invalid block %s", name)
	}
	return n, nil
}

// Preserve existing whole-device hashes so old journals can still restore the
// same actual control target. Partition hashes use a distinct versioned domain.
func wholeDeviceIdentity(root string) (string, error) {
	var identity string
	for _, name := range []string{"dm/uuid", "device/wwid", "wwid"} {
		value, err := read(filepath.Join(root, name))
		if err != nil && !os.IsNotExist(err) {
			return "", err
		}
		if err == nil && value != "" {
			identity = name + ":" + value
			break
		}
	}
	if identity == "" {
		return "", errors.New("device has no stable UUID/WWID; refusing a portable IO profile")
	}
	if _, err := sectorValue(root, "size", true); err != nil {
		return "", err
	}
	size, _ := read(filepath.Join(root, "size"))
	start, err := read(filepath.Join(root, "start"))
	if err != nil && !os.IsNotExist(err) {
		return "", err
	}
	hash := sha256.Sum256([]byte(identity + ":" + size + ":" + start))
	return hex.EncodeToString(hash[:]), nil
}

func blockSnapshot(sysfs, device string) (IOBlockDevice, error) {
	d := IOBlockDevice{Device: device, ControlDevice: device}
	root, err := blockNode(sysfs, device)
	if err != nil {
		return d, err
	}
	d.devicePath, d.controlPath = root, root
	d.SizeSectors, err = sectorValue(root, "size", true)
	if err != nil {
		return d, err
	}
	_, err = os.Stat(filepath.Join(root, "partition"))
	if err != nil && !os.IsNotExist(err) {
		return d, err
	}
	if err == nil {
		d.Partition, err = sectorValue(root, "partition", true)
		if err != nil {
			return d, err
		}
		d.StartSectors, err = sectorValue(root, "start", false)
		if err != nil {
			return d, err
		}
		// Walk real ancestors and verify the subsystem, not the kernel name or
		// a fixed number of ../ components. An unreadable block parent is fatal.
		found := false
		for parent, steps := filepath.Dir(root), 0; below(filepath.Join(sysfs, "devices"), parent) && steps < 64; parent, steps = filepath.Dir(parent), steps+1 {
			subsystem, e := filepath.EvalSymlinks(filepath.Join(parent, "subsystem"))
			if e != nil {
				if os.IsNotExist(e) {
					continue
				}
				return d, e
			}
			if filepath.Base(subsystem) != "block" {
				continue
			}
			n, e := read(filepath.Join(parent, "dev"))
			if e != nil {
				return d, e
			}
			verified, e := blockNode(sysfs, n)
			if e != nil || verified != parent {
				return d, errors.New("partition parent and block index differ")
			}
			if _, e = os.Stat(filepath.Join(parent, "partition")); !os.IsNotExist(e) {
				return d, errors.New("nested or unreadable partition parent")
			}
			size, e := sectorValue(parent, "size", true)
			if e != nil || d.StartSectors > size || d.SizeSectors > size-d.StartSectors {
				return d, errors.New("partition geometry exceeds verified parent")
			}
			d.ControlDevice, d.controlPath, found = n, parent, true
			break
		}
		if !found {
			return d, errors.New("partition has no verified whole-disk parent")
		}
	}
	d.ControlIdentity, err = wholeDeviceIdentity(d.controlPath)
	if err != nil {
		return d, err
	}
	d.Identity = d.ControlIdentity
	if d.Partition != 0 {
		value := fmt.Sprintf("crg-partition-v1:%s:%d:%d:%d", d.ControlIdentity, d.Partition, d.StartSectors, d.SizeSectors)
		hash := sha256.Sum256([]byte(value))
		d.Identity = hex.EncodeToString(hash[:])
	}
	return d, nil
}

func resolveIOBlockDevice(sysfs, device string) (IOBlockDevice, error) {
	sysfs, err := filepath.EvalSymlinks(sysfs)
	if err != nil {
		return IOBlockDevice{}, err
	}
	first, err := blockSnapshot(sysfs, device)
	if err != nil {
		return IOBlockDevice{}, err
	}
	second, err := blockSnapshot(sysfs, device)
	if err != nil || first != second {
		return IOBlockDevice{}, errors.New("block device topology changed while resolving")
	}
	return first, nil
}
