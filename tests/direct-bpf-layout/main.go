//go:build linux && amd64

// Read-only layout discovery: loads no BPF program or map and reads no task.
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"strings"

	"github.com/cilium/ebpf/btf"
)

type Field struct {
	Offset uint32 `json:"offset_bytes"`
	Bytes  int    `json:"size_bytes"`
	Kind   string `json:"underlying_kind"`
}
type Result struct {
	Schema      string           `json:"schema"`
	Phase       string           `json:"phase"`
	Reason      string           `json:"reason,omitempty"`
	BTF         string           `json:"kernel_BTF_sha256"`
	BTFBytes    int64            `json:"kernel_BTF_bytes"`
	Fields      map[string]Field `json:"fields"`
	KernelLoads int              `json:"BPF_programs_or_maps_loaded"`
	TaskReads   int              `json:"task_metadata_or_memory_reads"`
}

func members(t btf.Type) []btf.Member {
	switch v := btf.UnderlyingType(t).(type) {
	case *btf.Struct:
		return v.Members
	case *btf.Union:
		return v.Members
	}
	return nil
}
func find(t btf.Type, name string, depth int) (btf.Member, error) {
	if depth > 16 {
		return btf.Member{}, errors.New("BTF_MEMBER_DEPTH")
	}
	var found []btf.Member
	for _, m := range members(t) {
		if m.BitfieldSize != 0 || uint32(m.Offset)%8 != 0 {
			continue
		}
		if m.Name == name {
			found = append(found, m)
		} else if m.Name == "" {
			if n, e := find(m.Type, name, depth+1); e == nil {
				n.Offset += m.Offset
				found = append(found, n)
			}
		}
	}
	if len(found) != 1 {
		return btf.Member{}, errors.New("BTF_MEMBER_NOT_UNIQUE")
	}
	return found[0], nil
}
func run(r *Result) error {
	f, e := os.Open("/sys/kernel/btf/vmlinux")
	if e != nil {
		return errors.New("KERNEL_BTF_READ")
	}
	h := sha256.New()
	n, e := io.Copy(h, io.LimitReader(f, 64<<20+1))
	f.Close()
	if e != nil || n > 64<<20 {
		return errors.New("BTF_READ_BOUND")
	}
	r.BTFBytes = n
	r.BTF = hex.EncodeToString(h.Sum(nil))
	spec, e := btf.LoadKernelSpec()
	if e != nil {
		return errors.New("BTF_PARSE")
	}
	wanted := map[string]int{"task_struct.files": 8, "files_struct.fdt": 8, "fdtable.max_fds": 4, "fdtable.fd": 8, "file.f_inode": 8, "file.private_data": 8, "inode.i_mode": 2, "inode.i_ino": 8, "socket.type": 2, "socket.sk": 8, "sock.__sk_common.skc_family": 2, "sock.__sk_common.skc_state": 1, "sock.__sk_common.skc_rcv_saddr": 4, "sock.__sk_common.skc_daddr": 4, "sock.__sk_common.skc_num": 2, "sock.__sk_common.skc_dport": 2}
	for key, size := range wanted {
		parts := strings.Split(key, ".")
		var root *btf.Struct
		if e := spec.TypeByName(parts[0], &root); e != nil {
			return errors.New("BTF_ROOT:" + parts[0])
		}
		var tp btf.Type = root
		var offset uint32
		for _, part := range parts[1:] {
			m, e := find(tp, part, 0)
			if e != nil {
				return fmt.Errorf("BTF_FIELD:%s", key)
			}
			offset += m.Offset.Bytes()
			tp = m.Type
		}
		actual, e := btf.Sizeof(tp)
		if e != nil || actual != size || offset > 32760 {
			return errors.New("BTF_FIELD_LAYOUT:" + key)
		}
		r.Fields[key] = Field{offset, actual, fmt.Sprintf("%T", btf.UnderlyingType(tp))}
	}
	return nil
}
func main() {
	r := Result{Schema: "crg-readonly-kernel-BTF-metadata-layout-v1", Phase: "unavailable", Fields: map[string]Field{}}
	e := run(&r)
	if e != nil {
		r.Reason = e.Error()
	} else {
		r.Phase = "layout-discovered-not-a-BPF-runtime-qualification"
	}
	json.NewEncoder(os.Stdout).Encode(r)
	if e != nil {
		os.Exit(1)
	}
}
