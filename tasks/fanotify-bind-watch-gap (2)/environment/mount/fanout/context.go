package fanout

import (
	"os"
	"path/filepath"
	"sync"
)

type Context struct {
	Workspace string
	HostView  string
	WorkView  string
	Published string
	Archive   string
	Fixtures  string

	mu      sync.Mutex
	pinGen  int
	pinPath string
	active  *Handle
}

type Handle struct {
	Gen  int
	Path string
	File *os.File
}

type Edge struct {
	Host string
	Work string
	Gen  int
}

func New(workspace, fixtures string) *Context {
	base := filepath.Clean(workspace)
	return &Context{
		Workspace: base,
		HostView:  filepath.Join(base, "layers", "host"),
		WorkView:  filepath.Join(base, "layers", "work"),
		Published: filepath.Join(base, "published"),
		Archive:   filepath.Join(base, "archive"),
		Fixtures:  filepath.Clean(fixtures),
	}
}

func (c *Context) Reset() {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.active != nil && c.active.File != nil {
		_ = c.active.File.Close()
	}
	c.active = nil
	c.pinGen = 0
	c.pinPath = ""
}

func (c *Context) ActiveGen() int {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.active != nil {
		return c.active.Gen
	}
	return c.pinGen
}

func (c *Context) SetActive(h *Handle) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.active = h
	if h != nil {
		c.pinGen = h.Gen
		c.pinPath = h.Path
	}
}

func (c *Context) PinnedPath() string {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.pinPath
}
