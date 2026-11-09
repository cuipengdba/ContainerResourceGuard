package guard

import (
	"fmt"
	"path/filepath"
	"strconv"
)

func (e *Engine) pidsHeadroom(target string) error {
	s, err := e.Files.Read(filepath.Join(e.Env.Target, "pids.current"))
	if err != nil {
		return fmt.Errorf("cannot read pids.current before decrease: %w", err)
	}
	n, err := strconv.ParseUint(s, 10, 64)
	if err != nil {
		return fmt.Errorf("invalid pids.current")
	}
	margin := n / 10
	if margin < 32 {
		margin = 32
	}
	limit := maxNumber(target)
	if n > limit || margin > limit-n {
		return fmt.Errorf("unsafe pids decrease: target=%s current=%d; require at least 32 tasks or 10%% headroom", target, n)
	}
	return nil
}
