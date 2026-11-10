//go:build !linux

package runlog

import "errors"

type sink struct{}

func openSink(string) (*sink, error) {
	return nil, errors.New("daily file logging requires Linux; stderr retained")
}
func (*sink) files() ([]dailyFile, error)       { return nil, errors.New("Linux required") }
func (*sink) remove(string) error               { return errors.New("Linux required") }
func (*sink) append(string, []byte, bool) error { return errors.New("Linux required") }
func (*sink) close()                            {}
