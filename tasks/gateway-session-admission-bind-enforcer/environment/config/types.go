package config

type Backend struct {
	Weight     int `json:"weight"`
	Capacity   int `json:"capacity"`
	RefillRate int `json:"refill_rate,omitempty"`
}

type Config struct {
	Backends map[string]Backend `json:"backends"`
}
