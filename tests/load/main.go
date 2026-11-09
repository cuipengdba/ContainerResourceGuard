//go:build linux

// Disposable integration-test workload. Never points at existing data files.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"sync"
	"sync/atomic"
	"syscall"
	"time"
)

var memorySink []byte

func main() {
	mode := flag.String("mode", "cpu", "cpu, read, write, or memory")
	seconds := flag.Int("seconds", 4, "bounded test duration")
	workers := flag.Int("workers", 8, "CPU workers")
	directory := flag.String("directory", "", "disposable file directory")
	bytes := flag.Int("bytes", 64<<20, "memory bytes")
	flag.Parse()
	if *seconds < 1 || *seconds > 20 {
		panic("seconds must be 1..20")
	}
	start := time.Now()
	var count atomic.Uint64
	switch *mode {
	case "cpu":
		if *workers < 1 || *workers > 64 {
			panic("workers must be 1..64")
		}
		runtime.GOMAXPROCS(*workers)
		var wg sync.WaitGroup
		deadline := time.Now().Add(time.Duration(*seconds) * time.Second)
		for k := 0; k < *workers; k++ {
			wg.Add(1)
			go func() {
				defer wg.Done()
				var n uint64
				for time.Now().Before(deadline) {
					for j := 0; j < 10000; j++ {
						n = n*1664525 + 1013904223
					}
					count.Add(n & 1)
				}
			}()
		}
		wg.Wait()
	case "memory":
		if *bytes < 1 || *bytes > 512<<20 {
			panic("memory bytes must be 1..512MiB")
		}
		memorySink = make([]byte, *bytes)
		for i := 0; i < len(memorySink); i += 4096 {
			memorySink[i] = 1
		}
		count.Store(uint64(len(memorySink)))
		time.Sleep(time.Duration(*seconds) * time.Second)
	case "read", "write":
		if *directory == "" {
			panic("directory required")
		}
		name := filepath.Join(*directory, fmt.Sprintf(".crg-probe-%d", os.Getpid()))
		fd, e := syscall.Open(name, syscall.O_CREAT|syscall.O_EXCL|syscall.O_RDWR|syscall.O_DIRECT|syscall.O_CLOEXEC, 0600)
		if e != nil {
			panic(e)
		}
		defer os.Remove(name)
		defer syscall.Close(fd)
		buf, e := syscall.Mmap(-1, 0, 1<<20, syscall.PROT_READ|syscall.PROT_WRITE, syscall.MAP_ANON|syscall.MAP_PRIVATE)
		if e != nil {
			panic(e)
		}
		defer syscall.Munmap(buf)
		for i := range buf {
			buf[i] = byte(i)
		}
		const size = 32 << 20
		for off := 0; off < size; off += len(buf) {
			if _, e = syscall.Pwrite(fd, buf, int64(off)); e != nil {
				panic(e)
			}
		}
		if e = syscall.Fsync(fd); e != nil {
			panic(e)
		}
		start = time.Now()
		deadline := start.Add(time.Duration(*seconds) * time.Second)
		off := int64(0)
		for time.Now().Before(deadline) {
			var n int
			if *mode == "read" {
				n, e = syscall.Pread(fd, buf, off)
			} else {
				n, e = syscall.Pwrite(fd, buf, off)
			}
			if e != nil {
				panic(e)
			}
			count.Add(uint64(n))
			off = (off + int64(len(buf))) % size
		}
	default:
		panic("unknown mode")
	}
	_ = json.NewEncoder(os.Stdout).Encode(map[string]any{"mode": *mode, "seconds": time.Since(start).Seconds(), "count": count.Load(), "rate": float64(count.Load()) / time.Since(start).Seconds()})
}
