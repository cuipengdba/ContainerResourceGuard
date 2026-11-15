//go:build linux

// Test-only helper for explicitly labelled, disposable native CI containers.
package main

import (
	"fmt"
	"os"
	"syscall"
	"unsafe"
)

func main() {
	if os.Getenv("CRG_PERSIST_FIXTURE") != "ephemeral-github-hosted-vm-only" || len(os.Args) < 2 {
		panic("explicit disposable fixture required")
	}
	if os.Args[1] == "remount-ro" || os.Args[1] == "remount-rw" {
		if os.Args[1] == "remount-ro" {
			// Existing lock descriptors pin the old writable mount. A new
			// private bind of the same state tree has no open writer count;
			// only future path-based access through this overlay becomes RO.
			if err := syscall.Mount("/state", "/state", "", syscall.MS_BIND, ""); err != nil {
				panic(err)
			}
		}
		flags := uintptr(syscall.MS_BIND | syscall.MS_REMOUNT)
		if os.Args[1] == "remount-ro" {
			flags |= syscall.MS_RDONLY
		}
		if err := syscall.Mount("", "/state", "", flags, ""); err != nil {
			panic(err)
		}
		fmt.Println("remounted-state-only")
		return
	}
	if os.Args[1] != "/crg" {
		panic("only the fixture candidate may be executed")
	}
	for _, capability := range []uintptr{1, 2} { // DAC_OVERRIDE, DAC_READ_SEARCH
		if _, _, err := syscall.RawSyscall(syscall.SYS_PRCTL, 24, capability, 0); err != 0 {
			panic(err)
		}
	}
	header := struct {
		Version uint32
		PID     int32
	}{Version: 0x20080522}
	data := [2]struct{ Effective, Permitted, Inheritable uint32 }{}
	if _, _, err := syscall.RawSyscall(syscall.SYS_CAPGET, uintptr(unsafe.Pointer(&header)), uintptr(unsafe.Pointer(&data)), 0); err != 0 {
		panic(err)
	}
	data[0].Effective &^= 6
	data[0].Permitted &^= 6
	data[0].Inheritable &^= 6
	if _, _, err := syscall.RawSyscall(syscall.SYS_CAPSET, uintptr(unsafe.Pointer(&header)), uintptr(unsafe.Pointer(&data)), 0); err != 0 {
		panic(err)
	}
	if _, _, err := syscall.RawSyscall(syscall.SYS_PRCTL, 38, 1, 0); err != 0 { // no_new_privs
		panic(err)
	}
	if err := syscall.Exec("/crg", os.Args[1:], os.Environ()); err != nil {
		panic(err)
	}
}
