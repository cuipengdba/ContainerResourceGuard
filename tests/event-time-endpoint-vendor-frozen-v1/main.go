//go:build linux && amd64

// Disposable host qualification tool. This is not part of CRG or its runtime.
package main

import (
	"bufio"
	"bytes"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"os/signal"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/cilium/ebpf"
	"github.com/cilium/ebpf/link"
	"github.com/cilium/ebpf/perf"
	"github.com/cilium/ebpf/rlimit"
	"golang.org/x/sys/unix"
)

const marker = "authorized-disposable-loopback-only"

type Plan struct {
	Vendor      *VendorScope `json:"vendor_fixture,omitempty"`
	OwnerPID    int          `json:"owner_pid"`
	OwnerStart  uint64       `json:"owner_start_ticks"`
	PID         int          `json:"pid"`
	Start       uint64       `json:"start_ticks"`
	ExeSHA      string       `json:"executable_sha256"`
	Probe       string       `json:"probe_path"`
	ProbeSHA    string       `json:"probe_sha256"`
	Cgroup      string       `json:"cgroup"`
	Duration    int          `json:"maximum_seconds"`
	ReaderDelay int          `json:"qualification_reader_delay_milliseconds"`
}
type proc struct {
	Start    uint64
	Parent   int
	State    string
	Cgroup   string
	Dev, Ino uint64
}
type Field struct {
	Offset int16 `json:"offset"`
	Size   int   `json:"size"`
	Signed bool  `json:"signed"`
}
type Hook struct {
	Name      string `json:"name"`
	Call      string `json:"call"`
	Direction string `json:"direction"`
	Type      uint32 `json:"type"`
	Value     Field  `json:"value"`
	Count     *Field `json:"count,omitempty"`
	SHA       string `json:"format_sha256"`
}
type Event struct {
	Mono      uint64         `json:"monotonic_ns"`
	Decoded   uint64         `json:"decoded_monotonic_ns"`
	PID       uint32         `json:"pid"`
	TID       uint32         `json:"tid"`
	Call      string         `json:"call"`
	Direction string         `json:"direction"`
	FD        int64          `json:"fd,omitempty"`
	Return    int64          `json:"return,omitempty"`
	Count     uint64         `json:"count,omitempty"`
	CgroupID  uint64         `json:"cgroup_id"`
	Metadata  map[string]any `json:"fd_metadata,omitempty"`
}
type Pair struct {
	Entry   Event  `json:"entry"`
	Exit    Event  `json:"exit"`
	Elapsed uint64 `json:"elapsed_ns"`
}
type Report struct {
	KernelLayout    *KernelLayout `json:"kernel_metadata_layout,omitempty"`
	VendorValidated bool          `json:"owned_vendor_fixture_validated"`
	Schema          string        `json:"schema"`
	Phase           string        `json:"phase"`
	Reason          string        `json:"reason,omitempty"`
	PlanSHA         string        `json:"plan_sha256"`
	ToolSHA         string        `json:"tool_sha256"`
	Target          int           `json:"target_pid"`
	Start           uint64        `json:"target_start_ticks"`
	CgroupID        uint64        `json:"cgroup_id"`
	Hooks           []Hook        `json:"hooks"`
	Programs        []uint32      `json:"program_ids"`
	Maps            []uint32      `json:"map_ids"`
	Events          []Event       `json:"events"`
	Pairs           []Pair        `json:"pairs"`
	PerfLost        uint64        `json:"perf_lost_samples"`
	OutputFailures  uint64        `json:"bpf_output_failures"`
	Trailing        uint64        `json:"ignored_kernel_padding_bytes"`
	Incomplete      bool          `json:"incomplete"`
	Errors          []string      `json:"diagnostic_errors"`
	CleanupErrors   []string      `json:"cleanup_errors"`
	Attached        bool          `json:"all_hooks_attached_before_ready"`
	Closed          bool          `json:"all_owned_handles_closed"`
	RawSaved        bool          `json:"raw_target_memory_pointers_buffers_payload_saved"`
	TargetMutations int           `json:"target_signals_or_control_writes"`
	Seconds         float64       `json:"elapsed_seconds"`
	CPU             float64       `json:"collector_cpu_seconds"`
	ReaderDelay     int           `json:"qualification_reader_delay_milliseconds"`
	Drained         bool          `json:"detached_stream_drained_to_deadline"`
}

func digest(b []byte) string { h := sha256.Sum256(b); return hex.EncodeToString(h[:]) }
func bounded(path string, max int64) ([]byte, error) {
	f, e := os.Open(path)
	if e != nil {
		return nil, e
	}
	defer f.Close()
	b, e := io.ReadAll(io.LimitReader(f, max+1))
	if e != nil {
		return nil, e
	}
	if int64(len(b)) > max {
		return nil, errors.New("READ_BOUND")
	}
	return b, nil
}
func fileSHA(path string) (string, error) {
	b, e := bounded(path, 64<<20)
	if e != nil {
		return "", e
	}
	return digest(b), nil
}
func identity(pid int) (proc, error) {
	var p proc
	b, e := bounded(fmt.Sprintf("/proc/%d/stat", pid), 8192)
	if e != nil {
		return p, e
	}
	s := strings.LastIndex(string(b), ")")
	if s < 0 {
		return p, errors.New("PROC_STAT")
	}
	a := strings.Fields(string(b)[s+1:])
	if len(a) < 20 {
		return p, errors.New("PROC_STAT")
	}
	p.State = a[0]
	p.Parent, _ = strconv.Atoi(a[1])
	p.Start, e = strconv.ParseUint(a[19], 10, 64)
	if e != nil {
		return p, e
	}
	b, e = bounded(fmt.Sprintf("/proc/%d/cgroup", pid), 4096)
	if e != nil {
		return p, e
	}
	lines := strings.Split(strings.TrimSpace(string(b)), "\n")
	if len(lines) != 1 || !strings.HasPrefix(lines[0], "0::/") {
		return p, errors.New("PURE_V2_REQUIRED")
	}
	p.Cgroup = strings.TrimPrefix(lines[0], "0::")
	var st unix.Stat_t
	if e = unix.Stat(fmt.Sprintf("/proc/%d/exe", pid), &st); e != nil {
		return p, e
	}
	p.Dev = uint64(st.Dev)
	p.Ino = st.Ino
	return p, nil
}
func sameIdentity(p Plan, base proc) bool {
	v, e := identity(p.PID)
	if e != nil || v.Start != base.Start || v.Parent != base.Parent || v.Cgroup != base.Cgroup || v.Dev != base.Dev || v.Ino != base.Ino || v.State == "Z" || v.State == "X" {
		return false
	}
	if p.Vendor == nil {
		return v.Parent == p.OwnerPID
	}
	return sameVendorFast(p)
}
func validate(p Plan) (proc, uint64, error) {
	limit := 20
	if p.Vendor != nil {
		limit = 180
	}
	if p.PID <= 1 || p.OwnerPID <= 1 || p.PID == os.Getpid() || p.OwnerPID != os.Getppid() || p.Duration < 1 || p.Duration > limit || p.ReaderDelay < 0 || p.ReaderDelay > 1000 {
		return proc{}, 0, errors.New("OWNED_PROBE_SCOPE")
	}
	owner, e := identity(p.OwnerPID)
	if e != nil || owner.Start != p.OwnerStart {
		return proc{}, 0, errors.New("OWNER_IDENTITY")
	}
	v, e := identity(p.PID)
	if e != nil || v.Start != p.Start || (p.Vendor == nil && v.Parent != p.OwnerPID) || v.Cgroup != p.Cgroup || v.State == "Z" {
		return v, 0, errors.New("TARGET_IDENTITY")
	}
	sh, e := fileSHA(fmt.Sprintf("/proc/%d/exe", p.PID))
	if e != nil || sh != p.ExeSHA {
		return v, 0, errors.New("EXECUTABLE_SHA")
	}
	if p.Vendor == nil {
		if !filepath.IsAbs(p.Probe) || !strings.HasPrefix(p.Probe, "/var/tmp/crg-bpf692-") || filepath.Base(p.Probe) != "own-http-with-blocked-pipe.py" {
			return v, 0, errors.New("OWNED_PROBE_PATH")
		}
		b, e := bounded(fmt.Sprintf("/proc/%d/cmdline", p.PID), 8192)
		if e != nil {
			return v, 0, e
		}
		args := bytes.Split(bytes.TrimRight(b, "\x00"), []byte{0})
		if len(args) != 2 || string(args[1]) != p.Probe {
			return v, 0, errors.New("OWNED_PROBE_CMDLINE")
		}
		sh, e := fileSHA(p.Probe)
		if e != nil || sh != p.ProbeSHA {
			return v, 0, errors.New("PROBE_SHA")
		}

	} else if e := validateVendor(p); e != nil {
		return v, 0, e
	}
	var st unix.Stat_t
	cg := filepath.Join("/sys/fs/cgroup", filepath.Clean(p.Cgroup))
	if e = unix.Stat(cg, &st); e != nil {
		return v, 0, e
	}
	var fs unix.Statfs_t
	if e = unix.Statfs(cg, &fs); e != nil || uint64(fs.Type) != 0x63677270 {
		return v, 0, errors.New("CGROUP2_FS")
	}
	if !sameIdentity(p, v) {
		return v, 0, errors.New("TARGET_IDENTITY_CHANGED")
	}
	return v, st.Ino, nil
}

var fieldRE = regexp.MustCompile(`field:[^;]*\b([A-Za-z_][A-Za-z_0-9]*)\s*;\s*offset:(\d+);\s*size:(\d+);\s*signed:([01]);`)

func field(raw []byte, name string, wantSigned bool) (Field, error) {
	var f Field
	count := 0
	for _, a := range fieldRE.FindAllStringSubmatch(string(raw), -1) {
		if a[1] != name {
			continue
		}
		count++
		o, _ := strconv.Atoi(a[2])
		n, _ := strconv.Atoi(a[3])
		if o < 0 || o > 256 || o%8 != 0 || n != 8 || (a[4] == "1") != wantSigned {
			return f, errors.New("TRACE_FIELD_LAYOUT")
		}
		f = Field{int16(o), n, wantSigned}
	}
	if count != 1 {
		return f, errors.New("TRACE_FIELD_MISSING")
	}
	return f, nil
}
func hooks() ([]Hook, error) {
	var out []Hook
	for i, call := range []string{"write", "recvfrom", "sendto", "accept", "accept4", "close"} {
		for d, dir := range []string{"enter", "exit"} {
			name := "sys_" + dir + "_" + call
			b, e := bounded("/sys/kernel/tracing/events/syscalls/"+name+"/format", 8192)
			if e != nil {
				return nil, errors.New("TRACE_FORMAT_UNAVAILABLE:" + name)
			}
			h := Hook{Name: name, Call: call, Direction: dir, Type: uint32(i*2 + d + 1), SHA: digest(b)}
			value := "fd"
			signed := false
			if dir == "exit" {
				value = "ret"
				signed = true
			}
			h.Value, e = field(b, value, signed)
			if e != nil {
				return nil, fmt.Errorf("%s:%w", name, e)
			}
			if call == "write" && dir == "enter" {
				f, e := field(b, "count", false)
				if e != nil {
					return nil, e
				}
				h.Count = &f
			}
			out = append(out, h)
		}
	}
	return out, nil
}
func mono() uint64 {
	var v unix.Timespec
	if unix.ClockGettime(unix.CLOCK_MONOTONIC, &v) != nil {
		return 0
	}
	return uint64(v.Sec)*1000000000 + uint64(v.Nsec)
}
func metadata(p Plan, base proc, fd int64) map[string]any {
	unknown := map[string]any{"kind": "unknown", "non_atomic_proc_observation": true}
	if fd < 0 || fd > 65535 || !sameIdentity(p, base) {
		return unknown
	}
	path := fmt.Sprintf("/proc/%d/fd/%d", p.PID, fd)
	name, e := os.Readlink(path)
	if e != nil || !sameIdentity(p, base) {
		return unknown
	}
	value := map[string]any{"kind": "other", "non_atomic_proc_observation": true}
	if strings.HasPrefix(name, "pipe:[") {
		value["kind"] = "pipe"
	}
	if name == "/opt/dbs/log/DBS.log" || name == "/opt/dbs/log/HISDBS.log" {
		value["kind"] = "vendor_log"
		value["path"] = name
	}
	if strings.HasPrefix(name, "socket:[") && strings.HasSuffix(name, "]") {
		value = unknown
		inode, e := strconv.ParseUint(strings.TrimSuffix(strings.TrimPrefix(name, "socket:["), "]"), 10, 64)
		if e != nil {
			return unknown
		}
		b, e := bounded(fmt.Sprintf("/proc/%d/net/tcp", p.PID), 1<<20)
		if e != nil {
			return unknown
		}
		for _, line := range strings.Split(string(b), "\n") {
			v := strings.Fields(line)
			if len(v) < 10 || v[9] != strconv.FormatUint(inode, 10) {
				continue
			}
			local := strings.Split(v[1], ":")
			remote := strings.Split(v[2], ":")
			if len(local) != 2 || len(remote) != 2 || local[0] != "0100007F" || remote[0] != "0100007F" {
				return unknown
			}
			lp, e1 := strconv.ParseUint(local[1], 16, 16)
			rp, e2 := strconv.ParseUint(remote[1], 16, 16)
			if e1 != nil || e2 != nil || lp == 0 || rp == 0 {
				return unknown
			}
			value = map[string]any{"kind": "loopback_socket", "socket_inode": inode, "local_port": lp, "remote_port": rp, "non_atomic_proc_observation": true}
			break
		}
	}
	again, e := os.Readlink(path)
	if e != nil || again != name || !sameIdentity(p, base) {
		return unknown
	}
	return value
}
func collect(p Plan, base proc, cgroup uint64, r *Report, out *os.File) error {
	if r.KernelLayout == nil {
		return errors.New("BTF_LAYOUT_REQUIRED")
	}
	started := time.Now()
	var cpuStart, cpuEnd syscall.Rusage
	syscall.Getrusage(syscall.RUSAGE_SELF, &cpuStart)
	defer func() {
		r.Seconds = time.Since(started).Seconds()
		syscall.Getrusage(syscall.RUSAGE_SELF, &cpuEnd)
		r.CPU = float64(cpuEnd.Utime.Nano()+cpuEnd.Stime.Nano()-cpuStart.Utime.Nano()-cpuStart.Stime.Nano()) / 1e9
	}()
	pidfd, e := unix.PidfdOpen(p.PID, 0)
	if e != nil {
		return errors.New("PIDFD_OPEN")
	}
	defer unix.Close(pidfd)
	if e = rlimit.RemoveMemlock(); e != nil {
		return errors.New("OWN_MEMLOCK")
	}
	var maps []*ebpf.Map
	var progs []*ebpf.Program
	var links []link.Link
	var reader *perf.Reader
	defer func() {
		for i := len(links) - 1; i >= 0; i-- {
			if e := links[i].Close(); e != nil {
				r.CleanupErrors = append(r.CleanupErrors, "LINK_CLOSE")
			}
		}
		if reader != nil {
			if e := reader.Close(); e != nil {
				r.CleanupErrors = append(r.CleanupErrors, "READER_CLOSE")
			}
		}
		for _, v := range progs {
			if e := v.Close(); e != nil {
				r.CleanupErrors = append(r.CleanupErrors, "PROGRAM_CLOSE")
			}
		}
		for _, v := range maps {
			if e := v.Close(); e != nil {
				r.CleanupErrors = append(r.CleanupErrors, "MAP_CLOSE")
			}
		}
		r.Closed = len(r.CleanupErrors) == 0
	}()
	newMap := func(spec *ebpf.MapSpec) (*ebpf.Map, error) {
		v, e := ebpf.NewMap(spec)
		if e != nil {
			return nil, e
		}
		maps = append(maps, v)
		info, e := v.Info()
		if e != nil {
			return nil, e
		}
		id, ok := info.ID()
		if !ok {
			return nil, errors.New("MAP_ID")
		}
		r.Maps = append(r.Maps, uint32(id))
		return v, nil
	}
	targets, e := newMap(&ebpf.MapSpec{Name: "crg692_targets", Type: ebpf.Hash, KeySize: 4, ValueSize: 8, MaxEntries: 1})
	if e != nil {
		return errors.New("TARGET_MAP_LOAD")
	}
	events, e := newMap(&ebpf.MapSpec{Name: "crg692_events", Type: ebpf.PerfEventArray})
	if e != nil {
		return errors.New("EVENT_MAP_LOAD")
	}
	drops, e := newMap(&ebpf.MapSpec{Name: "crg692_drops", Type: ebpf.Array, KeySize: 4, ValueSize: 8, MaxEntries: 1})
	if e != nil {
		return errors.New("DROPS_MAP_LOAD")
	}
	reader, e = perf.NewReader(events, os.Getpagesize()*4)
	if e != nil {
		return errors.New("PERF_READER_OPEN")
	}
	key := uint32(p.PID)
	if e = targets.Put(key, cgroup); e != nil {
		return errors.New("TARGET_MAP_PUT")
	}
	for _, h := range r.Hooks {
		pr, e := ebpf.NewProgram(&ebpf.ProgramSpec{Name: fmt.Sprintf("crg692_%02d", h.Type), Type: ebpf.TracePoint, License: "GPL", Instructions: instructions(h, targets.FD(), events.FD(), drops.FD(), *r.KernelLayout)})
		if e != nil {
			return fmt.Errorf("PROGRAM_LOAD:%s:%s", h.Name, safeError(e))
		}
		progs = append(progs, pr)
		info, e := pr.Info()
		if e != nil {
			return errors.New("PROGRAM_INFO")
		}
		id, ok := info.ID()
		if !ok {
			return errors.New("PROGRAM_ID")
		}
		r.Programs = append(r.Programs, uint32(id))
		ln, e := link.Tracepoint("syscalls", h.Name, pr, nil)
		if e != nil {
			return errors.New("TRACEPOINT_ATTACH:" + h.Name)
		}
		links = append(links, ln)
	}
	if !sameIdentity(p, base) {
		return errors.New("TARGET_CHANGED_BEFORE_READY")
	}
	r.Attached = true
	ready, _ := json.Marshal(map[string]any{"phase": "ready", "program_ids": r.Programs, "map_ids": r.Maps, "cgroup_id": cgroup})
	fmt.Println(string(ready))
	stop := make(chan string, 1)
	go func() {
		bufio.NewReader(io.LimitReader(os.Stdin, 16)).ReadString('\n')
		select {
		case stop <- "controller-stdin":
		default:
		}
	}()
	sig := make(chan os.Signal, 1)
	signal.Notify(sig, os.Interrupt, syscall.SIGTERM)
	defer signal.Stop(sig)
	end := time.Now().Add(time.Duration(p.Duration) * time.Second)
	r.ReaderDelay = p.ReaderDelay
	time.Sleep(time.Duration(p.ReaderDelay) * time.Millisecond)
	stopping := false
	stopReason := ""
	drainUntil := time.Time{}
	hookMap := map[uint32]Hook{}
	for _, h := range r.Hooks {
		hookMap[h.Type] = h
	}
	for {
		if !stopping {
			select {
			case stopReason = <-stop:
				stopping = true
			case <-sig:
				stopReason = "own-signal"
				stopping = true
			default:
			}
			if time.Now().After(end) {
				stopReason = "duration-bound"
				stopping = true
				r.Incomplete = true
			}
			if !sameIdentity(p, base) {
				stopReason = "target-identity-ended"
				stopping = true
				r.Incomplete = true
			}
			if stopping {
				for _, ln := range links {
					if e := ln.Close(); e != nil {
						r.CleanupErrors = append(r.CleanupErrors, "DETACH")
					}
				}
				links = nil
				drainUntil = time.Now().Add(150 * time.Millisecond)
			}
		}
		if stopping && time.Now().After(drainUntil) {
			r.Incomplete = true
			break
		}
		reader.SetDeadline(time.Now().Add(25 * time.Millisecond))
		rec, e := reader.Read()
		decoded := mono()
		if errors.Is(e, os.ErrDeadlineExceeded) {
			if stopping {
				r.Drained = true
				break
			}
			continue
		}
		if e != nil {
			return errors.New("PERF_READ")
		}
		if rec.LostSamples > 0 {
			r.PerfLost += rec.LostSamples
			r.Incomplete = true
			continue
		}
		b := rec.RawSample
		if len(b) < 64 || len(b) > 71 {
			return errors.New("SAMPLE_SIZE")
		}
		r.Trailing += uint64(len(b) - 64)
		if binary.LittleEndian.Uint32(b[20:24]) != 0 {
			return errors.New("SAMPLE_PADDING")
		}
		h, ok := hookMap[binary.LittleEndian.Uint32(b[16:20])]
		if !ok {
			return errors.New("EVENT_TYPE")
		}
		tg := binary.LittleEndian.Uint64(b[8:16])
		event := Event{Mono: binary.LittleEndian.Uint64(b[:8]), Decoded: decoded, PID: uint32(tg >> 32), TID: uint32(tg), Call: h.Call, Direction: h.Direction, CgroupID: binary.LittleEndian.Uint64(b[40:48])}
		if event.PID != uint32(p.PID) || event.CgroupID != cgroup || event.Mono == 0 || decoded < event.Mono || !sameIdentity(p, base) {
			return errors.New("EVENT_IDENTITY_OR_CLOCK")
		}
		if h.Direction == "enter" {
			event.FD = int64(binary.LittleEndian.Uint64(b[24:32]))
			event.Count = binary.LittleEndian.Uint64(b[32:40])
			event.Metadata, e = decodeMetadata(b, p, base, event.FD)
			if e != nil {
				return e
			}
		} else {
			event.Return = int64(binary.LittleEndian.Uint64(b[24:32]))
			if h.Call == "accept" || h.Call == "accept4" {
				event.Metadata, e = decodeMetadata(b, p, base, event.Return)
				if e != nil {
					return e
				}
			}
		}
		r.Events = append(r.Events, event)
		if len(r.Events) > 20000 {
			return errors.New("EVENT_COUNT_BOUND")
		}
	}
	var zero uint32
	if e = drops.Lookup(zero, &r.OutputFailures); e != nil {
		return errors.New("DROPS_LOOKUP")
	}
	if r.OutputFailures > 0 {
		r.Incomplete = true
	}
	r.Reason = stopReason
	sort.SliceStable(r.Events, func(i, j int) bool { return r.Events[i].Mono < r.Events[j].Mono })
	pending := map[uint32]Event{}
	for _, ev := range r.Events {
		if ev.Direction == "enter" {
			if _, ok := pending[ev.TID]; ok {
				r.Incomplete = true
			}
			pending[ev.TID] = ev
			continue
		}
		a, ok := pending[ev.TID]
		if !ok || a.Call != ev.Call || ev.Mono < a.Mono {
			r.Incomplete = true
			continue
		}
		r.Pairs = append(r.Pairs, Pair{a, ev, ev.Mono - a.Mono})
		delete(pending, ev.TID)
	}
	if len(pending) > 0 {
		r.Incomplete = true
	}
	return nil
}

var hexRE = regexp.MustCompile(`0x[0-9a-fA-F]+`)

func safeError(e error) string {
	s := hexRE.ReplaceAllString(e.Error(), "[redacted-hex]")
	if len(s) > 512 {
		s = s[:512]
	}
	return s
}
func run() (code int) {
	planPath := flag.String("plan", "", "private owned-probe plan")
	output := flag.String("output", "", "fresh private JSON output")
	execute := flag.Bool("execute", false, "attach temporary programs to explicitly owned host probe")
	flag.Parse()
	r := Report{Schema: "crg-direct-bpf-kernel-endpoint-prototype-v1", Phase: "rejected", Errors: []string{}, CleanupErrors: []string{}, Events: []Event{}, Pairs: []Pair{}}
	if *output == "" {
		fmt.Println(`{"phase":"rejected","reason":"OUTPUT_REQUIRED"}`)
		return 1
	}
	f, e := os.OpenFile(*output, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if e != nil {
		fmt.Println(`{"phase":"rejected","reason":"FRESH_OUTPUT_REQUIRED"}`)
		return 1
	}
	defer f.Close()
	defer func() {
		b, e := json.MarshalIndent(r, "", "  ")
		if e == nil && len(b) < 32<<20 {
			_, e = f.Write(append(b, '\n'))
		}
		if e != nil {
			code = 1
		}
		fmt.Println(`{"phase":"finished"}`)
	}()
	reject := func(s string) int { r.Reason = s; return 1 }
	if *execute && os.Getenv("CRG_DIRECT_BPF") != marker {
		return reject("EXPLICIT_LAB_MARKER")
	}
	b, e := bounded(*planPath, 16384)
	if e != nil {
		return reject("PLAN_READ")
	}
	r.PlanSHA = digest(b)
	var p Plan
	d := json.NewDecoder(bytes.NewReader(b))
	d.DisallowUnknownFields()
	if e = d.Decode(&p); e != nil {
		return reject("PLAN_JSON")
	}
	if d.Decode(new(any)) != io.EOF {
		return reject("PLAN_TRAILING")
	}
	if *execute && p.Vendor != nil && os.Getenv("CRG_DIRECT_BPF_VENDOR") != "owned-fresh-vendor-fixture-only" {
		return reject("EXPLICIT_VENDOR_LAB_MARKER")
	}
	r.Target = p.PID
	r.Start = p.Start
	r.ToolSHA, _ = fileSHA("/proc/self/exe")
	base, cgroup, e := validate(p)
	if e != nil {
		return reject(safeError(e))
	}
	r.VendorValidated = p.Vendor != nil
	layout, e := loadKernelLayout()
	if e != nil {
		return reject(safeError(e))
	}
	r.KernelLayout = &layout
	r.CgroupID = cgroup
	r.Hooks, e = hooks()
	if e != nil {
		return reject(safeError(e))
	}
	if !*execute {
		r.Phase = "preflight-readonly"
		r.Reason = "execute-and-explicit-marker-required"
		return 0
	}
	r.Phase = "running"
	e = collect(p, base, cgroup, &r, f)
	if e != nil {
		r.Phase = "failed"
		r.Reason = safeError(e)
		r.Errors = append(r.Errors, r.Reason)
		r.Incomplete = true
		return 1
	}
	if len(r.CleanupErrors) > 0 {
		r.Phase = "failed"
		r.Incomplete = true
		return 1
	}
	r.Phase = "collected"
	return 0
}
func main() { os.Exit(run()) }
