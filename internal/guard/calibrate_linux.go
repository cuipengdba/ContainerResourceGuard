//go:build linux

package guard

import (
	"context"
	"crypto/rand"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"syscall"
	"time"
)

// Calibrate only creates a new regular file in an explicitly named directory.
// No raw-device writes, cache dropping, global tuning, or startup calibration.
func Calibrate(ctx context.Context, directory string, seconds int) (Profile, error) {
	p := Profile{Version: 1, Method: "direct-sync-qdepth1-seq1m-random4k", CreatedUTC: time.Now().UTC().Format(time.RFC3339)}
	if seconds < 1 || seconds > 30 {
		return p, errors.New("seconds must be 1..30 per phase")
	}
	directory, e := filepath.Abs(directory)
	if e != nil {
		return p, e
	}
	st, e := os.Stat(directory)
	if e != nil || !st.IsDir() {
		return p, errors.New("calibration directory must already exist")
	}
	var fs syscall.Statfs_t
	if e = syscall.Statfs(directory, &fs); e != nil {
		return p, e
	}
	if fs.Type == 0x794c7630 || fs.Type == 0x01021994 {
		return p, errors.New("calibrate on a block-backed data mount, not overlay/tmpfs")
	}
	const size = 128 << 20
	if uint64(fs.Bavail)*uint64(fs.Bsize) < size+(256<<20) {
		return p, errors.New("less than 384 MiB free")
	}
	dev, e := fileDevice(directory)
	if e != nil {
		return p, e
	}
	id, e := DeviceIdentity(dev)
	if e != nil {
		return p, e
	}
	tmp, e := os.CreateTemp(directory, ".crg-calibration-*")
	if e != nil {
		return p, e
	}
	name := tmp.Name()
	tmp.Close()
	defer os.Remove(name)
	// Open the file we just created without following a substituted symlink.
	fd, e := syscall.Open(name, syscall.O_RDWR|syscall.O_DIRECT|syscall.O_NOFOLLOW|syscall.O_CLOEXEC, 0600)
	if e != nil {
		return p, fmt.Errorf("O_DIRECT unavailable: %w", e)
	}
	defer syscall.Close(fd)
	if e = syscall.Ftruncate(fd, size); e != nil {
		return p, e
	}
	buf, e := syscall.Mmap(-1, 0, 1<<20, syscall.PROT_READ|syscall.PROT_WRITE, syscall.MAP_PRIVATE|syscall.MAP_ANON)
	if e != nil {
		return p, e
	}
	defer syscall.Munmap(buf)
	if _, e = rand.Read(buf); e != nil {
		return p, e
	}
	// Populate once so random/read phases do not measure sparse holes.
	for off := int64(0); off < size; off += int64(len(buf)) {
		if e = ctx.Err(); e != nil {
			return p, e
		}
		n, x := syscall.Pwrite(fd, buf, off)
		if x != nil {
			return p, x
		}
		if n != len(buf) {
			return p, errors.New("short population write")
		}
	}
	if e = syscall.Fsync(fd); e != nil {
		return p, e
	}
	measure := func(write, random bool) (uint64, error) {
		start := time.Now()
		var count, offset uint64
		state := uint64(0x9e3779b97f4a7c15)
		block := buf
		if random {
			block = buf[:4096]
		}
		for time.Since(start) < time.Duration(seconds)*time.Second {
			if e := ctx.Err(); e != nil {
				return 0, e
			}
			if random {
				state ^= state << 13
				state ^= state >> 7
				state ^= state << 17
				offset = (state % (size / 4096)) * 4096
			} else {
				offset = (count * uint64(len(block))) % size
			}
			var n int
			var e error
			if write {
				n, e = syscall.Pwrite(fd, block, int64(offset))
			} else {
				n, e = syscall.Pread(fd, block, int64(offset))
			}
			if e != nil {
				return 0, e
			}
			if n != len(block) {
				return 0, errors.New("short direct IO")
			}
			count++
		}
		rate := float64(count) / time.Since(start).Seconds()
		if !random {
			rate *= float64(len(block))
		}
		if rate < 1 {
			return 0, errors.New("invalid calibration rate")
		}
		return uint64(rate), nil
	}
	d := DeviceProfile{Device: dev, Identity: id}
	if d.WriteBPS, e = measure(true, false); e != nil {
		return p, e
	}
	if e = syscall.Fsync(fd); e != nil {
		return p, e
	}
	if d.ReadBPS, e = measure(false, false); e != nil {
		return p, e
	}
	if d.WriteIOPS, e = measure(true, true); e != nil {
		return p, e
	}
	if e = syscall.Fsync(fd); e != nil {
		return p, e
	}
	if d.ReadIOPS, e = measure(false, true); e != nil {
		return p, e
	}
	latestDevice, err := fileDevice(directory)
	if err != nil {
		return p, err
	}
	latestID, err := DeviceIdentity(dev)
	if err != nil || latestDevice != dev || latestID != id {
		return p, errors.New("calibration device changed; no profile accepted")
	}
	p.Devices = []DeviceProfile{d}
	return p, nil
}
