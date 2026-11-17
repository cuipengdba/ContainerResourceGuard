//go:build linux

package guard

import (
	"errors"
	"os"
	"syscall"
)

func verifySupervisorMetadata(path string) error {
	var st syscall.Stat_t
	if err := syscall.Lstat(path, &st); err != nil {
		return err
	}
	if st.Nlink != 1 || st.Uid != uint32(os.Geteuid()) || st.Gid != uint32(os.Getegid()) {
		return errors.New("automatic supervisor replacement requires a single-link file owned by the maintenance UID/GID")
	}
	n, err := syscall.Listxattr(path, nil)
	if err != nil && err != syscall.ENOTSUP {
		return err
	}
	if n > 0 {
		return errors.New("supervisor has extended attributes; preserve them with a separately reviewed deployment change")
	}
	return nil
}
