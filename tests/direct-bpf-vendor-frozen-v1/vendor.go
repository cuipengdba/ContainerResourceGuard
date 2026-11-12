//go:build linux && amd64

package main

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"

	"golang.org/x/sys/unix"
)

// This mode is restricted to the two freshly created, fixed-path fixtures of
// this particular diagnostic. It is deliberately not a general PID selector.
type VendorScope struct {
	Namespace    string `json:"namespace"`
	NamespaceUID string `json:"namespace_uid"`
	Pod          string `json:"pod"`
	PodUID       string `json:"pod_uid"`
	ContainerID  string `json:"container_id"`
	Role         string `json:"role"`
	Root         string `json:"fixture_root"`
	InitPID      int    `json:"container_init_pid"`
	InitStart    uint64 `json:"container_init_start_ticks"`
}

const vendorSHA = "bd21a02c74b4e416439d72f1cc5039280bea6399f67e2923dff6a743c189fdcb"

var uuidRE = regexp.MustCompile(`^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`)
var cidRE = regexp.MustCompile(`^[0-9a-f]{64}$`)

type boundedBuffer struct {
	bytes.Buffer
	max int
}

func (b *boundedBuffer) Write(p []byte) (int, error) {
	if len(p) > b.max-b.Len() {
		return 0, errors.New("KUBE_OUTPUT_BOUND")
	}
	return b.Buffer.Write(p)
}
func kube(kind, name, namespace, template string) (string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 8*time.Second)
	defer cancel()
	args := []string{"--request-timeout=5s", "get", kind, name}
	if namespace != "" {
		args = append(args, "-n", namespace)
	}
	args = append(args, "-o", "jsonpath="+template)
	cmd := exec.CommandContext(ctx, "/usr/bin/kubectl", args...)
	var out boundedBuffer
	out.max = 8192
	var stderr boundedBuffer
	stderr.max = 8192
	cmd.Stdout = &out
	cmd.Stderr = &stderr
	if e := cmd.Run(); e != nil {
		return "", errors.New("VENDOR_KUBE_METADATA")
	}
	if stderr.Len() != 0 {
		return "", errors.New("VENDOR_KUBE_STDERR")
	}
	return out.String(), nil
}
func statSame(a, b string) bool {
	var x, y unix.Stat_t
	return unix.Stat(a, &x) == nil && unix.Stat(b, &y) == nil && x.Dev == y.Dev && x.Ino == y.Ino
}
func vendorShape(p Plan) bool {
	v := p.Vendor
	if v == nil || v.Namespace != "crg-vendor-lab-bpf676-20261112" || !uuidRE.MatchString(v.NamespaceUID) || !uuidRE.MatchString(v.PodUID) || !cidRE.MatchString(v.ContainerID) || v.InitPID <= 1 || v.InitStart == 0 || p.ReaderDelay != 0 || p.Probe != "" || p.ProbeSHA != "" || p.ExeSHA != vendorSHA {
		return false
	}
	if (v.Role != "dbs" && v.Role != "hisdbs") || v.Pod != v.Role+"-business" {
		return false
	}
	want := "/var/tmp/crg-bpf676-diagnostic-20261112/v10-" + v.Role + "-bw64/" + v.Role + "-business"
	if v.Root != want || filepath.Clean(v.Root) != want {
		return false
	}
	leaf := "cri-containerd-" + v.ContainerID + ".scope"
	podSlice := "-pod" + strings.ReplaceAll(v.PodUID, "-", "_") + ".slice/"
	return filepath.Base(p.Cgroup) == leaf && strings.Contains(p.Cgroup, podSlice)
}
func sameVendorFast(p Plan) bool {
	if !vendorShape(p) {
		return false
	}
	v := p.Vendor
	init, e := identity(v.InitPID)
	if e != nil || init.Start != v.InitStart || init.Cgroup != p.Cgroup || init.State == "Z" || init.State == "X" {
		return false
	}
	owner, e := identity(p.OwnerPID)
	if e != nil || owner.Start != p.OwnerStart || p.OwnerPID != os.Getppid() {
		return false
	}
	procRoot := fmt.Sprintf("/proc/%d/root", p.PID)
	initRoot := fmt.Sprintf("/proc/%d/root", v.InitPID)
	for _, a := range [][2]string{{"dbs", "/opt/dbs"}, {"postgresql", "/opt/postgresql"}, {"crg-config", "/etc/crg"}} {
		if !statSame(filepath.Join(v.Root, a[0]), procRoot+a[1]) || !statSame(filepath.Join(v.Root, a[0]), initRoot+a[1]) {
			return false
		}
	}
	for _, name := range []string{"net", "mnt", "pid"} {
		a, e := os.Readlink(fmt.Sprintf("/proc/%d/ns/%s", p.PID, name))
		if e != nil {
			return false
		}
		b, e := os.Readlink(fmt.Sprintf("/proc/%d/ns/%s", v.InitPID, name))
		if e != nil || a != b {
			return false
		}
	}
	exe, e := os.Readlink(fmt.Sprintf("/proc/%d/exe", p.PID))
	if e != nil || exe != "/opt/dbs/bin/"+v.Role {
		return false
	}
	return statSame(fmt.Sprintf("/proc/%d/exe", p.PID), filepath.Join(v.Root, "dbs/bin", v.Role))
}
func validateVendor(p Plan) error {
	if !vendorShape(p) {
		return errors.New("VENDOR_FIXED_SCOPE")
	}
	v := p.Vendor
	raw, e := kube("namespace", v.Namespace, "", "{.metadata.uid}|{.metadata.labels.managed-by}")
	if e != nil {
		return e
	}
	if raw != v.NamespaceUID+"|crg-vendor-test" {
		return errors.New("VENDOR_NAMESPACE_IDENTITY")
	}
	template := fmt.Sprintf("{.metadata.uid}|{.metadata.namespace}|{.metadata.name}|{.metadata.labels.managed-by}|{.status.containerStatuses[?(@.name==%q)].containerID}", v.Role)
	raw, e = kube("pod", v.Pod, v.Namespace, template)
	if e != nil {
		return e
	}
	if raw != v.PodUID+"|"+v.Namespace+"|"+v.Pod+"|crg-vendor-test|containerd://"+v.ContainerID {
		return errors.New("VENDOR_POD_IDENTITY")
	}
	status, e := bounded(fmt.Sprintf("/proc/%d/status", v.InitPID), 8192)
	if e != nil {
		return errors.New("VENDOR_INIT_STATUS")
	}
	isInit := false
	for _, line := range strings.Split(string(status), "\n") {
		if strings.HasPrefix(line, "NSpid:") {
			fields := strings.Fields(line)
			isInit = len(fields) > 2 && fields[len(fields)-1] == "1"
		}
	}
	if !isInit || !sameVendorFast(p) {
		return errors.New("VENDOR_PROCESS_MOUNT_OR_NAMESPACE")
	}
	members, e := bounded(filepath.Join("/sys/fs/cgroup", p.Cgroup, "cgroup.procs"), 65536)
	if e != nil {
		return errors.New("VENDOR_LEAF_MEMBERS")
	}
	found := false
	lines := strings.Fields(string(members))
	if len(lines) > 4096 {
		return errors.New("VENDOR_PROCESS_BOUND")
	}
	for _, s := range lines {
		pid, e := strconv.Atoi(s)
		if e != nil {
			return errors.New("VENDOR_PID_FORMAT")
		}
		if pid == p.PID {
			found = true
		}
	}
	if !found {
		return errors.New("VENDOR_TARGET_NOT_MEMBER")
	}
	return nil
}
