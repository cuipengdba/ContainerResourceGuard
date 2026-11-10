//go:build linux

package runlog

import (
	"errors"
	"os"
	"path/filepath"
	"strings"
	"syscall"
)

type sink struct{ directory, lock *os.File }

// Open each path component relative to a verified directory FD. Neither a
// symlinked ancestor nor a replaced path can redirect appends or cleanup.
func openSink(path string) (*sink, error) {
	if !filepath.IsAbs(path) || filepath.Clean(path) != path || path == "/" {
		return nil, errors.New("log_dir must be a dedicated clean absolute directory")
	}
	fd, err := syscall.Open("/", syscall.O_RDONLY|syscall.O_DIRECTORY|syscall.O_CLOEXEC, 0)
	if err != nil {
		return nil, err
	}
	for _, part := range strings.Split(strings.TrimPrefix(path, "/"), "/") {
		next, e := syscall.Openat(fd, part, syscall.O_RDONLY|syscall.O_DIRECTORY|syscall.O_NOFOLLOW|syscall.O_CLOEXEC, 0)
		if errors.Is(e, syscall.ENOENT) {
			e = syscall.Mkdirat(fd, part, 0700)
			if e == nil || errors.Is(e, syscall.EEXIST) {
				next, e = syscall.Openat(fd, part, syscall.O_RDONLY|syscall.O_DIRECTORY|syscall.O_NOFOLLOW|syscall.O_CLOEXEC, 0)
			}
		}
		syscall.Close(fd)
		if e != nil {
			return nil, e
		}
		fd = next
	}
	dir := os.NewFile(uintptr(fd), path)
	var stat syscall.Stat_t
	if err := syscall.Fstat(fd, &stat); err != nil {
		dir.Close()
		return nil, err
	}
	if stat.Mode&0022 != 0 {
		dir.Close()
		return nil, errors.New("dedicated log directory must not be group/world writable")
	}
	s := &sink{directory: dir}
	s.lock, err = s.regular(".crg-logs.lock", syscall.O_RDWR|syscall.O_CREAT)
	if err != nil {
		dir.Close()
		return nil, err
	}
	if err = syscall.Flock(int(s.lock.Fd()), syscall.LOCK_EX|syscall.LOCK_NB); err != nil {
		s.close()
		return nil, err
	}
	return s, nil
}

func (s *sink) regular(name string, flags int) (*os.File, error) {
	fd, err := syscall.Openat(int(s.directory.Fd()), name, flags|syscall.O_NOFOLLOW|syscall.O_NONBLOCK|syscall.O_CLOEXEC, 0600)
	if err != nil {
		return nil, err
	}
	f := os.NewFile(uintptr(fd), name)
	var stat syscall.Stat_t
	if err = syscall.Fstat(fd, &stat); err == nil && (stat.Mode&syscall.S_IFMT != syscall.S_IFREG || stat.Nlink != 1) {
		err = errors.New("log destination must be a regular file with one link")
	}
	if err != nil {
		f.Close()
		return nil, err
	}
	return f, nil
}

func (s *sink) files() ([]dailyFile, error) {
	names, err := s.directory.Readdirnames(-1)
	if err != nil {
		return nil, err
	}
	var files []dailyFile
	for _, name := range names {
		day, ok := dailyDate(name)
		if !ok {
			continue
		}
		f, err := s.regular(name, syscall.O_RDONLY)
		if err != nil {
			if errors.Is(err, syscall.ELOOP) || errors.Is(err, syscall.ENOENT) {
				continue
			}
			return nil, err
		}
		stat, err := f.Stat()
		f.Close()
		if err != nil {
			return nil, err
		}
		files = append(files, dailyFile{name: name, day: day, size: stat.Size()})
	}
	return files, nil
}

func (s *sink) remove(name string) error { return syscall.Unlinkat(int(s.directory.Fd()), name) }

func (s *sink) append(name string, b []byte, reset bool) error {
	f, err := s.regular(name, syscall.O_WRONLY|syscall.O_APPEND|syscall.O_CREAT)
	if err != nil {
		return err
	}
	if reset {
		if err := f.Truncate(0); err != nil {
			f.Close()
			return err
		}
	}
	n, err := f.Write(b)
	closeErr := f.Close()
	if err == nil && n != len(b) {
		err = errors.New("short log write")
	}
	return errors.Join(err, closeErr)
}

func (s *sink) close() {
	if s.lock != nil {
		s.lock.Close()
	}
	s.directory.Close()
}
