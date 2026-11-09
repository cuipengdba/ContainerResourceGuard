package guard

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"os"
	"path"
	"path/filepath"
	"strings"
)

func splitCPU(s string) []string    { return strings.Split(strings.TrimSpace(s), ",") }
func read(p string) (string, error) { b, e := os.ReadFile(p); return strings.TrimSpace(string(b)), e }
func membership(s string) (string, error) {
	for _, line := range strings.Split(s, "\n") {
		if strings.HasPrefix(line, "0::") {
			p := strings.TrimPrefix(line, "0::")
			if !strings.HasPrefix(p, "/") {
				break
			}
			for _, v := range strings.Split(p, "/") {
				if v == ".." || v == "." {
					return "", errors.New("ambiguous cgroup membership")
				}
			}
			return path.Clean(p), nil
		}
	}
	return "", errors.New("cgroup v2 membership unavailable (v1 is observe-only)")
}
func unescape(s string) string {
	r := strings.NewReplacer(`\040`, " ", `\011`, "\t", `\012`, "\n", `\134`, "\\")
	return r.Replace(s)
}

// Resolve uses namespace-relative membership AND mount root. It never takes a user target.
func Resolve(cgroup, mountinfo, pid1 string) (string, error) {
	rel, e := membership(cgroup)
	if e != nil {
		return "", e
	}
	first, e := membership(pid1)
	if e != nil || first != rel {
		return "", errors.New("self and container PID 1 differ; refusing a partial or hostPID target")
	}
	var target string
	best := -1
	for _, line := range strings.Split(mountinfo, "\n") {
		sides := strings.SplitN(line, " - ", 2)
		if len(sides) != 2 || !strings.HasPrefix(sides[1], "cgroup2 ") {
			continue
		}
		f := strings.Fields(sides[0])
		if len(f) < 6 {
			continue
		}
		root, mp := unescape(f[3]), unescape(f[4])
		if rel != root && root != "/" && !strings.HasPrefix(rel, root+"/") {
			continue
		}
		sub := strings.TrimPrefix(rel, root)
		candidate := path.Join(mp, strings.TrimPrefix(sub, "/"))
		if len(root) > best {
			target = candidate
			best = len(root)
		}
	}
	if target == "" {
		return "", errors.New("no unambiguous cgroup2 mount for self")
	}
	return target, nil
}

type Environment struct {
	Target               string   `json:"cgroup"`
	Identity             string   `json:"identity"`
	OnlineCPUs           int      `json:"host_online_cpus"`
	MemoryBytes          uint64   `json:"host_memory_bytes"`
	CPUCapacitySource    string   `json:"cpu_capacity_source"`
	MemoryCapacitySource string   `json:"memory_capacity_source"`
	EffectiveCPUs        string   `json:"effective_cpuset,omitempty"`
	CapacityWarnings     []string `json:"capacity_warnings,omitempty"`
}

func Discover() (Environment, error) {
	var env Environment
	cg, e := read("/proc/self/cgroup")
	if e != nil {
		return env, e
	}
	mi, e := read("/proc/self/mountinfo")
	if e != nil {
		return env, e
	}
	p1, e := read("/proc/1/cgroup")
	if e != nil {
		return env, e
	}
	env.Target, e = Resolve(cg, mi, p1)
	if e != nil {
		return env, e
	}
	resolved, e := filepath.EvalSymlinks(env.Target)
	if e != nil || resolved != env.Target {
		return env, errors.New("cgroup target contains symlinks or is unavailable")
	}
	if e = verifyCgroup(env.Target); e != nil {
		return env, e
	}
	// The real host root has no cpu.max. Do not enable controllers or create children.
	for _, f := range []string{"cgroup.procs", "cgroup.type"} {
		if _, e = os.Stat(filepath.Join(env.Target, f)); e != nil {
			return env, fmt.Errorf("self is not a supported container leaf: %s: %w", f, e)
		}
	}
	_, cpuErr := os.Stat(filepath.Join(env.Target, "cpu.max"))
	_, memErr := os.Stat(filepath.Join(env.Target, "memory.max"))
	if cpuErr != nil && memErr != nil {
		return env, errors.New("host root or controllers unavailable; refusing mutation")
	}
	env.Identity, e = groupIdentity(env.Target)
	if e != nil {
		return env, e
	}
	discoverCapacity(&env, read, func(path string) bool { _, err := os.Stat(path); return err == nil }, verifyCapacitySource)
	env.EffectiveCPUs, _ = read(filepath.Join(env.Target, "cpuset.cpus.effective"))
	return env, nil
}

func DeviceIdentity(dev string) (string, error) {
	if !validDevice(dev) {
		return "", errors.New("invalid device number")
	}
	root := filepath.Join("/sys/dev/block", dev)
	if _, e := os.Stat(root); e != nil {
		return "", e
	}
	var id string
	for _, p := range []string{"dm/uuid", "device/wwid", "wwid"} {
		if v, e := read(filepath.Join(root, p)); e == nil && v != "" {
			id = p + ":" + v
			break
		}
	}
	if id == "" {
		return "", errors.New("device has no stable UUID/WWID; refusing a portable IO profile")
	}
	size, e := read(filepath.Join(root, "size"))
	if e != nil {
		return "", e
	}
	// Partition start disambiguates partitions sharing a parent's WWID.
	start, _ := read(filepath.Join(root, "start"))
	hash := sha256.Sum256([]byte(id + ":" + size + ":" + start))
	return hex.EncodeToString(hash[:]), nil
}

func validDevice(s string) bool {
	f := strings.Split(s, ":")
	if len(f) != 2 {
		return false
	}
	for _, v := range f {
		if v == "" {
			return false
		}
		for _, r := range v {
			if r < '0' || r > '9' {
				return false
			}
		}
	}
	return true
}

func validIdentity(s string) bool {
	v, err := hex.DecodeString(s)
	return err == nil && len(v) == 32
}
