//go:build linux && amd64

package main

import (
	"encoding/binary"
	"errors"

	"github.com/cilium/ebpf/asm"
)

// Only integers leave the BPF stack. Safe reads never follow user pointers.
// Re-reading the FD slot detects a changed reference but does not make the
// traversal atomic or prove an absence of every concurrent close/reuse race.
func kernelMetadata(h Hook, l KernelLayout) asm.Instructions {
	if h.Direction != "enter" && h.Call != "accept" && h.Call != "accept4" {
		return nil
	}
	a := asm.Instructions{asm.LoadMem(asm.R0, asm.RFP, -168, asm.DWord), asm.JSLT.Imm(asm.R0, 0, "metadata_done"), asm.JGT.Imm(asm.R0, 65535, "metadata_done"), asm.FnGetCurrentTask.Call(), asm.Mov.Reg(asm.R9, asm.R0)}
	read := func(off int16, size int) {
		a = append(a, asm.Mov.Reg(asm.R1, asm.RFP), asm.Add.Imm(asm.R1, -16), asm.Mov.Imm(asm.R2, int32(size)), asm.Mov.Reg(asm.R3, asm.R9), asm.Add.Imm(asm.R3, int32(off)), asm.FnProbeReadKernel.Call(), asm.JNE.Imm(asm.R0, 0, "metadata_done"))
	}
	field := func(key string) { f := l.Fields[key]; read(f.Offset, f.Bytes) }
	pointer := func(key string) {
		field(key)
		a = append(a, asm.LoadMem(asm.R9, asm.RFP, -16, asm.DWord), asm.JEq.Imm(asm.R9, 0, "metadata_done"))
	}
	pointer("task_struct.files")
	pointer("files_struct.fdt")
	a = append(a, asm.StoreMem(asm.RFP, -80, asm.R9, asm.DWord))
	field("fdtable.max_fds")
	a = append(a, asm.LoadMem(asm.R0, asm.RFP, -16, asm.Word), asm.LoadMem(asm.R1, asm.RFP, -168, asm.DWord), asm.JGE.Reg(asm.R1, asm.R0, "metadata_done"), asm.LoadMem(asm.R9, asm.RFP, -80, asm.DWord))
	pointer("fdtable.fd")
	a = append(a, asm.LoadMem(asm.R0, asm.RFP, -168, asm.DWord), asm.LSh.Imm(asm.R0, 3), asm.Add.Reg(asm.R9, asm.R0), asm.StoreMem(asm.RFP, -24, asm.R9, asm.DWord))
	read(0, 8)
	a = append(a, asm.LoadMem(asm.R9, asm.RFP, -16, asm.DWord), asm.JEq.Imm(asm.R9, 0, "metadata_done"), asm.StoreMem(asm.RFP, -32, asm.R9, asm.DWord))
	pointer("file.f_inode")
	a = append(a, asm.StoreMem(asm.RFP, -40, asm.R9, asm.DWord))
	field("inode.i_mode")
	a = append(a, asm.LoadMem(asm.R0, asm.RFP, -16, asm.Half), asm.StoreMem(asm.RFP, -88, asm.R0, asm.DWord), asm.And.Imm(asm.R0, 0xf000), asm.JEq.Imm(asm.R0, 0x8000, "regular_file"), asm.JNE.Imm(asm.R0, 0xc000, "metadata_done"), asm.LoadMem(asm.R9, asm.RFP, -40, asm.DWord))
	field("inode.i_ino")
	a = append(a, asm.LoadMem(asm.R0, asm.RFP, -16, asm.DWord), asm.JEq.Imm(asm.R0, 0, "metadata_done"), asm.StoreMem(asm.RFP, -48, asm.R0, asm.DWord), asm.LoadMem(asm.R9, asm.RFP, -32, asm.DWord))
	pointer("file.private_data")
	a = append(a, asm.StoreMem(asm.RFP, -80, asm.R9, asm.DWord))
	field("socket.type")
	a = append(a, asm.LoadMem(asm.R0, asm.RFP, -16, asm.Half), asm.JNE.Imm(asm.R0, 1, "metadata_done"), asm.LoadMem(asm.R9, asm.RFP, -80, asm.DWord))
	pointer("socket.sk")
	a = append(a, asm.StoreMem(asm.RFP, -56, asm.R9, asm.DWord))
	field("sock.__sk_common.skc_family")
	a = append(a, asm.LoadMem(asm.R0, asm.RFP, -16, asm.Half), asm.JNE.Imm(asm.R0, 2, "metadata_done"))
	field("sock.__sk_common.skc_state")
	a = append(a, asm.LoadMem(asm.R0, asm.RFP, -16, asm.Byte), asm.JEq.Imm(asm.R0, 1, "state_ok"), asm.JNE.Imm(asm.R0, 8, "metadata_done"), asm.Mov.Reg(asm.R9, asm.R9).WithSymbol("state_ok"))
	for _, key := range []string{"sock.__sk_common.skc_rcv_saddr", "sock.__sk_common.skc_daddr"} {
		field(key)
		a = append(a, asm.LoadMem(asm.R0, asm.RFP, -16, asm.Word), asm.JNE.Imm(asm.R0, 0x0100007f, "metadata_done"))
	}
	field("sock.__sk_common.skc_num")
	a = append(a, asm.LoadMem(asm.R0, asm.RFP, -16, asm.Half), asm.JEq.Imm(asm.R0, 0, "metadata_done"), asm.StoreMem(asm.RFP, -64, asm.R0, asm.DWord))
	field("sock.__sk_common.skc_dport")
	a = append(a, asm.LoadMem(asm.R0, asm.RFP, -16, asm.Half), asm.HostTo(asm.BE, asm.R0, asm.Half), asm.JEq.Imm(asm.R0, 0, "metadata_done"), asm.StoreMem(asm.RFP, -72, asm.R0, asm.DWord))
	// The file reference must still occupy this exact FD slot.
	a = append(a, asm.LoadMem(asm.R9, asm.RFP, -24, asm.DWord))
	read(0, 8)
	a = append(a, asm.LoadMem(asm.R0, asm.RFP, -16, asm.DWord), asm.LoadMem(asm.R1, asm.RFP, -32, asm.DWord), asm.JNE.Reg(asm.R0, asm.R1, "metadata_done"))
	// Commit metadata only after every type/value/reference check has succeeded.
	a = append(a, asm.LoadMem(asm.R0, asm.RFP, -64, asm.DWord), asm.StoreMem(asm.RFP, -144, asm.R0, asm.Half), asm.LoadMem(asm.R0, asm.RFP, -72, asm.DWord), asm.StoreMem(asm.RFP, -142, asm.R0, asm.Half), asm.LoadMem(asm.R0, asm.RFP, -48, asm.DWord), asm.StoreMem(asm.RFP, -136, asm.R0, asm.DWord), asm.StoreImm(asm.RFP, -140, 1, asm.Word), asm.Ja.Label("metadata_done"))
	// A regular file exports only inode, device, mode and flags, never contents.
	a = append(a, asm.LoadMem(asm.R9, asm.RFP, -40, asm.DWord).WithSymbol("regular_file"))
	field("inode.i_ino")
	a = append(a, asm.LoadMem(asm.R0, asm.RFP, -16, asm.DWord), asm.JEq.Imm(asm.R0, 0, "metadata_done"), asm.StoreMem(asm.RFP, -48, asm.R0, asm.DWord), asm.LoadMem(asm.R9, asm.RFP, -40, asm.DWord))
	pointer("inode.i_sb")
	field("super_block.s_dev")
	a = append(a, asm.LoadMem(asm.R0, asm.RFP, -16, asm.Word), asm.StoreMem(asm.RFP, -96, asm.R0, asm.DWord), asm.LoadMem(asm.R9, asm.RFP, -32, asm.DWord))
	field("file.f_flags")
	a = append(a, asm.LoadMem(asm.R0, asm.RFP, -16, asm.Word), asm.StoreMem(asm.RFP, -64, asm.R0, asm.DWord), asm.LoadMem(asm.R9, asm.RFP, -24, asm.DWord))
	read(0, 8)
	a = append(a, asm.LoadMem(asm.R0, asm.RFP, -16, asm.DWord), asm.LoadMem(asm.R1, asm.RFP, -32, asm.DWord), asm.JNE.Reg(asm.R0, asm.R1, "metadata_done"), asm.LoadMem(asm.R0, asm.RFP, -64, asm.DWord), asm.StoreMem(asm.RFP, -144, asm.R0, asm.Word), asm.LoadMem(asm.R0, asm.RFP, -48, asm.DWord), asm.StoreMem(asm.RFP, -136, asm.R0, asm.DWord), asm.LoadMem(asm.R0, asm.RFP, -96, asm.DWord), asm.StoreMem(asm.RFP, -128, asm.R0, asm.Word), asm.LoadMem(asm.R0, asm.RFP, -88, asm.DWord), asm.StoreMem(asm.RFP, -124, asm.R0, asm.Half), asm.StoreImm(asm.RFP, -140, 2, asm.Word), asm.Mov.Imm(asm.R0, 0).WithSymbol("metadata_done"))
	return a
}
func instructions(h Hook, targets, events, drops int, l KernelLayout) asm.Instructions {
	if h.Category == "writeback" {
		return waitInstructions(h, targets, events, drops)
	}
	a := asm.Instructions{asm.Mov.Reg(asm.R6, asm.R1), asm.FnGetCurrentPidTgid.Call(), asm.Mov.Reg(asm.R7, asm.R0), asm.RSh.Imm(asm.R0, 32), asm.StoreMem(asm.RFP, -4, asm.R0, asm.Word), asm.LoadMapPtr(asm.R1, targets), asm.Mov.Reg(asm.R2, asm.RFP), asm.Add.Imm(asm.R2, -4), asm.FnMapLookupElem.Call(), asm.JEq.Imm(asm.R0, 0, "done"), asm.LoadMem(asm.R8, asm.R0, 0, asm.DWord), asm.FnGetCurrentCgroupId.Call(), asm.JNE.Reg(asm.R0, asm.R8, "done")}
	for off := -192; off <= -128; off += 8 {
		a = append(a, asm.StoreImm(asm.RFP, int16(off), 0, asm.DWord))
	}
	a = append(a, asm.FnKtimeGetNs.Call(), asm.StoreMem(asm.RFP, -192, asm.R0, asm.DWord), asm.StoreMem(asm.RFP, -184, asm.R7, asm.DWord), asm.StoreImm(asm.RFP, -176, int64(h.Type), asm.Word), asm.LoadMem(asm.R0, asm.R6, h.Value.Offset, asm.DWord), asm.StoreMem(asm.RFP, -168, asm.R0, asm.DWord), asm.StoreMem(asm.RFP, -152, asm.R8, asm.DWord))
	if h.Count != nil {
		a = append(a, asm.LoadMem(asm.R0, asm.R6, h.Count.Offset, asm.DWord), asm.StoreMem(asm.RFP, -160, asm.R0, asm.DWord))
	}
	a = append(a, kernelMetadata(h, l)...)
	a = append(a, asm.Mov.Reg(asm.R1, asm.R6), asm.LoadMapPtr(asm.R2, events), asm.LoadImm(asm.R3, 0xffffffff, asm.DWord), asm.Mov.Reg(asm.R4, asm.RFP), asm.Add.Imm(asm.R4, -192), asm.Mov.Imm(asm.R5, 72), asm.FnPerfEventOutput.Call(), asm.JSGE.Imm(asm.R0, 0, "done"), asm.StoreImm(asm.RFP, -4, 0, asm.Word), asm.LoadMapPtr(asm.R1, drops), asm.Mov.Reg(asm.R2, asm.RFP), asm.Add.Imm(asm.R2, -4), asm.FnMapLookupElem.Call(), asm.JEq.Imm(asm.R0, 0, "done"), asm.Mov.Imm(asm.R1, 1), asm.StoreXAdd(asm.R0, asm.R1, asm.DWord), asm.Mov.Imm(asm.R0, 0).WithSymbol("done"), asm.Return())
	return a
}
func decodeMetadata(b []byte, p Plan, base proc, fd int64) (map[string]any, error) {
	flags := binary.LittleEndian.Uint32(b[52:56])
	lp := binary.LittleEndian.Uint16(b[48:50])
	rp := binary.LittleEndian.Uint16(b[50:52])
	inode := binary.LittleEndian.Uint64(b[56:64])
	device := binary.LittleEndian.Uint32(b[64:68])
	mode := binary.LittleEndian.Uint16(b[68:70])
	if binary.LittleEndian.Uint16(b[70:72]) != 0 {
		return nil, errors.New("METADATA_PADDING")
	}
	if flags == 2 {
		return decodeFileMetadata(b, p, base, fd, device, mode, inode)
	}
	if flags == 1 {
		if device != 0 || mode != 0 {
			return nil, errors.New("SOCKET_METADATA_EXTRA")
		}
		if lp == 0 || rp == 0 || inode == 0 || fd < 0 || fd > 65535 {
			return nil, errors.New("KERNEL_METADATA_VALUE")
		}
		return map[string]any{"kind": "loopback_socket", "local_port": lp, "remote_port": rp, "socket_inode": inode, "source": "event-time-safe-kernel-metadata", "non_atomic_kernel_traversal": true, "FD_slot_reference_rechecked": true}, nil
	}
	if flags != 0 || lp != 0 || rp != 0 || inode != 0 || device != 0 || mode != 0 {
		return nil, errors.New("KERNEL_METADATA_FLAGS")
	}
	// Preserve regular file/pipe annotations, but never substitute post-close
	// userspace socket observations for missing event-time kernel metadata.
	v := metadata(p, base, fd)
	if v["kind"] == "loopback_socket" {
		v = map[string]any{"kind": "unknown", "kernel_metadata_unavailable": true}
	}
	return v, nil
}
