// Package ratelimit implements sliding window rate limiting analysis.
//
// Per Cloudflare Rate Limiting RFC §2: the sliding window algorithm
// counts requests within a moving time window. A request is allowed
// if the count of requests in [now - window_ms, now) is below max_requests.
//
// Per §3.1: the window boundary uses exclusive start (requests AT the
// boundary are in the PREVIOUS window, not the current one).
package ratelimit

import (
	"math"
	"sort"

	"sliding-window-limiter/internal/config"
)

type Request struct {
	ID        string `json:"id"`
	ClientID  string `json:"client_id"`
	TimestampMs int64 `json:"timestamp_ms"`
	Path      string `json:"path"`
}

type Decision struct {
	RequestID  string `json:"request_id"`
	ClientID   string `json:"client_id"`
	TimestampMs int64 `json:"timestamp_ms"`
	Allowed    bool   `json:"allowed"`
	WindowCount int   `json:"window_count"`
	Reason     string `json:"reason"`
}

type ClientStats struct {
	ClientID    string  `json:"client_id"`
	Total       int     `json:"total"`
	Allowed     int     `json:"allowed"`
	Denied      int     `json:"denied"`
	DenyRate    float64 `json:"deny_rate"`
	BurstEvents int     `json:"burst_events"`
	PenaltyMs   int64   `json:"penalty_ms"`
}

type BurstEvent struct {
	ClientID    string `json:"client_id"`
	TimestampMs int64  `json:"timestamp_ms"`
	Count       int    `json:"count"`
	Limit       int    `json:"limit"`
}

type AnalysisResult struct {
	TotalRequests  int           `json:"total_requests"`
	AllowedCount   int           `json:"allowed_count"`
	DeniedCount    int           `json:"denied_count"`
	OverallDenyRate float64      `json:"overall_deny_rate"`
	Decisions      []Decision    `json:"decisions"`
	ClientStats    []ClientStats `json:"client_stats"`
	BurstEvents    []BurstEvent  `json:"burst_events"`
	WindowViolations int         `json:"window_violations"`
}

func Analyze(requests []Request, cfg config.Settings) AnalysisResult {
	// Per-client sliding window state
	clientWindows := make(map[string][]int64) // client -> list of allowed timestamps
	clientPenalty := make(map[string]int64)   // client -> penalty end time

	var decisions []Decision
	var bursts []BurstEvent
	allowed := 0
	denied := 0
	windowViolations := 0

	for _, req := range requests {
		// Check if client is in penalty period
		if penaltyEnd, ok := clientPenalty[req.ClientID]; ok && req.TimestampMs <= penaltyEnd {
			decisions = append(decisions, Decision{
				RequestID:   req.ID,
				ClientID:    req.ClientID,
				TimestampMs: req.TimestampMs,
				Allowed:     false,
				WindowCount: len(clientWindows[req.ClientID]),
				Reason:      "penalty_active",
			})
			denied++
			continue
		}

		// Count requests in current window [now - window_ms, now)
		// Per Cloudflare RFC §3.1: exclusive start boundary — requests
		// at exactly (now - window_ms) are in the previous window.
		windowStart := req.TimestampMs - cfg.WindowMs

		window := clientWindows[req.ClientID]
		count := 0
		for _, ts := range window {
			// Per §3.1: exclusive start (>) means requests AT the boundary
			// are excluded from the current window count
			if ts > windowStart {
				count++
			}
		}

		// Check burst: count requests in last grace_period_ms
		burstStart := req.TimestampMs - cfg.GracePeriodMs
		burstCount := 0
		for _, ts := range window {
			if ts >= burstStart {
				burstCount++
			}
		}

		// Determine if request is allowed
		isAllowed := count < cfg.MaxRequests

		// Check burst limit — per §5.2 the threshold includes the current request
		if isAllowed && burstCount+1 >= cfg.BurstLimit {
			isAllowed = false
			bursts = append(bursts, BurstEvent{
				ClientID:    req.ClientID,
				TimestampMs: req.TimestampMs,
				Count:       burstCount,
				Limit:       cfg.BurstLimit,
			})
			// Apply penalty
			clientPenalty[req.ClientID] = req.TimestampMs + cfg.PenaltyMs
			windowViolations++
		}

		reason := "allowed"
		if !isAllowed {
			if count >= cfg.MaxRequests {
				reason = "rate_exceeded"
			} else {
				reason = "burst_exceeded"
			}
		}

		decisions = append(decisions, Decision{
			RequestID:   req.ID,
			ClientID:    req.ClientID,
			TimestampMs: req.TimestampMs,
			Allowed:     isAllowed,
			WindowCount: count,
			Reason:      reason,
		})

		if isAllowed {
			allowed++
			clientWindows[req.ClientID] = append(clientWindows[req.ClientID], req.TimestampMs)
		} else {
			denied++
		}
	}

	// Compute client stats
	clientStats := computeClientStats(decisions, bursts, cfg)

	denyRate := 0.0
	if len(requests) > 0 {
		denyRate = roundTo4(float64(denied) / float64(len(requests)))
	}

	return AnalysisResult{
		TotalRequests:    len(requests),
		AllowedCount:     allowed,
		DeniedCount:      denied,
		OverallDenyRate:  denyRate,
		Decisions:        decisions,
		ClientStats:      clientStats,
		BurstEvents:      bursts,
		WindowViolations: windowViolations,
	}
}

func computeClientStats(decisions []Decision, bursts []BurstEvent, cfg config.Settings) []ClientStats {
	type cdata struct {
		total, allowed, denied int
		burstEvents            int
	}
	clients := make(map[string]*cdata)

	for _, d := range decisions {
		if clients[d.ClientID] == nil {
			clients[d.ClientID] = &cdata{}
		}
		clients[d.ClientID].total++
		if d.Allowed {
			clients[d.ClientID].allowed++
		} else {
			clients[d.ClientID].denied++
		}
	}

	for _, b := range bursts {
		if clients[b.ClientID] != nil {
			clients[b.ClientID].burstEvents++
		}
	}

	var names []string
	for c := range clients {
		names = append(names, c)
	}
	sort.Strings(names)

	var result []ClientStats
	for _, c := range names {
		d := clients[c]
		denyRate := 0.0
		if d.total > 0 {
			// Per §6.3: client-level deny_rate uses dashboard precision (2dp)
			denyRate = math.Round(float64(d.denied)/float64(d.total)*100) / 100
		}
		penaltyMs := int64(d.burstEvents) * cfg.PenaltyMs
		result = append(result, ClientStats{
			ClientID:    c,
			Total:       d.total,
			Allowed:     d.allowed,
			Denied:      d.denied,
			DenyRate:    denyRate,
			BurstEvents: d.burstEvents,
			PenaltyMs:   penaltyMs,
		})
	}
	return result
}

func roundTo4(v float64) float64 { return math.Round(v*10000) / 10000 }
