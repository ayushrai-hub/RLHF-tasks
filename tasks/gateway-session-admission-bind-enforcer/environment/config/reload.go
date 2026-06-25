package config

import "gateway-session/rate"

func ApplyReload(buckets map[string]rate.Bucket, cfg Config) map[string]rate.Bucket {
	out := make(map[string]rate.Bucket, len(cfg.Backends))
	for id, be := range cfg.Backends {
		capacity := be.Capacity
		if capacity <= 0 {
			capacity = 100
		}
		tokens := capacity
		if prev, ok := buckets[id]; ok {
			tokens = prev.Tokens
			if tokens > capacity {
				tokens = capacity
			}
		}
		out[id] = rate.NewBucket(capacity, tokens)
	}
	return out
}
