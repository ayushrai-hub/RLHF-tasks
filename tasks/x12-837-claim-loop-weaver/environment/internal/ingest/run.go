package ingest

import (
	"claim-weaver/internal/staging"
	"claim-weaver/internal/weave"
)

func Run(shardsDir, manifestPath string) (staging.WeaveSnapshot, error) {
	engine := weave.NewEngine()
	manifest, err := engine.LoadManifest(manifestPath)
	if err != nil {
		return staging.WeaveSnapshot{}, err
	}
	if err := engine.ProcessShards(shardsDir, manifest); err != nil {
		return staging.WeaveSnapshot{}, err
	}
	return engine.BuildSnapshot(), nil
}
