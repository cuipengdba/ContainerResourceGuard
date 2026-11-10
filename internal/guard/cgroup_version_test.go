package guard

import "testing"

func TestCgroupVersionGate(t *testing.T) {
	const unified = "24 23 0:22 / /sys/fs/cgroup rw - cgroup2 cgroup rw"
	const legacy = "25 23 0:23 / /sys/fs/cgroup/cpu rw - cgroup cgroup rw,cpu"
	for _, row := range []struct {
		name, cg, mounts, version string
		allowed                   bool
	}{
		{"unified", "0::/container-NEW-ID", unified, "v2", true},
		{"legacy", "3:cpu,cpuacct:/container-NEW-ID\n2:memory:/container-NEW-ID", legacy, "v1", false},
		{"hybrid", "0::/container\n3:cpu:/container", unified + "\n" + legacy, "hybrid", false},
		{"missing unified mount", "0::/container", legacy, "unknown", false},
		{"missing legacy mount", "3:cpu:/container", unified, "unknown", false},
		{"damaged membership", "0::/container\ninvalid", unified, "unknown", false},
		{"empty", "", unified, "unknown", false},
		{"not mount filesystem", "0::/container", "24 23 0:22 / /cgroup2 rw - tmpfs tmpfs rw", "unknown", false},
	} {
		t.Run(row.name, func(t *testing.T) {
			got := InspectCgroupVersion(row.cg, row.mounts)
			if got.Version != row.version || got.Allowed != row.allowed || got.Reason == "" || !got.Allowed && got.Action != "skip" {
				t.Fatal(got)
			}
		})
	}
}
