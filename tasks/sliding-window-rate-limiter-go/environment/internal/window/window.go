// Package window provides sliding window utilities.
// Per Cloudflare RFC §3.1: exclusive start boundary means requests
// at exactly (now - window_ms) belong to the previous window.
package window

// BoundaryMode defines how window boundaries are handled.
// Per RFC §3.1: exclusive start is the correct mode.
const BoundaryMode = "exclusive_start"

// DefaultWindowMs per Cloudflare RFC §2.
const DefaultWindowMs = 1000

// DefaultMaxRequests per Cloudflare RFC §2.
const DefaultMaxRequests = 10
