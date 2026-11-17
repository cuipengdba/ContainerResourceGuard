//go:build linux

// A bounded direct-IO acceptance load, never part of the CRG product.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"syscall"
	"time"
)

type file struct {
	fd   int
	path string
	stat syscall.Stat_t
	buf  []byte
}

func prepare(dir string) (*file, error) {
	abs, err := filepath.Abs(dir)
	if err != nil {
		return nil, err
	}
	real, err := filepath.EvalSymlinks(abs)
	if err != nil || real != abs {
		return nil, fmt.Errorf("unverified disposable directory")
	}
	f, err := os.CreateTemp(abs, "crg-partition-load-*.bin")
	if err != nil {
		return nil, err
	}
	x := &file{fd: -1, path: f.Name()}
	if err = syscall.Fstat(int(f.Fd()), &x.stat); err != nil {
		f.Close()
		return nil, err
	}
	if err = f.Close(); err != nil {
		return nil, err
	}
	x.fd, err = syscall.Open(x.path, syscall.O_RDWR|syscall.O_DIRECT|syscall.O_NOFOLLOW|syscall.O_CLOEXEC, 0)
	if err != nil {
		return nil, err
	}
	var current syscall.Stat_t
	if err = syscall.Fstat(x.fd, &current); err != nil || current.Dev != x.stat.Dev || current.Ino != x.stat.Ino || current.Mode&syscall.S_IFMT != syscall.S_IFREG || current.Nlink != 1 {
		return nil, fmt.Errorf("disposable regular file identity changed")
	}
	x.buf, err = syscall.Mmap(-1, 0, 1<<20, syscall.PROT_READ|syscall.PROT_WRITE, syscall.MAP_ANON|syscall.MAP_PRIVATE)
	if err != nil {
		return nil, err
	}
	for i := range x.buf {
		x.buf[i] = byte(i)
	}
	for offset := int64(0); offset < 32<<20; offset += int64(len(x.buf)) {
		if n, err := syscall.Pwrite(x.fd, x.buf, offset); err != nil || n != len(x.buf) {
			return nil, fmt.Errorf("direct population failed: %v", err)
		}
	}
	if err = syscall.Fsync(x.fd); err != nil {
		return nil, err
	}
	return x, nil
}

func (f *file) close() {
	syscall.Munmap(f.buf)
	syscall.Close(f.fd)
	var current syscall.Stat_t
	if err := syscall.Lstat(f.path, &current); err == nil && current.Dev == f.stat.Dev && current.Ino == f.stat.Ino && current.Mode&syscall.S_IFMT == syscall.S_IFREG && current.Nlink == 1 {
		os.Remove(f.path)
	}
}

func main() {
	first := flag.String("first", "", "first disposable partition directory")
	second := flag.String("second", "", "second disposable partition directory")
	seconds := flag.Int("seconds", 6, "bounded simultaneous measurement seconds")
	mode := flag.String("mode", "write", "write or randwrite")
	flag.Parse()
	if *seconds < 1 || *seconds > 20 || *first == "" || *second == "" || (*mode != "write" && *mode != "randwrite") {
		panic("invalid bounded acceptance load options")
	}
	population := time.Now()
	a, err := prepare(*first)
	if err != nil {
		panic(err)
	}
	defer a.close()
	b, err := prepare(*second)
	if err != nil {
		panic(err)
	}
	defer b.close()
	if a.stat.Dev == b.stat.Dev {
		panic("two distinct filesystem devices required")
	}
	populationSeconds := time.Since(population).Seconds()
	counts := [2]uint64{}
	errors := [2]error{}
	begin := make(chan struct{})
	var ready, done sync.WaitGroup
	ready.Add(2)
	done.Add(2)
	var start time.Time
	for index, f := range []*file{a, b} {
		go func(index int, f *file) {
			defer done.Done()
			ready.Done()
			<-begin
			deadline := start.Add(time.Duration(*seconds) * time.Second)
			block := f.buf
			if *mode == "randwrite" {
				block = block[:4096]
			}
			for offset := int64(0); time.Now().Before(deadline); offset = (offset + 104729*4096) % (32 << 20) {
				if *mode == "write" {
					offset = int64(counts[index]) % (32 << 20)
				}
				n, err := syscall.Pwrite(f.fd, block, offset)
				if err != nil || n != len(block) {
					errors[index] = fmt.Errorf("direct measurement failed: %v", err)
					return
				}
				counts[index] += uint64(n)
			}
		}(index, f)
	}
	ready.Wait()
	start = time.Now()
	close(begin)
	done.Wait()
	elapsed := time.Since(start).Seconds()
	if errors[0] != nil || errors[1] != nil || counts[0] == 0 || counts[1] == 0 {
		panic(fmt.Sprintf("one partition failed or made no progress: %v", errors))
	}
	total := counts[0] + counts[1]
	json.NewEncoder(os.Stdout).Encode(map[string]any{"mode": *mode, "seconds": elapsed, "population_seconds_excluded": populationSeconds,
		"counts": counts, "count": total, "rate": float64(total) / elapsed, "iops": float64(total/4096) / elapsed,
		"filesystem_devices": []string{fmt.Sprintf("%d:%d", (a.stat.Dev>>8)&0xfff|(a.stat.Dev>>32)&0xfffff000, a.stat.Dev&0xff|(a.stat.Dev>>12)&0xffffff00), fmt.Sprintf("%d:%d", (b.stat.Dev>>8)&0xfff|(b.stat.Dev>>32)&0xfffff000, b.stat.Dev&0xff|(b.stat.Dev>>12)&0xffffff00)}})
}
