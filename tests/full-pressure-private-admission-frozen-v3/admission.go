//go:build linux && amd64

package main

import (
	"errors"
	"github.com/cilium/ebpf"
	"github.com/cilium/ebpf/asm"
)

// This is a diagnostic candidate. Raw boundary events are retained, and the
// original whole-stream incomplete result is never reset by admission analysis.
const admissionDrainMilliseconds = 1000

type admissionKey struct {
	PIDTID    uint64
	TaskStart uint64
}
type admissionState struct {
	Syscall  uint32
	Depth    uint32
	Reserved uint64
}
type AdmissionRecord struct {
	PID       uint32 `json:"pid"`
	TID       uint32 `json:"tid"`
	TaskStart uint64 `json:"task_start_boottime_ns"`
	Syscall   uint32 `json:"syscall_enter_hook"`
	Depth     uint32 `json:"function_depth"`
}
type AdmissionReport struct {
	Policy                 string            `json:"policy"`
	Closing                bool              `json:"closing_requested"`
	ClosingMono            uint64            `json:"closing_observed_monotonic_ns"`
	Quiesced               bool              `json:"admitted_calls_quiesced_before_detach"`
	Timeout                bool              `json:"drain_timed_out"`
	DrainMilliseconds      int               `json:"maximum_admission_drain_milliseconds"`
	Errors                 uint64            `json:"admission_errors"`
	InFlight               uint64            `json:"probe_invocations_in_flight_after_detach"`
	BoundaryCounter        uint64            `json:"kernel_boundary_event_counter"`
	Final                  []AdmissionRecord `json:"final_thread_states"`
	BoundaryEvents         int               `json:"retained_raw_boundary_events"`
	InvalidEvents          int               `json:"retained_raw_invalid_events"`
	AdmittedEvents         int               `json:"admitted_event_count"`
	AdmittedPairs          []Pair            `json:"admitted_syscall_pairs"`
	AdmittedFunctionPairs  []Pair            `json:"admitted_function_pairs"`
	AdmittedFunctionIssues []string          `json:"admitted_function_pair_issues"`
	AdmittedIncomplete     bool              `json:"admitted_stream_incomplete"`
	RawIncomplete          bool              `json:"original_whole_raw_stream_incomplete"`
}

// Control indexes: 0 closing, 1 currently executing probe invocations,
// 2 explicit admission errors, 3 boundary events. The closing program uses
// atomic add, which provides the commit barrier before userspace reads guard.
// No userspace read/modify/write overwrites kernel counters.
func admissionCloser(control int) asm.Instructions {
	return asm.Instructions{
		asm.StoreImm(asm.RFP, -4, 0, asm.Word), asm.LoadMapPtr(asm.R1, control), asm.Mov.Reg(asm.R2, asm.RFP), asm.Add.Imm(asm.R2, -4), asm.FnMapLookupElem.Call(), asm.JEq.Imm(asm.R0, 0, "close_bad"),
		asm.LoadMem(asm.R1, asm.R0, 0, asm.DWord), asm.JNE.Imm(asm.R1, 0, "close_bad"), asm.Mov.Imm(asm.R1, 1), asm.StoreXAdd(asm.R0, asm.R1, asm.DWord), asm.Mov.Imm(asm.R0, 0), asm.Return(),
		asm.Mov.Imm(asm.R0, 1).WithSymbol("close_bad"), asm.Return(),
	}
}

func admissionInstructions(h Hook, states, control int, start KernelField) asm.Instructions {
	a := asm.Instructions{asm.StoreImm(asm.RFP, -320, 0, asm.Word)}
	lookupControl := func(index int32) {
		a = append(a, asm.StoreImm(asm.RFP, -328, int64(index), asm.Word), asm.LoadMapPtr(asm.R1, control), asm.Mov.Reg(asm.R2, asm.RFP), asm.Add.Imm(asm.R2, -328), asm.FnMapLookupElem.Call())
	}
	lookupControl(1)
	a = append(a, asm.JEq.Imm(asm.R0, 0, "admission_bad"), asm.StoreMem(asm.RFP, -296, asm.R0, asm.DWord), asm.Mov.Imm(asm.R1, 1), asm.StoreXAdd(asm.R0, asm.R1, asm.DWord), asm.StoreImm(asm.RFP, -304, 1, asm.Word))
	lookupControl(0)
	a = append(a, asm.JEq.Imm(asm.R0, 0, "admission_bad"), asm.LoadMem(asm.R0, asm.R0, 0, asm.DWord), asm.StoreMem(asm.RFP, -288, asm.R0, asm.DWord), asm.StoreMem(asm.RFP, -256, asm.R7, asm.DWord), asm.FnGetCurrentTask.Call(), asm.Mov.Reg(asm.R3, asm.R0), asm.Add.Imm(asm.R3, int32(start.Offset)), asm.Mov.Reg(asm.R1, asm.RFP), asm.Add.Imm(asm.R1, -248), asm.Mov.Imm(asm.R2, 8), asm.FnProbeReadKernel.Call(), asm.JNE.Imm(asm.R0, 0, "admission_bad"), asm.LoadMem(asm.R0, asm.RFP, -248, asm.DWord), asm.JEq.Imm(asm.R0, 0, "admission_bad"))
	lookupState := func() {
		a = append(a, asm.LoadMapPtr(asm.R1, states), asm.Mov.Reg(asm.R2, asm.RFP), asm.Add.Imm(asm.R2, -256), asm.FnMapLookupElem.Call())
	}
	lookupState()
	syscallEntry := h.Category == "" && h.Direction == "enter"
	if syscallEntry {
		a = append(a, asm.JNE.Imm(asm.R0, 0, "admission_have_state"), asm.LoadMem(asm.R0, asm.RFP, -288, asm.DWord), asm.JNE.Imm(asm.R0, 0, "admission_boundary"), asm.StoreImm(asm.RFP, -280, 0, asm.DWord), asm.StoreImm(asm.RFP, -272, 0, asm.DWord), asm.LoadMapPtr(asm.R1, states), asm.Mov.Reg(asm.R2, asm.RFP), asm.Add.Imm(asm.R2, -256), asm.Mov.Reg(asm.R3, asm.RFP), asm.Add.Imm(asm.R3, -280), asm.Mov.Imm(asm.R4, 1), asm.FnMapUpdateElem.Call(), asm.JNE.Imm(asm.R0, 0, "admission_bad"))
		lookupState()
		a = append(a, asm.JEq.Imm(asm.R0, 0, "admission_bad"))
	} else {
		a = append(a, asm.JEq.Imm(asm.R0, 0, "admission_boundary"))
	}
	a = append(a, asm.Mov.Reg(asm.R9, asm.R0).WithSymbol("admission_have_state"))
	if syscallEntry {
		a = append(a, asm.LoadMem(asm.R0, asm.R9, 0, asm.Word), asm.JNE.Imm(asm.R0, 0, "admission_bad"), asm.LoadMem(asm.R0, asm.R9, 4, asm.Word), asm.JNE.Imm(asm.R0, 0, "admission_bad"), asm.LoadMem(asm.R0, asm.RFP, -288, asm.DWord), asm.JNE.Imm(asm.R0, 0, "admission_boundary"), asm.StoreImm(asm.R9, 0, int64(h.Type), asm.Word), asm.Ja.Label("admission_ready"))
	} else if h.Category == "" && h.Direction == "exit" {
		a = append(a, asm.LoadMem(asm.R0, asm.R9, 0, asm.Word), asm.JEq.Imm(asm.R0, 0, "admission_no_active"), asm.JNE.Imm(asm.R0, int32(h.Type-1), "admission_bad"), asm.LoadMem(asm.R0, asm.R9, 4, asm.Word), asm.JNE.Imm(asm.R0, 0, "admission_bad"), asm.StoreImm(asm.R9, 0, 0, asm.Word), asm.Ja.Label("admission_ready"))
	} else if h.Direction == "function_enter" {
		a = append(a, asm.LoadMem(asm.R0, asm.RFP, -288, asm.DWord), asm.JEq.Imm(asm.R0, 0, "admission_function_enter"), asm.LoadMem(asm.R0, asm.R9, 0, asm.Word), asm.JNE.Imm(asm.R0, 0, "admission_function_enter"), asm.LoadMem(asm.R0, asm.R9, 4, asm.Word), asm.JEq.Imm(asm.R0, 0, "admission_boundary"), asm.LoadMem(asm.R0, asm.R9, 4, asm.Word).WithSymbol("admission_function_enter"), asm.JGE.Imm(asm.R0, 64, "admission_bad"), asm.Mov.Reg(asm.R0, asm.R9), asm.Add.Imm(asm.R0, 4), asm.Mov.Imm(asm.R1, 1), asm.StoreXAdd(asm.R0, asm.R1, asm.Word), asm.Ja.Label("admission_ready"))
	} else if h.Direction == "function_exit" {
		a = append(a, asm.LoadMem(asm.R0, asm.R9, 4, asm.Word), asm.JEq.Imm(asm.R0, 0, "admission_no_active"), asm.Mov.Reg(asm.R0, asm.R9), asm.Add.Imm(asm.R0, 4), asm.Mov.Imm(asm.R1, -1), asm.StoreXAdd(asm.R0, asm.R1, asm.Word), asm.Ja.Label("admission_ready"))
	} else {
		a = append(a, asm.LoadMem(asm.R0, asm.RFP, -288, asm.DWord), asm.JEq.Imm(asm.R0, 0, "admission_ready"), asm.LoadMem(asm.R0, asm.R9, 0, asm.Word), asm.JNE.Imm(asm.R0, 0, "admission_ready"), asm.LoadMem(asm.R0, asm.R9, 4, asm.Word), asm.JEq.Imm(asm.R0, 0, "admission_boundary"), asm.Ja.Label("admission_ready"))
	}
	if h.Category == "" && h.Direction == "exit" || h.Direction == "function_exit" {
		a = append(a, asm.LoadMem(asm.R0, asm.RFP, -288, asm.DWord).WithSymbol("admission_no_active"), asm.JEq.Imm(asm.R0, 0, "admission_bad"), asm.Ja.Label("admission_boundary"))
	}
	a = append(a, asm.StoreImm(asm.RFP, -320, 2, asm.Word).WithSymbol("admission_bad"))
	lookupControl(2)
	a = append(a, asm.JEq.Imm(asm.R0, 0, "admission_ready"), asm.Mov.Imm(asm.R1, 1), asm.StoreXAdd(asm.R0, asm.R1, asm.DWord), asm.Ja.Label("admission_ready"), asm.StoreImm(asm.RFP, -320, 1, asm.Word).WithSymbol("admission_boundary"))
	lookupControl(3)
	a = append(a, asm.JEq.Imm(asm.R0, 0, "admission_ready"), asm.Mov.Imm(asm.R1, 1), asm.StoreXAdd(asm.R0, asm.R1, asm.DWord), asm.Mov.Reg(asm.R0, asm.R0).WithSymbol("admission_ready"))
	return a
}

func admissionFlag() asm.Instructions {
	return asm.Instructions{asm.LoadMem(asm.R0, asm.RFP, -320, asm.Word), asm.StoreMem(asm.RFP, -172, asm.R0, asm.Word)}
}
func admissionWrap(a asm.Instructions) asm.Instructions {
	if len(a) < 2 || a[len(a)-2].Symbol() != "done" {
		panic("admission epilogue shape changed")
	}
	out := asm.Instructions{asm.StoreImm(asm.RFP, -304, 0, asm.Word)}
	out = append(out, a[:len(a)-2]...)
	return append(out, asm.LoadMem(asm.R0, asm.RFP, -304, asm.Word).WithSymbol("done"), asm.JEq.Imm(asm.R0, 0, "admission_return"), asm.LoadMem(asm.R0, asm.RFP, -296, asm.DWord), asm.Mov.Imm(asm.R1, -1), asm.StoreXAdd(asm.R0, asm.R1, asm.DWord), asm.Mov.Imm(asm.R0, 0).WithSymbol("admission_return"), asm.Return())
}

func admissionSnapshot(states, control *ebpf.Map, pid uint32) ([]AdmissionRecord, uint64, error) {
	var guard uint64
	if e := control.Lookup(uint32(1), &guard); e != nil {
		return nil, 0, e
	}
	var key admissionKey
	var state admissionState
	rows := []AdmissionRecord{}
	it := states.Iterate()
	for it.Next(&key, &state) {
		if len(rows) >= 1024 || uint32(key.PIDTID>>32) != pid || key.TaskStart == 0 || state.Depth > 64 || state.Reserved != 0 || (state.Syscall != 0 && (state.Syscall > 11 || state.Syscall%2 == 0)) {
			return nil, guard, errors.New("ADMISSION_STATE_INVALID")
		}
		rows = append(rows, AdmissionRecord{uint32(key.PIDTID >> 32), uint32(key.PIDTID), key.TaskStart, state.Syscall, state.Depth})
	}
	if e := it.Err(); e != nil {
		return nil, guard, e
	}
	return rows, guard, nil
}
func admissionIdle(states, control *ebpf.Map, pid uint32) (bool, error) {
	rows, before, e := admissionSnapshot(states, control, pid)
	if e != nil {
		return false, e
	}
	if before != 0 {
		return false, nil
	}
	for _, row := range rows {
		if row.Syscall != 0 || row.Depth != 0 {
			return false, nil
		}
	}
	var after uint64
	if e = control.Lookup(uint32(1), &after); e != nil {
		return false, e
	}
	return after == 0, nil
}
func closeAdmission(program *ebpf.Program) error {
	result, _, e := program.Test(make([]byte, 64))
	if e != nil {
		return e
	}
	if result != 0 {
		return errors.New("ADMISSION_CLOSE_ALREADY_OR_MISSING")
	}
	return nil
}
func admittedAnalysis(r *Report) {
	a := r.Admission
	events := []Event{}
	for _, event := range r.Events {
		switch event.Admission {
		case "":
			events = append(events, event)
			a.AdmittedEvents++
		case "boundary":
			a.BoundaryEvents++
		case "invalid":
			a.InvalidEvents++
		default:
			a.AdmittedIncomplete = true
		}
	}
	pending := map[uint32]Event{}
	for _, event := range events {
		if event.Direction == "metadata" || event.Direction == "function_enter" || event.Direction == "function_exit" {
			continue
		}
		if event.Direction == "enter" {
			if _, ok := pending[event.TID]; ok {
				a.AdmittedIncomplete = true
			}
			pending[event.TID] = event
			continue
		}
		start, ok := pending[event.TID]
		if !ok || start.Call != event.Call || event.Mono < start.Mono {
			a.AdmittedIncomplete = true
			continue
		}
		a.AdmittedPairs = append(a.AdmittedPairs, Pair{start, event, event.Mono - start.Mono})
		delete(pending, event.TID)
	}
	if len(pending) > 0 {
		a.AdmittedIncomplete = true
	}
	a.AdmittedFunctionPairs, a.AdmittedFunctionIssues = pairFunctions(events)
	if len(a.AdmittedFunctionIssues) > 0 || a.Errors > 0 || a.Timeout || a.InFlight > 0 || !a.Quiesced || a.InvalidEvents > 0 || uint64(a.BoundaryEvents) != a.BoundaryCounter || r.PerfLost > 0 || r.OutputFailures > 0 || r.ScopeErrors > 0 || r.ScopeRemaining > 0 {
		a.AdmittedIncomplete = true
	}
	for _, row := range a.Final {
		if row.Syscall != 0 || row.Depth != 0 {
			a.AdmittedIncomplete = true
		}
	}
	a.RawIncomplete = r.Incomplete
	// Admission views are additional evidence. The original raw failure remains.
	if a.AdmittedIncomplete {
		r.Incomplete = true
	}
}
