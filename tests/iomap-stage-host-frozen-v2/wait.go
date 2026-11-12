//go:build linux && amd64

package main

import (
	"encoding/binary"
	"errors"
	"fmt"
	"os"

	"github.com/cilium/ebpf/asm"
	"golang.org/x/sys/unix"
)

type NamedField struct {
	Name  string `json:"name"`
	Field Field  `json:"layout"`
}

func hookCategory(h Hook) string {
	if h.Category != "" {
		return h.Category
	}
	return "syscalls"
}
func addWaitHooks(out []Hook) ([]Hook, error) {
	wanted := []struct {
		name   string
		fields []struct {
			name   string
			signed bool
		}
	}{
		{"balance_dirty_pages", []struct {
			name   string
			signed bool
		}{{"paused", false}, {"pause", true}, {"dirty", false}, {"bdi_dirty", false}, {"cgroup_ino", false}}},
		{"folio_wait_writeback", []struct {
			name   string
			signed bool
		}{{"ino", false}, {"index", false}}},
	}
	for i, w := range wanted {
		raw, e := bounded("/sys/kernel/tracing/events/writeback/"+w.name+"/format", 16384)
		if e != nil {
			return nil, errors.New("WAIT_TRACE_FORMAT:" + w.name)
		}
		h := Hook{Category: "writeback", Name: w.name, Call: w.name, Direction: "metadata", Type: uint32(101 + i), SHA: digest(raw)}
		for _, v := range w.fields {
			f, e := field(raw, v.name, v.signed)
			if e != nil {
				return nil, fmt.Errorf("WAIT_TRACE_FIELD:%s:%s", w.name, v.name)
			}
			h.Numbers = append(h.Numbers, NamedField{v.name, f})
		}
		out = append(out, h)
	}
	return out, nil
}

var waitOffsets = []int{24, 32, 48, 56, 64}

func decodeWait(h Hook, b []byte) map[string]any {
	out := map[string]any{}
	for i, f := range h.Numbers {
		v := binary.LittleEndian.Uint64(b[waitOffsets[i] : waitOffsets[i]+8])
		if f.Field.Signed {
			out[f.Name] = int64(v)
		} else {
			out[f.Name] = v
		}
	}
	return out
}
func waitInstructions(h Hook, targets, events, drops, scope int) asm.Instructions {
	a := asm.Instructions{asm.Mov.Reg(asm.R6, asm.R1), asm.FnGetCurrentPidTgid.Call(), asm.Mov.Reg(asm.R7, asm.R0), asm.RSh.Imm(asm.R0, 32), asm.StoreMem(asm.RFP, -4, asm.R0, asm.Word), asm.LoadMapPtr(asm.R1, targets), asm.Mov.Reg(asm.R2, asm.RFP), asm.Add.Imm(asm.R2, -4), asm.FnMapLookupElem.Call(), asm.JEq.Imm(asm.R0, 0, "done"), asm.LoadMem(asm.R8, asm.R0, 0, asm.DWord), asm.FnGetCurrentCgroupId.Call(), asm.JNE.Reg(asm.R0, asm.R8, "done")}
	if h.Category == "function" && isStage(h.Name) {
		a = append(a, stageFilter(scope)...)
	}
	for off := -192; off <= -128; off += 8 {
		a = append(a, asm.StoreImm(asm.RFP, int16(off), 0, asm.DWord))
	}
	a = append(a, asm.FnKtimeGetNs.Call(), asm.StoreMem(asm.RFP, -192, asm.R0, asm.DWord), asm.StoreMem(asm.RFP, -184, asm.R7, asm.DWord), asm.StoreImm(asm.RFP, -176, int64(h.Type), asm.Word), asm.StoreMem(asm.RFP, -152, asm.R8, asm.DWord))
	for i, f := range h.Numbers {
		a = append(a, asm.LoadMem(asm.R0, asm.R6, f.Field.Offset, asm.DWord), asm.StoreMem(asm.RFP, int16(-192+waitOffsets[i]), asm.R0, asm.DWord))
	}
	a = append(a, asm.Mov.Reg(asm.R1, asm.R6), asm.LoadMapPtr(asm.R2, events), asm.LoadImm(asm.R3, 0xffffffff, asm.DWord), asm.Mov.Reg(asm.R4, asm.RFP), asm.Add.Imm(asm.R4, -192), asm.Mov.Imm(asm.R5, 72), asm.FnPerfEventOutput.Call(), asm.JSGE.Imm(asm.R0, 0, "done"), asm.StoreImm(asm.RFP, -4, 0, asm.Word), asm.LoadMapPtr(asm.R1, drops), asm.Mov.Reg(asm.R2, asm.RFP), asm.Add.Imm(asm.R2, -4), asm.FnMapLookupElem.Call(), asm.JEq.Imm(asm.R0, 0, "done"), asm.Mov.Imm(asm.R1, 1), asm.StoreXAdd(asm.R0, asm.R1, asm.DWord), asm.Mov.Imm(asm.R0, 0).WithSymbol("done"), asm.Return())
	return a
}
func decodeFileMetadata(b []byte, p Plan, base proc, fd int64, device uint32, mode uint16, inode uint64) (map[string]any, error) {
	if inode == 0 || mode&0xf000 != 0x8000 || fd < 0 || fd > 65535 {
		return nil, errors.New("KERNEL_FILE_METADATA_VALUE")
	}
	major, minor := device>>20, device&((1<<20)-1)
	v := map[string]any{"kind": "regular_file", "source": "event-time-safe-kernel-file-metadata", "inode": inode, "device_major": major, "device_minor": minor, "file_mode": mode, "file_flags": binary.LittleEndian.Uint32(b[48:52]), "non_atomic_kernel_traversal": true, "FD_slot_reference_rechecked": true}
	// Path labels are optional separate non-atomic proc observations. Require the
	// current inode, device, mode and readlink to match before annotating a log.
	path := fmt.Sprintf("/proc/%d/fd/%d", p.PID, fd)
	name, e := os.Readlink(path)
	if e != nil || (name != "/opt/dbs/log/DBS.log" && name != "/opt/dbs/log/HISDBS.log") || !sameIdentity(p, base) {
		return v, nil
	}
	var st unix.Stat_t
	if unix.Stat(path, &st) != nil || st.Ino != inode || unix.Major(st.Dev) != major || unix.Minor(st.Dev) != minor || st.Mode != uint32(mode) {
		return v, nil
	}
	again, e := os.Readlink(path)
	if e != nil || again != name || !sameIdentity(p, base) {
		return v, nil
	}
	v["kind"] = "vendor_log"
	v["path"] = name
	v["non_atomic_proc_path_annotation"] = true
	return v, nil
}
