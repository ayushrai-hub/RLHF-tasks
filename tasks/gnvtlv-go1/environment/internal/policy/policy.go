package policy

import (
	"encoding/json"
	"fmt"
	"os"
)

type Policy struct {
	Version         int             `json:"version"`
	Rules           map[string]Rule `json:"rules"`
	VendorAllowlist []int           `json:"vendor_allowlist"`
	MaxPerClass     map[string]int  `json:"max_per_class"`
}

type Rule struct {
	Severity string `json:"severity"`
	Mute     bool   `json:"mute"`
}

func LoadFromFile(path string) (*Policy, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("policy: %w", err)
	}
	p := &Policy{}
	if err := json.Unmarshal(b, p); err != nil {
		return nil, fmt.Errorf("policy parse: %w", err)
	}
	if p.Rules == nil {
		p.Rules = make(map[string]Rule)
	}
	if p.MaxPerClass == nil {
		p.MaxPerClass = make(map[string]int)
	}
	return p, nil
}

func (p *Policy) IsMuted(code string) bool {
	if p == nil {
		return false
	}
	r, ok := p.Rules[code]
	return ok && r.Mute
}

func (p *Policy) VendorAllowed(v int) bool {
	if p == nil {
		return false
	}
	for _, a := range p.VendorAllowlist {
		if a == v {
			return true
		}
	}
	return false
}

func (p *Policy) CapForClass(class int) int {
	if p == nil {
		return 0
	}
	key := fmt.Sprintf("0x%04x", class)
	return p.MaxPerClass[key]
}
