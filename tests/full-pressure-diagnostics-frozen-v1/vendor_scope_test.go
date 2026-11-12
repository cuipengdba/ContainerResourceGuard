//go:build linux && amd64

package main

import (
	"strings"
	"testing"
)

func TestFullVendorScopeIsOnlyTheFreshFixedFixture(t *testing.T) {
	base := Plan{ExeSHA: vendorSHA, Duration: 1200, Vendor: &VendorScope{Namespace: "crg-vendor-lab-high817-20261112", NamespaceUID: "11111111-1111-4111-8111-111111111111", PodUID: "22222222-2222-4222-8222-222222222222", ContainerID: strings.Repeat("a", 64), Role: "dbs", Pod: "dbs-business", InitPID: 1234, InitStart: 12345, Root: "/var/tmp/crg-high817-pressure-20261112/v10-dbs-bw64/dbs-business"}}
	base.Cgroup = "/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-pod22222222_2222_4222_8222_222222222222.slice/cri-containerd-" + base.Vendor.ContainerID + ".scope"
	if !vendorShape(base) {
		t.Fatal("fixed scope rejected")
	}
	for _, name := range []string{"namespace", "namespaceUID", "podUID", "CID", "PID1", "role", "pod", "root", "root-dotdot", "leaf", "delay", "exe", "probe"} {
		t.Run(name, func(t *testing.T) {
			p := base
			v := *base.Vendor
			p.Vendor = &v
			switch name {
			case "namespace":
				v.Namespace = "another-business-namespace"
			case "namespaceUID":
				v.NamespaceUID = "unknown"
			case "podUID":
				v.PodUID = "unknown"
			case "CID":
				v.ContainerID = "unknown"
			case "PID1":
				v.InitPID = 1
			case "role":
				v.Role = "another"
			case "pod":
				v.Pod = "other-business"
			case "root":
				v.Root = "/opt/production"
			case "root-dotdot":
				v.Root = "/var/tmp/crg-high817-pressure-20261112/../production"
			case "leaf":
				p.Cgroup = "/other.scope"
			case "delay":
				p.ReaderDelay = 1
			case "exe":
				p.ExeSHA = strings.Repeat("b", 64)
			case "probe":
				p.Probe = "/tmp/probe.py"
			}
			if vendorShape(p) {
				t.Fatal("out-of-scope target accepted")
			}
		})
	}
}
