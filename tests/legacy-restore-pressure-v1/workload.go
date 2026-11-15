//go:build linux

// Disposable CI workload; never linked into CRG or a vendor image.
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"runtime"
	"runtime/debug"
	"strconv"
	"strings"
	"sync/atomic"
	"time"
)

func main() {
	var syncs atomic.Uint64
	var failed atomic.Bool
	done := make(chan struct{})
	defer close(done)
	go func() {
		file, err := os.OpenFile("/data/fsync.bin", os.O_CREATE|os.O_RDWR, 0600)
		if err != nil {
			failed.Store(true)
			return
		}
		defer file.Close()
		block := make([]byte, 65536)
		for i := range block {
			block[i] = byte(i)
		}
		ticker := time.NewTicker(200 * time.Millisecond)
		defer ticker.Stop()
		for offset := int64(0); offset < 2000; offset++ {
			select {
			case <-done:
				return
			case <-ticker.C:
			}
			if _, err := file.WriteAt(block, offset%32*65536); err != nil {
				failed.Store(true)
				return
			}
			if file.Sync() != nil {
				failed.Store(true)
				return
			}
			syncs.Add(1)
		}
	}()
	go func() {
		time.Sleep(180 * time.Second)
		os.Exit(3)
	}()
	var held []byte
	scanner := bufio.NewScanner(os.Stdin)
	for scanner.Scan() {
		fields := strings.Fields(scanner.Text())
		if len(fields) == 0 {
			os.Exit(2)
		}
		started := time.Now()
		switch fields[0] {
		case "alloc":
			if len(fields) != 2 {
				os.Exit(2)
			}
			n, err := strconv.Atoi(fields[1])
			if err != nil || n < 0 || n > 256<<20 {
				os.Exit(2)
			}
			held = make([]byte, n)
			for i := 0; i < len(held); i += 4096 {
				held[i] = 1
			}
		case "free":
			held = nil
			runtime.GC()
			debug.FreeOSMemory()
		case "status", "quit":
		default:
			os.Exit(2)
		}
		runtime.KeepAlive(held)
		data, err := json.Marshal(map[string]any{"command": fields[0], "pid": os.Getpid(), "allocated_bytes": len(held), "fsync_count": syncs.Load(), "fsync_failed": failed.Load(), "elapsed_ns": time.Since(started).Nanoseconds(), "epoch_ns": time.Now().UnixNano()})
		if err != nil {
			os.Exit(2)
		}
		fmt.Println(string(data))
		if fields[0] == "quit" {
			return
		}
	}
	if scanner.Err() != nil {
		os.Exit(2)
	}
}
