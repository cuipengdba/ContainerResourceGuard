//go:build linux

// A bounded placeholder PID 1 for disposable, native cgroup CI containers.
package main

import (
	"os"
	"os/signal"
	"syscall"
	"time"
)

func main() {
	signals := make(chan os.Signal, 1)
	signal.Notify(signals, syscall.SIGTERM, syscall.SIGINT)
	defer signal.Stop(signals)
	select {
	case <-signals:
	case <-time.After(10 * time.Minute):
	}
}
