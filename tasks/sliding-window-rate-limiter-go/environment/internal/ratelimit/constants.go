// Package ratelimit constants.
// Per Cloudflare RFC §3.1: exclusive start boundary.
package ratelimit

// WindowBoundary per §3.1: exclusive start means requests at
// exactly (now - window_ms) are in the previous window.
const WindowBoundary = "exclusive_start"

// DefaultWindowMs per Cloudflare RFC §2.
const DefaultWindowMs = 1000

// DefaultMaxRequests per Cloudflare RFC §2.
const DefaultMaxRequests = 10
