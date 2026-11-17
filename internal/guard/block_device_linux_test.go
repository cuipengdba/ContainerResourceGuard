//go:build linux

package guard

import (
	"os"
	"path/filepath"
	"testing"
)

func blockTree(t *testing.T) (sysfs, disk, part string) {
	t.Helper()
	sysfs = t.TempDir()
	disk = filepath.Join(sysfs, "devices", "disk")
	part = filepath.Join(disk, "intermediate", "slice")
	for _, dir := range []string{filepath.Join(sysfs, "class/block"), filepath.Join(sysfs, "dev/block"), part} {
		if err := os.MkdirAll(dir, 0700); err != nil {
			t.Fatal(err)
		}
	}
	for _, v := range []struct{ path, value string }{
		{filepath.Join(disk, "dev"), "8:0"}, {filepath.Join(disk, "size"), "10000"},
		{filepath.Join(disk, "dm/uuid"), "CRG-SNAPSHOT-DISK"},
		{filepath.Join(part, "dev"), "8:1"}, {filepath.Join(part, "size"), "2000"},
		{filepath.Join(part, "start"), "100"}, {filepath.Join(part, "partition"), "1"},
	} {
		if err := os.MkdirAll(filepath.Dir(v.path), 0700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(v.path, []byte(v.value), 0600); err != nil {
			t.Fatal(err)
		}
	}
	for path, target := range map[string]string{
		filepath.Join(sysfs, "dev/block/8:0"): disk, filepath.Join(sysfs, "dev/block/8:1"): part,
		filepath.Join(disk, "subsystem"): filepath.Join(sysfs, "class/block"),
		filepath.Join(part, "subsystem"): filepath.Join(sysfs, "class/block"),
	} {
		if err := os.Symlink(target, path); err != nil {
			t.Fatal(err)
		}
	}
	return
}

func TestPartitionSeparatesFilesystemIdentityAndWholeControl(t *testing.T) {
	sysfs, disk, part := blockTree(t)
	whole, err := resolveIOBlockDevice(sysfs, "8:0")
	const legacy = "13491da17b7f76ae14362ef2695a524778a62126b7bbab38773213d6593ddb5f"
	if err != nil || whole.Identity != legacy || whole.ControlIdentity != legacy || whole.ControlDevice != "8:0" {
		t.Fatal("legacy whole-device/journal identity changed", whole, err)
	}
	slice, err := resolveIOBlockDevice(sysfs, "8:1")
	if err != nil || slice.ControlDevice != whole.Device || slice.ControlIdentity != legacy || slice.Identity == legacy || slice.Partition != 1 || slice.StartSectors != 100 || slice.SizeSectors != 2000 {
		t.Fatal(slice, err)
	}
	// Kernel names and MAJ:MIN can change while stable identity/geometry stays.
	for name, path := range map[string]string{"8:0": disk, "8:1": part} {
		if err := os.Remove(filepath.Join(sysfs, "dev/block", name)); err != nil {
			t.Fatal(err)
		}
		newName := map[string]string{"8:0": "252:7", "8:1": "252:8"}[name]
		if err := os.WriteFile(filepath.Join(path, "dev"), []byte(newName), 0600); err != nil {
			t.Fatal(err)
		}
		if err := os.Symlink(path, filepath.Join(sysfs, "dev/block", newName)); err != nil {
			t.Fatal(err)
		}
	}
	current, err := resolveIOBlockDevice(sysfs, "252:8")
	if err != nil || current.Identity != slice.Identity || current.ControlIdentity != slice.ControlIdentity || current.ControlDevice != "252:7" {
		t.Fatal("stable renumbering failed", current, err)
	}
}

func TestPartitionGeometryAndReplacementInvalidateCache(t *testing.T) {
	for _, field := range []string{"start", "size", "partition", "parent-uuid", "parent-size"} {
		t.Run(field, func(t *testing.T) {
			sysfs, disk, part := blockTree(t)
			before, err := resolveIOBlockDevice(sysfs, "8:1")
			if err != nil {
				t.Fatal(err)
			}
			path, value := filepath.Join(part, field), "2"
			switch field {
			case "parent-uuid":
				path, value = filepath.Join(disk, "dm/uuid"), "REPLACEMENT-DISK"
			case "parent-size":
				path, value = filepath.Join(disk, "size"), "20000"
			}
			if err := os.WriteFile(path, []byte(value), 0600); err != nil {
				t.Fatal(err)
			}
			after, err := resolveIOBlockDevice(sysfs, "8:1")
			if err != nil || after.Identity == before.Identity {
				t.Fatal("changed partition reused old baseline", after, err)
			}
		})
	}
}

func TestPartitionRejectsUnverifiedTreeAndGeometry(t *testing.T) {
	for _, bad := range []string{"missing-parent-id", "bad-parent-index", "bad-child-dev", "overflow", "zero-partition", "missing-start", "zero-size", "escape-index", "wrong-subsystem"} {
		t.Run(bad, func(t *testing.T) {
			sysfs, disk, part := blockTree(t)
			switch bad {
			case "missing-parent-id":
				os.Remove(filepath.Join(disk, "dm/uuid"))
			case "bad-parent-index":
				os.Remove(filepath.Join(sysfs, "dev/block/8:0"))
				os.Symlink(part, filepath.Join(sysfs, "dev/block/8:0"))
			case "bad-child-dev":
				os.WriteFile(filepath.Join(part, "dev"), []byte("8:2"), 0600)
			case "overflow":
				os.WriteFile(filepath.Join(part, "start"), []byte("18446744073709551615"), 0600)
			case "zero-partition":
				os.WriteFile(filepath.Join(part, "partition"), []byte("0"), 0600)
			case "missing-start":
				os.Remove(filepath.Join(part, "start"))
			case "zero-size":
				os.WriteFile(filepath.Join(part, "size"), []byte("0"), 0600)
			case "escape-index":
				os.Remove(filepath.Join(sysfs, "dev/block/8:1"))
				os.Symlink(t.TempDir(), filepath.Join(sysfs, "dev/block/8:1"))
			case "wrong-subsystem":
				os.Remove(filepath.Join(part, "subsystem"))
				os.Mkdir(filepath.Join(sysfs, "class/other"), 0700)
				os.Symlink(filepath.Join(sysfs, "class/other"), filepath.Join(part, "subsystem"))
			}
			if got, err := resolveIOBlockDevice(sysfs, "8:1"); err == nil {
				t.Fatal("unverified mapping accepted", got)
			}
		})
	}
}
