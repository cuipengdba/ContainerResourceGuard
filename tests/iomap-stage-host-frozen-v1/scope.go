//go:build linux && amd64

package main

import "github.com/cilium/ebpf/asm"

// These additional page-loop functions are scoped to validated regular-file
// write(2) calls of 1..4096 bytes. The original five functions remain unscoped.
var stageNames = []string{"iomap_iter", "iomap_write_iter", "iomap_write_begin", "iomap_write_end", "iomap_get_folio", "__filemap_get_folio", "__iomap_write_begin", "balance_dirty_pages_ratelimited_flags"}

func isStage(name string) bool {
	for _, v := range stageNames {
		if v == name {
			return true
		}
	}
	return false
}

// R7 is current pid_tgid, R8 is the already validated current cgroup. No
// register argument or function pointer is read. Stack and labels are distinct
// from the existing syscall metadata and output machinery.
func stageFilter(scope int) asm.Instructions {
	return asm.Instructions{asm.StoreMem(asm.RFP, -216, asm.R7, asm.DWord), asm.LoadMapPtr(asm.R1, scope), asm.Mov.Reg(asm.R2, asm.RFP), asm.Add.Imm(asm.R2, -216), asm.FnMapLookupElem.Call(), asm.JEq.Imm(asm.R0, 0, "done"), asm.LoadMem(asm.R0, asm.R0, 0, asm.DWord), asm.JNE.Reg(asm.R0, asm.R8, "done")}
}

func scopeError(errors int) asm.Instructions {
	return asm.Instructions{asm.StoreImm(asm.RFP, -224, 0, asm.Word), asm.LoadMapPtr(asm.R1, errors), asm.Mov.Reg(asm.R2, asm.RFP), asm.Add.Imm(asm.R2, -224), asm.FnMapLookupElem.Call(), asm.JEq.Imm(asm.R0, 0, "scope_done"), asm.Mov.Imm(asm.R1, 1), asm.StoreXAdd(asm.R0, asm.R1, asm.DWord)}
}

func writeScope(h Hook, scope, errors int) asm.Instructions {
	if h.Call != "write" || h.Category != "" {
		return nil
	}
	a := asm.Instructions{asm.StoreMem(asm.RFP, -216, asm.R7, asm.DWord)}
	if h.Direction == "enter" {
		// Refuse an existing entry; this thread cannot legitimately be in two
		// write syscalls at once. Record failure instead of silently replacing it.
		a = append(a, asm.LoadMapPtr(asm.R1, scope), asm.Mov.Reg(asm.R2, asm.RFP), asm.Add.Imm(asm.R2, -216), asm.FnMapLookupElem.Call(), asm.JNE.Imm(asm.R0, 0, "scope_error"), asm.LoadMem(asm.R0, asm.RFP, -160, asm.DWord), asm.JEq.Imm(asm.R0, 0, "scope_done"), asm.JGT.Imm(asm.R0, 4096, "scope_done"), asm.LoadMem(asm.R0, asm.RFP, -140, asm.Word), asm.JNE.Imm(asm.R0, 2, "scope_done"), asm.StoreMem(asm.RFP, -232, asm.R8, asm.DWord), asm.LoadMapPtr(asm.R1, scope), asm.Mov.Reg(asm.R2, asm.RFP), asm.Add.Imm(asm.R2, -216), asm.Mov.Reg(asm.R3, asm.RFP), asm.Add.Imm(asm.R3, -232), asm.Mov.Imm(asm.R4, 1), asm.FnMapUpdateElem.Call(), asm.JEq.Imm(asm.R0, 0, "scope_done"))
	} else {
		// Every write exit deletes the gate, including short/error returns. An
		// absent key is expected for unselected writes and is not an error.
		a = append(a, asm.LoadMapPtr(asm.R1, scope), asm.Mov.Reg(asm.R2, asm.RFP), asm.Add.Imm(asm.R2, -216), asm.FnMapDeleteElem.Call(), asm.JEq.Imm(asm.R0, 0, "scope_done"), asm.JEq.Imm(asm.R0, -2, "scope_done"))
	}
	a = append(a, asm.Mov.Reg(asm.R0, asm.R0).WithSymbol("scope_error"))
	a = append(a, scopeError(errors)...)
	a = append(a, asm.Mov.Reg(asm.R0, asm.R0).WithSymbol("scope_done"))
	return a
}
