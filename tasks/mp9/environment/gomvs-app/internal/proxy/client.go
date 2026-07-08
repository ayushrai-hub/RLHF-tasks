// Package proxy is a small read-only client for the Go module proxy protocol
// served at https://proxy.golang.org. It lists the tagged versions of a module,
// fetches the .info metadata for one version, and fetches the raw go.mod file
// for one version. Responses are memoised on disk so a build-list computation
// that visits the same module twice, or a second command in the same run, does
// not refetch.
//
// The proxy addresses modules by an escaped, case-folded form of the module
// path. Building that escaped path is EscapePath in escape.go; the transport
// here takes an already-escaped element.
package proxy

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// BaseURL is the public Go module proxy.
const BaseURL = "https://proxy.golang.org"

// DefaultCacheDir holds raw proxy responses between calls. It lives outside the
// working tree so it survives across separate command invocations in one run.
const DefaultCacheDir = "/tmp/gomvs-cache"

// Client fetches module metadata over HTTP with an on-disk response cache.
type Client struct {
	BaseURL  string
	CacheDir string
	HTTP     *http.Client
}

// New returns a Client pointed at the live Go module proxy.
func New() *Client {
	return &Client{
		BaseURL:  BaseURL,
		CacheDir: DefaultCacheDir,
		HTTP:     &http.Client{Timeout: 30 * time.Second},
	}
}

func (c *Client) cachePath(escaped, name string) string {
	safe := strings.ReplaceAll(escaped, "/", "_")
	return filepath.Join(c.CacheDir, safe, name)
}

// get fetches one proxy path, serving a cached copy when present and otherwise
// performing the request with a short retry on rate limiting and 5xx.
func (c *Client) get(escaped, name, urlPath string) ([]byte, error) {
	cp := c.cachePath(escaped, name)
	if b, err := os.ReadFile(cp); err == nil {
		return b, nil
	}
	url := c.BaseURL + urlPath
	var lastErr error
	for attempt := 0; attempt < 4; attempt++ {
		req, err := http.NewRequest(http.MethodGet, url, nil)
		if err != nil {
			return nil, err
		}
		req.Header.Set("User-Agent", "module-proxy-mvs (terminus task; contact anonymous)")
		resp, err := c.HTTP.Do(req)
		if err != nil {
			lastErr = err
			time.Sleep(time.Duration(attempt+1) * 400 * time.Millisecond)
			continue
		}
		body, err := io.ReadAll(resp.Body)
		resp.Body.Close()
		if err != nil {
			lastErr = err
			continue
		}
		if resp.StatusCode == http.StatusTooManyRequests || resp.StatusCode >= 500 {
			lastErr = fmt.Errorf("proxy %s: status %d", urlPath, resp.StatusCode)
			time.Sleep(time.Duration(attempt+1) * 700 * time.Millisecond)
			continue
		}
		if resp.StatusCode != http.StatusOK {
			return nil, fmt.Errorf("proxy %s: status %d", urlPath, resp.StatusCode)
		}
		if err := os.MkdirAll(filepath.Dir(cp), 0o755); err == nil {
			_ = os.WriteFile(cp, body, 0o644)
		}
		return body, nil
	}
	return nil, fmt.Errorf("proxy %s failed: %w", urlPath, lastErr)
}

// List returns the raw @v/list body: the tagged versions of a module, one per
// line and unordered. The module path is escaped before the request.
func (c *Client) List(module string) ([]byte, error) {
	e := EscapePath(module)
	return c.get(e, "list", fmt.Sprintf("/%s/@v/list", e))
}

// Info returns the raw @v/<version>.info JSON for one version. Both the module
// path and the version are escaped before the request.
func (c *Client) Info(module, version string) ([]byte, error) {
	e := EscapePath(module)
	ev := EscapePath(version)
	return c.get(e, ev+".info", fmt.Sprintf("/%s/@v/%s.info", e, ev))
}

// GoMod returns the raw @v/<version>.mod body (the go.mod file) for one
// version. Both the module path and the version are escaped before the request.
func (c *Client) GoMod(module, version string) ([]byte, error) {
	e := EscapePath(module)
	ev := EscapePath(version)
	return c.get(e, ev+".mod", fmt.Sprintf("/%s/@v/%s.mod", e, ev))
}
