package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestExplicitZeroPercentDoesNotFallBackToConfig(t *testing.T) {
	path := filepath.Join(t.TempDir(), "config.json")
	if err := os.WriteFile(path, []byte(`{"percent":20}`), 0600); err != nil {
		t.Fatal(err)
	}
	original := os.Args
	defer func() { os.Args = original }()
	for _, v := range []string{"0", "-1", "101", "NaN", "Inf"} {
		os.Args = []string{"crg", "run", "--config", path, "--percent", v}
		if err := mainErr(); err == nil {
			t.Fatalf("accepted explicit percent=%s", v)
		}
	}
}
