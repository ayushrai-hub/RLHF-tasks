package search

import (
	"offline-search-shard-coherence/internal/fsutil"
	"offline-search-shard-coherence/internal/model"
)

func SearchShard(path, shardID string, query model.Query, canon CanonicalMap, robots []RobotRule, epoch string) ([]model.Result, error) {
	docs, err := fsutil.ReadJSONL[model.Document](path)
	if err != nil {
		return nil, err
	}
	spec := ParseQuery(query.Text)
	out := []model.Result{}
	for _, doc := range docs {
		canonicalURL := canon.For(doc.URL)
		// Apply robots rules before scoring a document.
		if !Allowed(robots, canonicalURL) {
			continue
		}
		score, matched, err := ScoreDocument(doc, spec, epoch)
		if err != nil {
			return nil, err
		}
		if len(matched) == 0 {
			continue
		}
		out = append(out, model.Result{
			CanonicalURL:   canonicalURL,
			SelectedURL:    doc.URL,
			Title:          doc.Title,
			Score:          score,
			Published:      doc.Published,
			SourceShard:    shardID,
			MatchedTerms:   matched,
			SupportingURLs: []string{doc.URL},
		})
	}
	return out, nil
}
