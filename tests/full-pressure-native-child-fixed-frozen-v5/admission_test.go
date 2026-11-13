//go:build linux && amd64

package main

import (
	"reflect"
	"testing"
)

func TestAdmissionViewNeverErasesWholeRawFailureOrBoundaryRecord(t *testing.T) {
	raw := []Event{{PID: 1, TID: 2, CgroupID: 3, Mono: 9, Call: "write", Direction: "exit", Return: 4096, Admission: "boundary"}}
	report := Report{Events: append([]Event{}, raw...), Incomplete: true, FunctionPairIssues: []string{"original_failure"}, Admission: &AdmissionReport{Quiesced: true, BoundaryCounter: 1}}
	admittedAnalysis(&report)
	if !report.Incomplete || !report.Admission.RawIncomplete || report.Admission.AdmittedIncomplete || !reflect.DeepEqual(report.Events, raw) || !reflect.DeepEqual(report.FunctionPairIssues, []string{"original_failure"}) || report.Admission.BoundaryEvents != 1 {
		t.Fatal(report)
	}
}

func TestAdmissionAnalysisRejectsActualAccountingAndDrainFailures(t *testing.T) {
	cases := []AdmissionReport{{Quiesced: true, Errors: 1}, {Quiesced: true, InFlight: 1}, {Quiesced: true, Timeout: true}, {Quiesced: false}, {Quiesced: true, BoundaryCounter: 1}, {Quiesced: true, Final: []AdmissionRecord{{Syscall: 1}}}, {Quiesced: true, Final: []AdmissionRecord{{Depth: 1}}}}
	for _, value := range cases {
		report := Report{Admission: &value}
		admittedAnalysis(&report)
		if !report.Incomplete || !value.AdmittedIncomplete {
			t.Fatal(value)
		}
	}
	report := Report{Admission: &AdmissionReport{Quiesced: true}, Events: []Event{{Admission: "invalid"}}}
	admittedAnalysis(&report)
	if !report.Incomplete || !report.Admission.AdmittedIncomplete {
		t.Fatal(report)
	}
}

func TestAdmissionNestedFramesUseOriginalStrictPairer(t *testing.T) {
	events := []Event{fe(1, "write", "enter", 1), fe(1, "outer", "function_enter", 2), fe(1, "inner", "function_enter", 3), fe(1, "inner", "function_exit", 4), fe(1, "outer", "function_exit", 5), fe(1, "write", "exit", 6)}
	report := Report{Events: events, Admission: &AdmissionReport{Quiesced: true}}
	admittedAnalysis(&report)
	if report.Incomplete || report.Admission.AdmittedIncomplete || len(report.Admission.AdmittedPairs) != 1 || len(report.Admission.AdmittedFunctionPairs) != 2 {
		t.Fatal(report)
	}
	events[3].Call = "wrong"
	report = Report{Events: events, Admission: &AdmissionReport{Quiesced: true}}
	admittedAnalysis(&report)
	if !report.Incomplete || !report.Admission.AdmittedIncomplete || len(report.Admission.AdmittedFunctionIssues) == 0 {
		t.Fatal(report)
	}
}
