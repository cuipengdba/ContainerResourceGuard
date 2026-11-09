package guard

import (
	"context"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

const maxBinaryBytes = 64 << 20

// BinaryReceipt is PRIVATE recovery metadata. It never authorizes an import of
// a journal or a change to a kernel limit. Both replacement directions require
// the same quiescent identity and unchanged configuration/state snapshot.
type BinaryReceipt struct {
	Schema          string `json:"schema"`
	Identity        string `json:"identity"`
	InstallDir      string `json:"install_dir"`
	PreviousSHA256  string `json:"previous_sha256"`
	CandidateSHA256 string `json:"candidate_sha256"`
	SnapshotSHA256  string `json:"snapshot_sha256"`
	State           string `json:"state"`
}

func validSHA(s string) bool {
	b, err := hex.DecodeString(s)
	return err == nil && len(b) == 32 && s == strings.ToLower(s)
}

func realInstallDirectory(path string) error {
	if !filepath.IsAbs(path) || filepath.Clean(path) != path {
		return errors.New("installation directory must be a clean absolute path")
	}
	p, err := filepath.EvalSymlinks(path)
	if err != nil {
		return err
	}
	st, err := os.Lstat(path)
	if err != nil {
		return err
	}
	if p != path || !st.IsDir() || st.Mode().Perm()&0022 != 0 {
		return errors.New("installation directory must be real and not group/world writable")
	}
	return nil
}

func pathWithin(parent, child string) bool {
	r, err := filepath.Rel(parent, child)
	return err == nil && r != ".." && !strings.HasPrefix(r, ".."+string(filepath.Separator))
}

func binarySnapshot(c Config, s upgradeSnapshot) string {
	b, _ := json.Marshal(struct {
		Config                     Config
		Journal, Disabled, Profile json.RawMessage
	}{c, s.Journal, s.Disable, s.Profile})
	return digest(b)
}

func requireSwapSnapshot(s upgradeSnapshot) error {
	if !s.Check.QuiescentSnapshot || (len(s.Journal) > 0 && !s.Check.JournalIdentityMatches) {
		return errors.New("binary replacement requires a quiescent current identity and matching journal")
	}
	return nil
}

func openBinary(path string) (*os.File, error) {
	f, err := openStateJSONFile(path)
	if err != nil {
		return nil, err
	}
	st, err := f.Stat()
	if err == nil && (!st.Mode().IsRegular() || st.Size() < 64 || st.Size() > maxBinaryBytes) {
		err = errors.New("binary must be a regular ELF file between 64 bytes and 64MiB")
	}
	if err == nil {
		var header [4]byte
		_, err = io.ReadFull(f, header[:])
		if err == nil && string(header[:]) != "\x7fELF" {
			err = errors.New("binary is not ELF")
		}
		if err == nil {
			_, err = f.Seek(0, io.SeekStart)
		}
	}
	if err != nil {
		f.Close()
		return nil, err
	}
	return f, nil
}

func binaryDigest(f *os.File) (string, error) {
	if _, err := f.Seek(0, io.SeekStart); err != nil {
		return "", err
	}
	// Bounded streaming avoids loading the binary into the optional helper's RSS.
	h := newBinaryHash()
	n, err := io.CopyBuffer(h, io.LimitReader(f, maxBinaryBytes+1), make([]byte, 32768))
	if err != nil {
		return "", err
	}
	if n > maxBinaryBytes {
		return "", errors.New("binary grew beyond limit")
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}

type limitedOutput struct{ data []byte }

func (w *limitedOutput) Write(p []byte) (int, error) {
	if len(w.data)+len(p) > 8192 {
		return 0, errors.New("build-info exceeds 8KiB")
	}
	w.data = append(w.data, p...)
	return len(p), nil
}

func checkPreviousProtocol(ctx context.Context, target string) error {
	ctx, cancel := context.WithTimeout(ctx, 3*time.Second)
	defer cancel()
	command := exec.CommandContext(ctx, target, "build-info")
	out := &limitedOutput{}
	command.Stdout = out
	command.Stderr = io.Discard
	if err := command.Run(); err != nil {
		return fmt.Errorf("verified previous binary build-info failed: %w", err)
	}
	var info struct {
		LockProtocol    string `json:"lock_protocol"`
		JournalVersions []int  `json:"journal_versions"`
	}
	// build-info is additive; only the required protocol fields are decoded here.
	if err := json.Unmarshal(out.data, &info); err != nil {
		return err
	}
	if info.LockProtocol != LockProtocol {
		return errors.New("previous binary uses an unknown lock protocol")
	}
	for _, v := range info.JournalVersions {
		if v == 1 {
			return nil
		}
	}
	return errors.New("previous reader does not advertise journal v1")
}

func syncDirectory(path string) error {
	f, err := os.Open(path)
	if err != nil {
		return err
	}
	defer f.Close()
	return f.Sync()
}

func copyBinary(f *os.File, destination, expected string) error {
	if _, err := f.Seek(0, io.SeekStart); err != nil {
		return err
	}
	out, err := os.OpenFile(destination, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0700)
	if err != nil {
		return err
	}
	h := newBinaryHash()
	n, e := io.CopyBuffer(io.MultiWriter(out, h), io.LimitReader(f, maxBinaryBytes+1), make([]byte, 32768))
	if e == nil && (n > maxBinaryBytes || hex.EncodeToString(h.Sum(nil)) != expected) {
		e = errors.New("binary changed during copy")
	}
	if e == nil {
		e = out.Chmod(0755)
	}
	if e == nil {
		e = out.Sync()
	}
	closeErr := out.Close()
	return errors.Join(e, closeErr)
}

// InstallOwnBinary is explicit maintenance, never called by run/startup. The
// running candidate must live outside installDir; the supervisor keeps its old
// command and may resume only after enable. No process is killed here.
func InstallOwnBinary(ctx context.Context, c Config, env Environment, installDir, backupDir, previousSHA, candidateSHA string) (BinaryReceipt, error) {
	var receipt BinaryReceipt
	if !validSHA(previousSHA) || !validSHA(candidateSHA) {
		return receipt, errors.New("explicit lowercase previous and candidate SHA256 are required")
	}
	if err := realInstallDirectory(installDir); err != nil {
		return receipt, err
	}
	if pathWithin(c.StateDir, installDir) || pathWithin(installDir, c.StateDir) {
		return receipt, errors.New("installation and state directories must be separate")
	}
	if !filepath.IsAbs(backupDir) || filepath.Clean(backupDir) != backupDir {
		return receipt, errors.New("backup directory must be a fresh clean absolute path")
	}
	if err := realInstallDirectory(filepath.Dir(backupDir)); err != nil {
		return receipt, err
	}
	for _, p := range []string{c.StateDir, installDir} {
		if pathWithin(p, backupDir) || pathWithin(backupDir, p) {
			return receipt, errors.New("backup, state and installation directories must be separate")
		}
	}
	if c.IOProfile != "" && pathWithin(backupDir, resolveDiagnosticGuardPath(c.IOProfile)) {
		return receipt, errors.New("backup directory overlaps IO profile")
	}
	target := filepath.Join(installDir, "crg")
	err := withUpgradeSnapshot(c, env, func(s upgradeSnapshot) error {
		if err := requireSwapSnapshot(s); err != nil {
			return err
		}
		old, err := openBinary(target)
		if err != nil {
			return err
		}
		defer old.Close()
		oldSHA, err := binaryDigest(old)
		if err != nil {
			return err
		}
		if oldSHA != previousSHA {
			return errors.New("installed binary SHA256 mismatch")
		}
		if err = checkPreviousProtocol(ctx, target); err != nil {
			return err
		}
		selfPath, err := os.Executable()
		if err != nil {
			return err
		}
		if pathWithin(installDir, selfPath) {
			return errors.New("run the candidate from staging outside the installation directory")
		}
		self, err := openRunningBinary()
		if err != nil {
			return err
		}
		defer self.Close()
		selfSHA, err := binaryDigest(self)
		if err != nil {
			return err
		}
		if selfSHA != candidateSHA {
			return errors.New("running candidate SHA256 mismatch")
		}
		if err = os.Mkdir(backupDir, 0700); err != nil {
			return err
		}
		if err = syncDirectory(filepath.Dir(backupDir)); err != nil {
			return err
		}
		if err = copyBinary(old, filepath.Join(backupDir, "previous-crg"), previousSHA); err != nil {
			return err
		}
		backup := StateBackup{"crg-state-backup-v1", time.Now().UTC().Format(time.RFC3339), s.Check, s.Journal, s.Disable, s.Profile}
		encoded, err := json.MarshalIndent(backup, "", "  ")
		if err != nil {
			return err
		}
		if len(encoded) > 4*MaxJSONBytes {
			return errors.New("private recovery state exceeds 4MiB")
		}
		if err = writePrivateBackup(filepath.Join(backupDir, "state.json"), c.StateDir, append(encoded, '\n')); err != nil {
			return err
		}
		receipt = BinaryReceipt{"crg-binary-receipt-v1", env.Identity, installDir, previousSHA, candidateSHA, binarySnapshot(c, s), "prepared"}
		if err = AtomicJSON(filepath.Join(backupDir, "receipt.json"), receipt); err != nil {
			return err
		}
		return replaceBinary(c, env, s, self, target, candidateSHA, backupDir, &receipt, "installed")
	})
	return receipt, err
}

func replaceBinary(c Config, env Environment, s upgradeSnapshot, source *os.File, target, expected, backupDir string, receipt *BinaryReceipt, state string) error {
	stage, err := os.CreateTemp(filepath.Dir(target), ".crg-stage-")
	if err != nil {
		return err
	}
	stagePath := stage.Name()
	if err = stage.Close(); err != nil {
		return err
	}
	if err = os.Remove(stagePath); err != nil {
		return err
	}
	defer os.Remove(stagePath)
	if err = copyBinary(source, stagePath, expected); err != nil {
		return err
	}
	fresh, err := inspectUpgrade(c, env)
	if err != nil {
		return err
	}
	if err = VerifyIdentity(env); err != nil {
		return err
	}
	if err = requireSwapSnapshot(fresh); err != nil {
		return err
	}
	if binarySnapshot(c, fresh) != binarySnapshot(c, s) {
		return errors.New("state changed during binary copy; replacement refused")
	}
	current, err := openBinary(target)
	if err != nil {
		return err
	}
	got, e := binaryDigest(current)
	current.Close()
	if e != nil {
		return e
	}
	want := receipt.PreviousSHA256
	if state == "rolled_back" {
		want = receipt.CandidateSHA256
	}
	if got != want {
		return errors.New("installed binary changed before commit")
	}
	if err = os.Rename(stagePath, target); err != nil {
		return err
	}
	if err = syncDirectory(filepath.Dir(target)); err != nil {
		return fmt.Errorf("binary renamed but directory sync failed; inspect target SHA256 and prepared receipt: %w", err)
	}
	receipt.State = state
	if err = AtomicJSON(filepath.Join(backupDir, "receipt.json"), receipt); err != nil {
		return fmt.Errorf("binary renamed but receipt update failed; inspect target SHA256: %w", err)
	}
	return nil
}

func RollbackBinary(c Config, env Environment, installDir, backupDir string) (BinaryReceipt, error) {
	var receipt BinaryReceipt
	if err := realInstallDirectory(installDir); err != nil {
		return receipt, err
	}
	if err := realInstallDirectory(backupDir); err != nil {
		return receipt, err
	}
	b, err := ReadStateBoundedFile(filepath.Join(backupDir, "receipt.json"))
	if err != nil {
		return receipt, err
	}
	if err = Decode(b, &receipt); err != nil {
		return receipt, err
	}
	if receipt.Schema != "crg-binary-receipt-v1" || receipt.InstallDir != installDir || receipt.Identity != env.Identity || !validSHA(receipt.PreviousSHA256) || !validSHA(receipt.CandidateSHA256) || !validSHA(receipt.SnapshotSHA256) || (receipt.State != "prepared" && receipt.State != "installed") {
		return receipt, errors.New("incompatible binary rollback receipt")
	}
	err = withUpgradeSnapshot(c, env, func(s upgradeSnapshot) error {
		if e := requireSwapSnapshot(s); e != nil {
			return e
		}
		if binarySnapshot(c, s) != receipt.SnapshotSHA256 {
			return errors.New("state or effective configuration changed since installation; automatic rollback refused")
		}
		old, e := openBinary(filepath.Join(backupDir, "previous-crg"))
		if e != nil {
			return e
		}
		defer old.Close()
		got, e := binaryDigest(old)
		if e != nil {
			return e
		}
		if got != receipt.PreviousSHA256 {
			return errors.New("rollback binary SHA256 mismatch")
		}
		return replaceBinary(c, env, s, old, filepath.Join(installDir, "crg"), receipt.PreviousSHA256, backupDir, &receipt, "rolled_back")
	})
	return receipt, err
}
