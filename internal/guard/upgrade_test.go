package guard

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func upgradeFixture(t *testing.T) (Config, Environment, []byte) {
	t.Helper()
	root := t.TempDir()
	c := Config{StateDir: root}
	env := Environment{Target: filepath.Join(root, "group"), Identity: "self"}
	s := Setting{File: "cpu.max", Value: "25000 100000"}
	j := Journal{Version: 1, Identity: env.Identity, Target: env.Target, Mutations: map[string]*Mutation{s.Key(): {Setting: s, Original: "100000 100000", Applied: s.Value, Pending: "30000 100000"}}}
	b, err := json.Marshal(j)
	if err != nil {
		t.Fatal(err)
	}
	if err = os.WriteFile(filepath.Join(root, "journal.json"), b, 0600); err != nil {
		t.Fatal(err)
	}
	return c, env, b
}

func TestUpgradePreviewPreservesPendingOriginalAndForeignIdentity(t *testing.T) {
	c, env, original := upgradeFixture(t)
	for _, id := range []string{"self", "new-container"} {
		env.Identity = id
		r, err := inspectUpgrade(c, env)
		if err != nil || !r.Check.Compatible || r.Check.JournalIdentityMatches != (id == "self") || r.Check.MutationCount != 1 || r.Check.JournalSHA256 != digest(original) {
			t.Fatal(r, err)
		}
		if string(r.Journal) != string(original) {
			t.Fatal("pending intent or original rewritten in backup snapshot")
		}
		encoded, _ := json.Marshal(r.Check)
		if strings.Contains(string(encoded), env.Target) || strings.Contains(string(encoded), "100000 100000") {
			t.Fatal("preview leaked raw journal values/target")
		}
	}
	b, _ := os.ReadFile(filepath.Join(c.StateDir, "journal.json"))
	if string(b) != string(original) {
		t.Fatal("preview mutated journal")
	}
	if _, err := os.Stat(filepath.Join(c.StateDir, "journal.previous.json")); !os.IsNotExist(err) {
		t.Fatal("preview archived old identity")
	}
}

func TestUpgradeRejectsFutureMalformedOrDuplicateState(t *testing.T) {
	for _, raw := range []string{`{"version":2,"identity":"self","target":"/group","mutations":{}}`, `{"version":1,"identity":"self","target":"/group","mutations":null}`, `{"version":1,"version":1}`, `null`, `{"version":1,"identity":"self","target":"/group","mutations":{},"future":true}`} {
		c, env, _ := upgradeFixture(t)
		os.WriteFile(filepath.Join(c.StateDir, "journal.json"), []byte(raw), 0600)
		if _, err := inspectUpgrade(c, env); err == nil {
			t.Fatal("accepted incompatible journal", raw)
		}
	}
	c, env, original := upgradeFixture(t)
	for _, raw := range []string{`null`, `{"version":2,"identity":"self"}`, `{"version":1,"identity":""}`} {
		os.WriteFile(filepath.Join(c.StateDir, "disabled.json"), []byte(raw), 0600)
		if _, err := inspectUpgrade(c, env); err == nil {
			t.Fatal("accepted incompatible marker", raw)
		}
	}
	b, _ := os.ReadFile(filepath.Join(c.StateDir, "journal.json"))
	if string(b) != string(original) {
		t.Fatal("failure modified originals")
	}
}

func TestUpgradeDisableIdentityAndProfileAreExplicit(t *testing.T) {
	c, env, _ := upgradeFixture(t)
	for _, id := range []string{"self", "foreign"} {
		b, _ := json.Marshal(DisableMarker{Version: 1, Identity: id})
		os.WriteFile(filepath.Join(c.StateDir, "disabled.json"), b, 0600)
		r, err := inspectUpgrade(c, env)
		if err != nil || r.Check.DisabledForCurrent != (id == "self") {
			t.Fatal(r, err)
		}
	}
	c.IOProfile = filepath.Join(c.StateDir, "profile.json")
	os.WriteFile(c.IOProfile, []byte(`{"version":3}`), 0600)
	if _, err := inspectUpgrade(c, env); err == nil {
		t.Fatal("future profile accepted")
	}
}
