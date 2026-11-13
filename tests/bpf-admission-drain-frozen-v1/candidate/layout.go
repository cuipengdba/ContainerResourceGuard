//go:build linux && amd64

package main

import (
	"bytes"
	"errors"
	"fmt"
	"strings"

	"github.com/cilium/ebpf/btf"
)

type KernelField struct {
	Offset int16  `json:"offset_bytes"`
	Bytes  int    `json:"size_bytes"`
	Type   string `json:"validated_type"`
}
type KernelLayout struct {
	Schema string                 `json:"schema"`
	SHA    string                 `json:"kernel_BTF_sha256"`
	Bytes  int                    `json:"kernel_BTF_bytes"`
	Fields map[string]KernelField `json:"fields"`
}

func btfMembers(t btf.Type) []btf.Member {
	switch v := btf.UnderlyingType(t).(type) {
	case *btf.Struct:
		return v.Members
	case *btf.Union:
		return v.Members
	}
	return nil
}
func btfFind(t btf.Type, name string, depth int) (btf.Member, error) {
	if depth > 16 {
		return btf.Member{}, errors.New("BTF_MEMBER_DEPTH")
	}
	var found []btf.Member
	for _, m := range btfMembers(t) {
		if m.BitfieldSize != 0 || uint32(m.Offset)%8 != 0 {
			continue
		}
		if m.Name == name {
			found = append(found, m)
		} else if m.Name == "" {
			if n, e := btfFind(m.Type, name, depth+1); e == nil {
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
func pointerTo(t btf.Type, name string, levels int) bool {
	for i := 0; i < levels; i++ {
		p, ok := btf.UnderlyingType(t).(*btf.Pointer)
		if !ok {
			return false
		}
		t = p.Target
	}
	if name == "void" {
		_, ok := btf.UnderlyingType(t).(*btf.Void)
		return ok
	}
	v, ok := btf.UnderlyingType(t).(*btf.Struct)
	return ok && v.Name == name
}
func loadKernelLayout() (KernelLayout, error) {
	l := KernelLayout{Schema: "crg-kernel-file-admission-BTF-type-graph-v3", Fields: map[string]KernelField{}}
	raw, e := bounded("/sys/kernel/btf/vmlinux", 64<<20)
	if e != nil {
		return l, errors.New("KERNEL_BTF_READ")
	}
	l.SHA = digest(raw)
	l.Bytes = len(raw)
	spec, e := btf.LoadSpecFromReader(bytes.NewReader(raw))
	if e != nil {
		return l, errors.New("BTF_PARSE")
	}
	sizes := map[string]int{"task_struct.start_boottime": 8, "task_struct.files": 8, "files_struct.fdt": 8, "fdtable.max_fds": 4, "fdtable.fd": 8, "file.f_inode": 8, "file.f_flags": 4, "inode.i_sb": 8, "super_block.s_dev": 4, "file.private_data": 8, "inode.i_mode": 2, "inode.i_ino": 8, "socket.type": 2, "socket.sk": 8, "sock.__sk_common.skc_family": 2, "sock.__sk_common.skc_state": 1, "sock.__sk_common.skc_rcv_saddr": 4, "sock.__sk_common.skc_daddr": 4, "sock.__sk_common.skc_num": 2, "sock.__sk_common.skc_dport": 2}
	pointers := map[string]struct {
		name   string
		levels int
	}{"task_struct.files": {"files_struct", 1}, "files_struct.fdt": {"fdtable", 1}, "fdtable.fd": {"file", 2}, "file.f_inode": {"inode", 1}, "inode.i_sb": {"super_block", 1}, "file.private_data": {"void", 1}, "socket.sk": {"sock", 1}}
	for key, size := range sizes {
		parts := strings.Split(key, ".")
		var root *btf.Struct
		if e := spec.TypeByName(parts[0], &root); e != nil {
			return l, errors.New("BTF_ROOT:" + parts[0])
		}
		var tp btf.Type = root
		var offset uint32
		for _, part := range parts[1:] {
			m, e := btfFind(tp, part, 0)
			if e != nil {
				return l, errors.New("BTF_FIELD:" + key)
			}
			offset += m.Offset.Bytes()
			tp = m.Type
		}
		actual, e := btf.Sizeof(tp)
		if e != nil || actual != size || offset > 32760 || offset+uint32(size) > root.Size {
			return l, errors.New("BTF_LAYOUT:" + key)
		}
		kind := "integer"
		if want, ok := pointers[key]; ok {
			if !pointerTo(tp, want.name, want.levels) {
				return l, errors.New("BTF_POINTER_GRAPH:" + key)
			}
			kind = fmt.Sprintf("pointer%d-to-%s", want.levels, want.name)
		} else if _, ok := btf.UnderlyingType(tp).(*btf.Int); !ok {
			return l, errors.New("BTF_INTEGER:" + key)
		}
		l.Fields[key] = KernelField{int16(offset), size, kind}
	}
	return l, nil
}
