package sink

import "xferverify/internal/io"

type RedirectSink struct{}

func (r *RedirectSink) WriteChunk(size int) (int, io.TermEvent, error) {
	return size, io.TermEvent{}, nil
}
