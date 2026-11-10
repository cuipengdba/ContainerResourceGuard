package guard

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

// SupervisorOptions deliberately has no container/PID/cgroup target. These are
// explicit, per-container maintenance paths, never business-startup options.
type SupervisorOptions struct {
	Path, SourceSHA256, Helper, HelperSHA256, Binary, BinarySHA256, Config string
	BackupDir                                                              string
}

type SupervisorPlan struct {
	Schema         string `json:"schema"`
	SourceSHA256   string `json:"source_sha256"`
	ProposedSHA256 string `json:"proposed_sha256"`
	HelperSHA256   string `json:"helper_sha256"`
	BinarySHA256   string `json:"binary_sha256"`
	ConfigSHA256   string `json:"config_sha256"`
	State          string `json:"state"`
	Activation     string `json:"activation"`
}

// PRIVATE receipt: it includes installation paths and must not be published.
// It authorizes only a byte-exact supervisor restoration, never resource writes.
type supervisorReceipt struct {
	Schema         string `json:"schema"`
	Path           string `json:"path"`
	SourceSHA256   string `json:"source_sha256"`
	ProposedSHA256 string `json:"proposed_sha256"`
	SourceMode     uint32 `json:"source_mode"`
	State          string `json:"state"`
}

func maintenanceFile(path string) ([]byte, os.FileMode, error) {
	if !filepath.IsAbs(path) || filepath.Clean(path) != path {
		return nil, 0, errors.New("maintenance file must use a clean absolute path")
	}
	if err := realInstallDirectory(filepath.Dir(path)); err != nil {
		return nil, 0, err
	}
	b, err := ReadStateBoundedFile(path) // NOFOLLOW, NONBLOCK, regular, bounded
	if err != nil {
		return nil, 0, err
	}
	st, err := os.Lstat(path)
	if err != nil {
		return nil, 0, err
	}
	if !st.Mode().IsRegular() || st.Mode().Perm()&0022 != 0 || st.Mode()&os.ModeType != 0 || st.Mode()&(os.ModeSetuid|os.ModeSetgid|os.ModeSticky) != 0 {
		return nil, 0, errors.New("maintenance file must be protected, regular and without special permission bits")
	}
	return b, st.Mode().Perm(), nil
}

func checkedShell(ctx context.Context, body []byte) error {
	ctx, cancel := context.WithTimeout(ctx, 3*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, "/bin/bash", "--noprofile", "--norc", "-n")
	cmd.Env = []string{"PATH=/usr/bin:/bin", "LANG=C"}
	cmd.Stdin = bytes.NewReader(body)
	// Syntax checking never executes the script. Suppress source-containing
	// diagnostics: raw vendor code does not belong in public CLI JSON.
	if err := cmd.Run(); err != nil {
		return errors.New("bash syntax validation failed or timed out")
	}
	return nil
}

func shellLiteral(s string) string { return "'" + strings.ReplaceAll(s, "'", "'\"'\"'") + "'" }

func proposedSupervisor(raw []byte, o SupervisorOptions) ([]byte, error) {
	if !bytes.HasPrefix(raw, []byte("#!/usr/bin/env bash\n")) && !bytes.HasPrefix(raw, []byte("#!/bin/bash\n")) {
		return nil, errors.New("verified Bash supervisor required")
	}
	text := string(raw)
	if strings.ContainsAny(text, "\r\x00") || strings.Contains(text, "CRG OPTIONAL") {
		return nil, errors.New("unsupported or already integrated supervisor")
	}
	anchors := []string{"business_pid=\nguard_pid=\nstopping=0\n", "\"$BUSINESS_START\" &\nbusiness_pid=$!\nstart_guard\n"}
	stop := "  [[ -z \"$guard_pid\" ]] || kill -TERM \"$guard_pid\" 2>/dev/null || "
	stopLine := ""
	for _, ending := range []string{":\n", "true\n"} {
		if strings.Count(text, stop+ending) == 1 {
			if stopLine != "" {
				return nil, errors.New("ambiguous shutdown anchor")
			}
			stopLine = stop + ending
		}
	}
	if stopLine == "" {
		return nil, errors.New("unsupported supervisor shutdown; no changes made")
	}
	for _, anchor := range anchors {
		if strings.Count(text, anchor) != 1 {
			return nil, errors.New("unsupported supervisor layout; no changes made")
		}
	}
	start := "# CRG OPTIONAL BEGIN\nCRG_BIN=" + shellLiteral(o.Binary) + "\nCRG_CONFIG=" + shellLiteral(o.Config) + "\nif [[ -r " + shellLiteral(o.Helper) + " ]]; then\n  source " + shellLiteral(o.Helper) + " || :\n  if declare -F crg_start_optional >/dev/null; then crg_start_optional || :; fi\nfi\n# CRG OPTIONAL END\n"
	finish := "  # CRG OPTIONAL STOP BEGIN\n  if declare -F crg_stop_optional >/dev/null; then crg_stop_optional || :; fi\n  # CRG OPTIONAL STOP END\n"
	text = strings.Replace(text, anchors[0], "business_pid=\nguard_pid=\nCRG_HELPER_PID=\nstopping=0\n", 1)
	text = strings.Replace(text, stopLine, stopLine+finish, 1)
	text = strings.Replace(text, anchors[1], anchors[1]+start, 1)
	if len(text) > MaxJSONBytes {
		return nil, errors.New("integrated supervisor exceeds 1MiB")
	}
	return []byte(text), nil
}

func planSupervisor(ctx context.Context, c Config, o SupervisorOptions) (SupervisorPlan, []byte, []byte, os.FileMode, error) {
	var p SupervisorPlan
	for _, sha := range []string{o.SourceSHA256, o.HelperSHA256, o.BinarySHA256} {
		if !validSHA(sha) {
			return p, nil, nil, 0, errors.New("explicit trusted source/helper/binary lowercase SHA256 required")
		}
	}
	paths := []string{o.Path, o.Helper, o.Binary, o.Config}
	seen := map[string]bool{}
	for _, path := range paths {
		if seen[path] || pathWithin(c.StateDir, path) || (c.IOProfile != "" && resolveDiagnosticGuardPath(c.IOProfile) == path) {
			return p, nil, nil, 0, errors.New("maintenance paths must be distinct and outside state/profile")
		}
		seen[path] = true
	}
	raw, mode, err := maintenanceFile(o.Path)
	if err != nil {
		return p, nil, nil, 0, err
	}
	if mode&0111 == 0 || digest(raw) != o.SourceSHA256 {
		return p, nil, nil, 0, errors.New("supervisor executable mode or trusted source SHA256 mismatch")
	}
	if err = verifySupervisorMetadata(o.Path); err != nil {
		return p, nil, nil, 0, err
	}
	helper, _, err := maintenanceFile(o.Helper)
	if err != nil {
		return p, nil, nil, 0, err
	}
	if digest(helper) != o.HelperSHA256 {
		return p, nil, nil, 0, errors.New("helper SHA256 mismatch")
	}
	if err = checkedShell(ctx, helper); err != nil {
		return p, nil, nil, 0, err
	}
	// Executable images have a larger dedicated bound and are never run here.
	if err = realInstallDirectory(filepath.Dir(o.Binary)); err != nil {
		return p, nil, nil, 0, err
	}
	if !filepath.IsAbs(o.Binary) || filepath.Clean(o.Binary) != o.Binary {
		return p, nil, nil, 0, errors.New("binary path must be clean and absolute")
	}
	binary, err := openBinary(o.Binary)
	if err != nil {
		return p, nil, nil, 0, err
	}
	binarySHA, hashErr := binaryDigest(binary)
	st, statErr := binary.Stat()
	binary.Close()
	if hashErr != nil || statErr != nil || binarySHA != o.BinarySHA256 || st.Mode().Perm()&0111 == 0 || st.Mode().Perm()&0022 != 0 {
		return p, nil, nil, 0, errors.New("binary mode or trusted SHA256 mismatch")
	}
	config, _, err := maintenanceFile(o.Config)
	if err != nil {
		return p, nil, nil, 0, err
	}
	var actual Config
	if err = Decode(config, &actual); err != nil {
		return p, nil, nil, 0, err
	}
	if err = actual.Validate(); err != nil {
		return p, nil, nil, 0, err
	}
	want, _ := json.Marshal(c)
	got, _ := json.Marshal(actual)
	if !bytes.Equal(want, got) {
		return p, nil, nil, 0, errors.New("effective configuration differs from the persistent configuration file")
	}
	proposed, err := proposedSupervisor(raw, o)
	if err != nil {
		return p, nil, nil, 0, err
	}
	if err = checkedShell(ctx, raw); err != nil {
		return p, nil, nil, 0, err
	}
	if err = checkedShell(ctx, proposed); err != nil {
		return p, nil, nil, 0, err
	}
	p = SupervisorPlan{"crg-supervisor-plan-v1", digest(raw), digest(proposed), digest(helper), binarySHA, digest(config), "preview", "next planned restart; no process started or stopped"}
	return p, raw, proposed, mode, nil
}

func PreviewSupervisor(ctx context.Context, c Config, o SupervisorOptions) (SupervisorPlan, error) {
	p, _, _, _, err := planSupervisor(ctx, c, o)
	return p, err
}

// InstallSupervisor performs only the reviewed script replacement. A resident
// resource Agent holds the same cgroup inode lock and causes refusal. Backups
// are private, durable and never overwritten. No journal/config/helper changes.
func InstallSupervisor(ctx context.Context, c Config, env Environment, o SupervisorOptions) (SupervisorPlan, error) {
	var p SupervisorPlan
	lock, err := lockGroup(env.Target)
	if err != nil {
		return p, fmt.Errorf("%w: quiesce the resource Agent before maintenance: %v", ErrLocked, err)
	}
	defer lock.Close()
	if err = VerifyIdentity(env); err != nil {
		return p, err
	}
	p, raw, proposed, mode, err := planSupervisor(ctx, c, o)
	if err != nil {
		return p, err
	}
	if err = realInstallDirectory(filepath.Dir(o.BackupDir)); err != nil {
		return p, err
	}
	if !filepath.IsAbs(o.BackupDir) || filepath.Clean(o.BackupDir) != o.BackupDir {
		return p, errors.New("fresh absolute backup directory required")
	}
	for _, path := range []string{c.StateDir, o.Path, o.Helper, o.Binary, o.Config, c.IOProfile} {
		if path != "" && (pathWithin(o.BackupDir, path) || pathWithin(path, o.BackupDir)) {
			return p, errors.New("backup directory overlaps protected input/state paths")
		}
	}
	if err = os.Mkdir(o.BackupDir, 0700); err != nil {
		return p, err
	}
	if err = syncDirectory(filepath.Dir(o.BackupDir)); err != nil {
		return p, err
	}
	if err = writePrivateBackup(filepath.Join(o.BackupDir, "supervisor.original"), c.StateDir, raw); err != nil {
		return p, err
	}
	if err = writePrivateBackup(filepath.Join(o.BackupDir, "supervisor.proposed.sh"), c.StateDir, proposed); err != nil {
		return p, err
	}
	for _, input := range []struct{ path, name, sha string }{{o.Config, "config.json", p.ConfigSHA256}, {o.Helper, "optional-agent.sh", p.HelperSHA256}} {
		body, _, err := maintenanceFile(input.path)
		if err != nil {
			return p, err
		}
		if digest(body) != input.sha {
			return p, errors.New("input changed during private backup")
		}
		if err = writePrivateBackup(filepath.Join(o.BackupDir, input.name), c.StateDir, body); err != nil {
			return p, err
		}
	}
	if err = AtomicJSON(filepath.Join(o.BackupDir, "plan.json"), p); err != nil {
		return p, err
	}
	r := supervisorReceipt{"crg-supervisor-receipt-v1", o.Path, p.SourceSHA256, p.ProposedSHA256, uint32(mode), "prepared"}
	if err = AtomicJSON(filepath.Join(o.BackupDir, "receipt.json"), r); err != nil {
		return p, err
	}
	fresh, _, _, _, err := planSupervisor(ctx, c, o)
	if err != nil {
		return p, err
	}
	if fresh != p {
		return p, errors.New("maintenance inputs changed before commit")
	}
	if err = VerifyIdentity(env); err != nil {
		return p, err
	}
	if err = replaceSupervisor(o.Path, proposed, mode, p.SourceSHA256); err != nil {
		return p, err
	}
	r.State = "installed"
	if err = AtomicJSON(filepath.Join(o.BackupDir, "receipt.json"), r); err != nil {
		return p, fmt.Errorf("supervisor replaced but receipt update failed; inspect file SHA256: %w", err)
	}
	p.State = "installed"
	return p, nil
}

func replaceSupervisor(path string, body []byte, mode os.FileMode, expected string) error {
	f, err := os.CreateTemp(filepath.Dir(path), ".crg-supervisor-")
	if err != nil {
		return err
	}
	stage := f.Name()
	defer os.Remove(stage)
	err = f.Chmod(mode)
	if err == nil {
		_, err = f.Write(body)
	}
	if err == nil {
		err = f.Sync()
	}
	closeErr := f.Close()
	if err == nil {
		err = closeErr
	}
	if err != nil {
		return err
	}
	current, currentMode, err := maintenanceFile(path)
	if err != nil {
		return err
	}
	if digest(current) != expected || currentMode != mode {
		return errors.New("supervisor changed before atomic replacement")
	}
	if err = verifySupervisorMetadata(path); err != nil {
		return err
	}
	if err = os.Rename(stage, path); err != nil {
		return err
	}
	if err = syncDirectory(filepath.Dir(path)); err != nil {
		return fmt.Errorf("supervisor renamed but directory sync failed; inspect actual SHA256: %w", err)
	}
	return nil
}

func UninstallSupervisor(ctx context.Context, c Config, env Environment, path, backupDir string) (SupervisorPlan, error) {
	var p SupervisorPlan
	lock, err := lockGroup(env.Target)
	if err != nil {
		return p, fmt.Errorf("%w: stop the resource writer before uninstall: %v", ErrLocked, err)
	}
	defer lock.Close()
	if err = VerifyIdentity(env); err != nil {
		return p, err
	}
	if err = realInstallDirectory(backupDir); err != nil {
		return p, err
	}
	b, _, err := maintenanceFile(filepath.Join(backupDir, "receipt.json"))
	if err != nil {
		return p, err
	}
	var r supervisorReceipt
	if err = Decode(b, &r); err != nil {
		return p, err
	}
	if r.Schema != "crg-supervisor-receipt-v1" || r.Path != path || !validSHA(r.SourceSHA256) || !validSHA(r.ProposedSHA256) || (r.State != "prepared" && r.State != "installed") || r.SourceMode > 0777 || r.SourceMode&0111 == 0 || r.SourceMode&0022 != 0 {
		return p, errors.New("incompatible supervisor uninstall receipt")
	}
	// Retained ownership/pending intent must be resolved by disable/restore,
	// never by erasing the startup hook or deleting the journal.
	snapshot, err := inspectUpgrade(c, env)
	if err != nil {
		return p, err
	}
	if !snapshot.Check.DisabledForCurrent {
		return p, errors.New("uninstall requires explicit disable for the current identity; the optional helper must remain unable to restart a writer")
	}
	if len(snapshot.Journal) > 0 && (!snapshot.Check.JournalIdentityMatches || snapshot.Check.MutationCount > 0) {
		return p, errors.New("unresolved resource journal; explicitly disable/restore and inspect remaining controls before uninstall")
	}
	original, _, err := maintenanceFile(filepath.Join(backupDir, "supervisor.original"))
	if err != nil {
		return p, err
	}
	if digest(original) != r.SourceSHA256 {
		return p, errors.New("original supervisor backup SHA256 mismatch")
	}
	if err = checkedShell(ctx, original); err != nil {
		return p, err
	}
	if err = VerifyIdentity(env); err != nil {
		return p, err
	}
	if err = replaceSupervisor(path, original, os.FileMode(r.SourceMode), r.ProposedSHA256); err != nil {
		return p, err
	}
	r.State = "uninstalled"
	if err = AtomicJSON(filepath.Join(backupDir, "receipt.json"), r); err != nil {
		return p, fmt.Errorf("supervisor restored but receipt update failed; inspect source SHA256: %w", err)
	}
	p = SupervisorPlan{Schema: "crg-supervisor-plan-v1", SourceSHA256: r.ProposedSHA256, ProposedSHA256: r.SourceSHA256, State: "uninstalled", Activation: "next planned restart; no process stopped; keep backups/state for audit"}
	return p, nil
}
