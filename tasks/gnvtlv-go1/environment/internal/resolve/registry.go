package resolve

import (
	"encoding/json"
	"fmt"
	"os"
)

type RegistryEntry struct {
	OptClass     int    `json:"opt_class"`
	Type         int    `json:"type"`
	Name         string `json:"name"`
	Kind         string `json:"kind"`
	FixedBytes   int    `json:"fixed_bytes"`
	VendorPrefix bool   `json:"vendor_prefix"`
}

type EtherEntry struct {
	Type int    `json:"type"`
	Name string `json:"name"`
}

type Registries struct {
	Geneve []RegistryEntry
	Ether  []EtherEntry
	geneve map[uint32]RegistryEntry
	ether  map[int]EtherEntry
}

func LoadRegistries(genevePath, etherPath string) (*Registries, error) {
	r := &Registries{}
	b, err := os.ReadFile(genevePath)
	if err != nil {
		return nil, fmt.Errorf("load %s: %w", genevePath, err)
	}
	if err := json.Unmarshal(b, &r.Geneve); err != nil {
		return nil, fmt.Errorf("parse %s: %w", genevePath, err)
	}
	b, err = os.ReadFile(etherPath)
	if err != nil {
		return nil, fmt.Errorf("load %s: %w", etherPath, err)
	}
	if err := json.Unmarshal(b, &r.Ether); err != nil {
		return nil, fmt.Errorf("parse %s: %w", etherPath, err)
	}
	r.geneve = make(map[uint32]RegistryEntry, len(r.Geneve))
	for _, e := range r.Geneve {
		r.geneve[uint32(e.OptClass)<<16|uint32(e.Type&0x7F)] = e
	}
	r.ether = make(map[int]EtherEntry, len(r.Ether))
	for _, e := range r.Ether {
		r.ether[e.Type] = e
	}
	return r, nil
}

func (r *Registries) LookupOption(class, typ int) (RegistryEntry, bool) {
	if r == nil {
		return RegistryEntry{}, false
	}
	e, ok := r.geneve[uint32(class)<<16|uint32(typ&0x7F)]
	return e, ok
}

func (r *Registries) LookupEther(typ int) (EtherEntry, bool) {
	if r == nil {
		return EtherEntry{}, false
	}
	e, ok := r.ether[typ]
	return e, ok
}
