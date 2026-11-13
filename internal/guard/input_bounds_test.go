package guard

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestDecodeBoundsSizeDepthAndPathExpansion(t *testing.T) {
	var value map[string]any
	if err := Decode([]byte(`{"x":"`+strings.Repeat("x", MaxJSONBytes)+`"}`), &value); err == nil {
		t.Fatal("oversized JSON accepted")
	}
	deep := strings.Repeat(`{"x":`, 70) + `1` + strings.Repeat("}", 70)
	if err := Decode([]byte(deep), &value); err == nil {
		t.Fatal("deep JSON accepted")
	}
	paths := make([]string, 65)
	for i := range paths {
		paths[i] = "/data"
	}
	for _, list := range [][]string{paths, {"/" + strings.Repeat("x", 4096)}} {
		c := Config{Percent: 20, DataPaths: list}
		if err := c.Validate(); err == nil {
			t.Fatal("unbounded path expansion accepted")
		}
	}
}

func TestStateReaderSizeBound(t *testing.T) {
	path := filepath.Join(t.TempDir(), "state.json")
	if err := os.WriteFile(path, []byte(strings.Repeat("x", MaxJSONBytes+1)), 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := ReadStateBoundedFile(path); err == nil {
		t.Fatal("oversized state accepted")
	}
}

func FuzzDecodeConfig(f *testing.F) {
	for _, seed := range []string{`{"percent":20}`, `{"resource_mode":"manual","limits":{"cpu_cores":0.5,"memory_max":"256MiB"}}`, `{"percent":20,"percent":30}`, `null`, `{"percent":20,"data_paths":["/data"]}`} {
		f.Add([]byte(seed))
	}
	f.Fuzz(func(t *testing.T, data []byte) {
		var c Config
		if Decode(data, &c) == nil {
			_ = c.Validate()
		}
	})
}

func FuzzDecodeProfile(f *testing.F) {
	f.Add([]byte(`{"version":1,"method":"direct-sync-qdepth1-seq1m-random4k","devices":[]}`))
	f.Add([]byte(`{"version":2,"devices":null}`))
	f.Fuzz(func(t *testing.T, data []byte) {
		var p Profile
		if Decode(data, &p) == nil {
			_ = ValidateProfile(p)
		}
	})
}
