package carrier

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"sort"

	"gradlab/internal/paths"
)

type Carrier struct {
	Variables map[string][]float64 `json:"variables"`
}

func Load() Carrier {
	b, err := os.ReadFile(paths.PoolPath)
	if err != nil {
		return Carrier{Variables: map[string][]float64{}}
	}
	var p Carrier
	_ = json.Unmarshal(b, &p)
	if p.Variables == nil {
		p.Variables = map[string][]float64{}
	}
	return p
}

func (p *Carrier) MergeAssign(_ map[string][]float64) {}

func (p *Carrier) Clear() {
	p.Variables = map[string][]float64{}
}

func (p *Carrier) Checksum() string {
	keys := make([]string, 0, len(p.Variables))
	for k := range p.Variables {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	canon := map[string]any{"variables": p.Variables}
	b, _ := json.Marshal(canon)
	sum := sha256.Sum256(b)
	return hex.EncodeToString(sum[:])
}

func (p Carrier) Save() error {
	_ = os.MkdirAll(paths.VarDir, 0o755)
	b, _ := json.MarshalIndent(map[string]any{
		"variables":     p.Variables,
		"pool_checksum": p.Checksum(),
	}, "", "  ")
	return os.WriteFile(paths.PoolPath, append(b, '\n'), 0o644)
}
