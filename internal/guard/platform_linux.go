//go:build linux

package guard

import (
	"crypto/sha256"
	"fmt"
	"os"
	"syscall"
)

func verifyCgroup(p string) error {
	var s syscall.Statfs_t
	if e := syscall.Statfs(p, &s); e != nil {
		return e
	}
	if s.Type != 0x63677270 {
		return fmt.Errorf("target is not cgroup2")
	}
	return nil
}

func openStateJSONFile(path string) (*os.File, error) {
	fd, err := syscall.Open(path, syscall.O_RDONLY|syscall.O_NONBLOCK|syscall.O_NOFOLLOW|syscall.O_CLOEXEC, 0)
	if err != nil {
		return nil, err
	}
	return os.NewFile(uintptr(fd), path), nil
}

func verifyCapacitySource(path, kind string) error {
	var s syscall.Statfs_t
	if err := syscall.Statfs(path, &s); err != nil {
		return err
	}
	want := int64(0x9fa0) // PROC_SUPER_MAGIC
	if kind == "cpu" {
		want = 0x62656572
	} // SYSFS_MAGIC
	if int64(s.Type) != want {
		return fmt.Errorf("source is not native %s filesystem; provide read-only host proc/sys mounts", kind)
	}
	return nil
}
func groupIdentity(p string) (string, error) {
	var s syscall.Stat_t
	if e := syscall.Stat(p, &s); e != nil {
		return "", e
	}
	boot, e := read("/proc/sys/kernel/random/boot_id")
	if e != nil {
		return "", e
	}
	h := sha256.Sum256([]byte(fmt.Sprintf("%s:%s:%d:%d", boot, p, s.Dev, s.Ino)))
	return fmt.Sprintf("%x", h), nil
}
func lockFile(path string) (*os.File, error) {
	fd, e := syscall.Open(path, syscall.O_CREAT|syscall.O_RDWR|syscall.O_NOFOLLOW|syscall.O_CLOEXEC, 0600)
	if e != nil {
		return nil, e
	}
	f := os.NewFile(uintptr(fd), path)
	if e = syscall.Flock(fd, syscall.LOCK_EX|syscall.LOCK_NB); e != nil {
		f.Close()
		return nil, e
	}
	return f, nil
}

// Lock the actual cgroup inode, independent of state_dir, TMPDIR and mount path.
// This is advisory coordination between CRG instances, not a security boundary.
func lockGroup(path string) (*os.File, error) {
	fd, e := syscall.Open(path, syscall.O_RDONLY|syscall.O_DIRECTORY|syscall.O_NOFOLLOW|syscall.O_CLOEXEC, 0)
	if e != nil {
		return nil, e
	}
	f := os.NewFile(uintptr(fd), path)
	if e = syscall.Flock(fd, syscall.LOCK_EX|syscall.LOCK_NB); e != nil {
		f.Close()
		return nil, e
	}
	return f, nil
}
func fileDevice(path string) (string, error) {
	var s syscall.Stat_t
	if e := syscall.Stat(path, &s); e != nil {
		return "", e
	}
	d := uint64(s.Dev)
	major := (d>>8)&0xfff | (d>>32)&0xfffff000
	minor := d&0xff | (d>>12)&0xffffff00
	return fmt.Sprintf("%d:%d", major, minor), nil
}

func openConfigFile(path string) (*os.File, error) {
	fd, err := syscall.Open(path, syscall.O_RDONLY|syscall.O_NONBLOCK|syscall.O_CLOEXEC, 0)
	if err != nil {
		return nil, err
	}
	return os.NewFile(uintptr(fd), path), nil
}
