package guard

import (
	"fmt"
	"os"
	"strconv"
	"strings"
)

// CgroupCheck describes the current process, never another container or a
// host-wide mode inferred from a directory that may belong to another mount.
type CgroupCheck struct {
	Version string `json:"cgroup_version"`
	Allowed bool   `json:"resource_control_allowed"`
	Action  string `json:"resource_action"`
	Reason  string `json:"reason"`
}

func InspectCgroupVersion(membershipText, mountinfo string) CgroupCheck {
	result := CgroupCheck{Version: "unknown", Action: "skip", Reason: "cgroup version could not be confirmed; no resource settings will be written"}
	var v1, v2, mountV1, mountV2 bool
	for _, line := range strings.Split(strings.TrimSpace(membershipText), "\n") {
		parts := strings.SplitN(line, ":", 3)
		if len(parts) != 3 || !strings.HasPrefix(parts[2], "/") {
			return result
		}
		id, err := strconv.ParseUint(parts[0], 10, 32)
		if err != nil {
			return result
		}
		switch {
		case id == 0 && parts[1] == "":
			v2 = true
		case id > 0 && parts[1] != "":
			v1 = true
		default:
			return result
		}
	}
	for _, line := range strings.Split(mountinfo, "\n") {
		sides := strings.SplitN(line, " - ", 2)
		if len(sides) != 2 || len(strings.Fields(sides[0])) < 6 {
			continue
		}
		fields := strings.Fields(sides[1])
		if len(fields) < 3 {
			continue
		}
		mountV1 = mountV1 || fields[0] == "cgroup"
		mountV2 = mountV2 || fields[0] == "cgroup2"
	}
	switch {
	case v1 && v2:
		result.Version, result.Reason = "hybrid", "mixed cgroup v1/v2 membership; CPU, memory and IO settings skipped"
	case v1 && mountV1:
		result.Version, result.Reason = "v1", "cgroup v1 detected; CPU, memory and IO settings skipped; business startup continues"
	case v2 && mountV2:
		result = CgroupCheck{Version: "v2", Allowed: true, Action: "verify_self_then_apply", Reason: "cgroup v2 detected; self identity, permissions and resource safety checks still required"}
	}
	return result
}

func DetectCgroupVersion() (CgroupCheck, error) {
	cg, err := os.ReadFile("/proc/self/cgroup")
	if err != nil {
		return CgroupCheck{Version: "unknown", Action: "skip"}, fmt.Errorf("read cgroup membership: %w", err)
	}
	mi, err := os.ReadFile("/proc/self/mountinfo")
	if err != nil {
		return CgroupCheck{Version: "unknown", Action: "skip"}, fmt.Errorf("read cgroup mounts: %w", err)
	}
	return InspectCgroupVersion(string(cg), string(mi)), nil
}

type UnsupportedCgroupError struct{ Check CgroupCheck }

func (e *UnsupportedCgroupError) Error() string { return e.Check.Reason }
