package guard

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

const LockProtocol = "cgroup-inode-flock+state-agent-lock-v1"

// A successful check describes this reader and a locked snapshot. It is not an
// authorization token for a later replacement, nor a claim about another binary.
type UpgradeCheck struct {
	Schema                 string   `json:"schema"`
	Compatible             bool     `json:"compatible"`
	State                  string   `json:"state"`
	LockProtocol           string   `json:"lock_protocol"`
	JournalVersion         int      `json:"journal_version,omitempty"`
	JournalSHA256          string   `json:"journal_sha256,omitempty"`
	JournalIdentityMatches bool     `json:"journal_identity_matches"`
	MutationCount          int      `json:"mutation_count"`
	Controllers            []string `json:"controllers"`
	DisabledForCurrent     bool     `json:"disabled_for_current_container"`
	ProfileVersion         int      `json:"profile_version,omitempty"`
	ProfileSHA256          string   `json:"profile_sha256,omitempty"`
	QuiescentSnapshot      bool     `json:"quiescent_snapshot"`
	Detail                 string   `json:"detail"`
}

type upgradeSnapshot struct {
	Check   UpgradeCheck
	Journal json.RawMessage
	Disable json.RawMessage
	Profile json.RawMessage
}

func digest(b []byte) string {
	s := sha256.Sum256(b)
	return hex.EncodeToString(s[:])
}

func inspectUpgrade(c Config, env Environment) (upgradeSnapshot, error) {
	r := upgradeSnapshot{Check: UpgradeCheck{Schema: "crg-upgrade-check-v1", LockProtocol: LockProtocol, Controllers: []string{}}}
	b, err := ReadStateBoundedFile(filepath.Join(c.StateDir, "journal.json"))
	if err == nil {
		var j Journal
		if err = Decode(b, &j); err != nil {
			return r, fmt.Errorf("journal incompatible: %w", err)
		}
		if err = validateJournal(j); err != nil {
			return r, err
		}
		r.Journal = b
		r.Check.JournalVersion, r.Check.JournalSHA256 = j.Version, digest(b)
		r.Check.JournalIdentityMatches = j.Identity == env.Identity && j.Target == env.Target
		r.Check.MutationCount = len(j.Mutations)
		seen := map[string]bool{}
		for _, m := range j.Mutations {
			seen[m.File] = true
		}
		for name := range seen {
			r.Check.Controllers = append(r.Check.Controllers, name)
		}
		sort.Strings(r.Check.Controllers)
	} else if !os.IsNotExist(err) {
		return r, err
	}
	b, err = ReadStateBoundedFile(filepath.Join(c.StateDir, "disabled.json"))
	if err == nil {
		var marker DisableMarker
		if err = Decode(b, &marker); err != nil {
			return r, err
		}
		if marker.Version != 1 || marker.Identity == "" {
			return r, errors.New("unsupported disable marker")
		}
		r.Disable = b
		r.Check.DisabledForCurrent = marker.Identity == env.Identity
	} else if !os.IsNotExist(err) {
		return r, err
	}
	if c.IOProfile != "" {
		b, err = ReadBoundedFile(c.IOProfile)
		if err == nil {
			var profile Profile
			if err = Decode(b, &profile); err != nil {
				return r, err
			}
			if err = ValidateProfile(profile); err != nil {
				return r, err
			}
			r.Profile = b
			r.Check.ProfileVersion, r.Check.ProfileSHA256 = profile.Version, digest(b)
		} else if !os.IsNotExist(err) {
			return r, err
		}
	}
	r.Check.Compatible, r.Check.State = true, "compatible"
	r.Check.Detail = "this reader accepts the snapshot; check the replacement reader separately; no migration or control writes performed"
	return r, nil
}

// Locks are acquired without creating, archiving or rewriting any state file.
// A missing lock is not silently initialized by the preview tool.
func withUpgradeSnapshot(c Config, env Environment, visit func(upgradeSnapshot) error) error {
	group, err := lockGroup(env.Target)
	if err != nil {
		return fmt.Errorf("%w: %v", ErrLocked, err)
	}
	defer group.Close()
	st, err := os.Lstat(c.StateDir)
	if err != nil {
		return err
	}
	resolved, resolveErr := filepath.EvalSymlinks(c.StateDir)
	if !st.IsDir() || st.Mode()&os.ModeSymlink != 0 || resolveErr != nil || resolved != c.StateDir {
		return errors.New("upgrade state directory must be a real absolute directory without symlink components")
	}
	state, err := lockExistingState(filepath.Join(c.StateDir, "agent.lock"))
	if err != nil {
		return fmt.Errorf("cannot reserve existing state lock: %w", err)
	}
	defer state.Close()
	if err = VerifyIdentity(env); err != nil {
		return err
	}
	r, err := inspectUpgrade(c, env)
	if err != nil {
		return err
	}
	r.Check.QuiescentSnapshot = r.Check.DisabledForCurrent
	if !r.Check.DisabledForCurrent {
		r.Check.Detail += "; disable the current identity and stop its optional helper before upgrade"
	}
	return visit(r)
}

func CheckUpgrade(c Config, env Environment) (UpgradeCheck, error) {
	var r UpgradeCheck
	err := withUpgradeSnapshot(c, env, func(s upgradeSnapshot) error { r = s.Check; return nil })
	return r, err
}

// This is a private recovery backup, not the redacted diagnostic bundle. There
// is intentionally no automatic migration/import into a different identity.
type StateBackup struct {
	Schema   string          `json:"schema"`
	TimeUTC  string          `json:"time_utc"`
	Check    UpgradeCheck    `json:"check"`
	Journal  json.RawMessage `json:"journal,omitempty"`
	Disabled json.RawMessage `json:"disabled,omitempty"`
	Profile  json.RawMessage `json:"io_profile,omitempty"`
}

func BackupUpgradeState(c Config, env Environment, output string) (UpgradeCheck, error) {
	var result UpgradeCheck
	err := withUpgradeSnapshot(c, env, func(s upgradeSnapshot) error {
		result = s.Check
		if !s.Check.QuiescentSnapshot {
			return errors.New("state backup requires the current identity to be disabled and writer locks free")
		}
		backup := StateBackup{"crg-state-backup-v1", time.Now().UTC().Format(time.RFC3339), s.Check, s.Journal, s.Disable, s.Profile}
		encoded, err := json.MarshalIndent(backup, "", "  ")
		if err != nil {
			return err
		}
		if len(encoded) > 4*MaxJSONBytes {
			return errors.New("state backup exceeds 4MiB")
		}
		if c.IOProfile != "" && resolveDiagnosticGuardPath(output) == resolveDiagnosticGuardPath(c.IOProfile) {
			return errors.New("backup cannot use the IO profile destination")
		}
		return writePrivateBackup(output, c.StateDir, append(encoded, '\n'))
	})
	return result, err
}

func writePrivateBackup(output, stateDir string, encoded []byte) error {
	if !filepath.IsAbs(output) || filepath.Clean(output) != output {
		return errors.New("backup output must be a clean absolute fresh file path")
	}
	parent, err := filepath.EvalSymlinks(filepath.Dir(output))
	if err != nil {
		return err
	}
	state, err := filepath.EvalSymlinks(stateDir)
	if err != nil {
		return err
	}
	resolved := filepath.Join(parent, filepath.Base(output))
	rel, err := filepath.Rel(state, resolved)
	if err == nil && rel != ".." && !strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		return errors.New("backup must be outside the state directory")
	}
	f, err := os.OpenFile(resolved, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if err != nil {
		return err
	}
	n, writeErr := f.Write(encoded)
	if writeErr == nil && n != len(encoded) {
		writeErr = errors.New("short backup write")
	}
	if writeErr == nil {
		writeErr = f.Sync()
	}
	closeErr := f.Close()
	if writeErr != nil || closeErr != nil {
		return errors.Join(writeErr, closeErr)
	}
	d, err := os.Open(parent)
	if err != nil {
		return err
	}
	defer d.Close()
	return d.Sync()
}
