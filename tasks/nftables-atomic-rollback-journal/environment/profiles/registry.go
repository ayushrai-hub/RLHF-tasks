package profiles

import (
	"os"
	"path/filepath"
	"strings"

	"nfrd.local/nfrd/model"
)

func Lookup(name string) model.ProfileSpec {
	base := filepath.Join(model.EnvRoot, "profiles", name+".toml")
	data, err := os.ReadFile(base)
	if err != nil {
		panic(err)
	}
	spec := model.ProfileSpec{Name: name, FixtureDir: filepath.Join(model.EnvRoot, "fixtures", name+"_rules")}
	for _, line := range strings.Split(string(data), "\n") {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "runs = ") {
			inner := strings.Trim(strings.TrimPrefix(line, "runs = "), "[]")
			for _, part := range strings.Split(inner, ",") {
				part = strings.Trim(strings.TrimSpace(part), "\"")
				if part != "" {
					spec.Runs = append(spec.Runs, part)
				}
			}
		}
		if strings.HasPrefix(line, "simulate = ") {
			spec.Simulate = strings.Trim(strings.TrimPrefix(line, "simulate = "), "\"")
		}
	}
	return spec
}
