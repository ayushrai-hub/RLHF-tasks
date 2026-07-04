package search

import (
	"math"
	"time"

	"offline-search-shard-coherence/internal/model"
)

func ScoreDocument(doc model.Document, spec QuerySpec, epoch string) (float64, []string, error) {
	titleTokens := tokens(doc.Title)
	bodyTokens := tokens(doc.Body)
	anchorTokens := tokens(doc.AnchorText)
	score := doc.Quality
	matched := []string{}
	for _, term := range spec.Terms {
		titleHits := countTerm(titleTokens, term)
		bodyHits := countTerm(bodyTokens, term)
		anchorHits := countTerm(anchorTokens, term)
		score += float64(6*titleHits + bodyHits + 3*anchorHits)
		if titleHits+bodyHits+anchorHits > 0 {
			matched = append(matched, term)
		}
	}
	for _, phrase := range spec.Phrases {
		score += float64(12*countPhrase(doc.Title, phrase) + 5*countPhrase(doc.Body, phrase))
	}
	fresh, err := Freshness(doc.Published, epoch)
	if err != nil {
		return 0, nil, err
	}
	score += fresh
	return round3(score), matched, nil
}

func Freshness(published, epoch string) (float64, error) {
	pub, err := time.Parse("2006-01-02", published)
	if err != nil {
		return 0, err
	}
	ep, err := time.Parse("2006-01-02", epoch)
	if err != nil {
		return 0, err
	}
	if pub.After(ep) {
		return 0, nil
	}
	age := int(ep.Sub(pub).Hours() / 24)
	val := float64(90-age) / 30.0
	if val < 0 {
		val = 0
	}
	return val, nil
}

func round3(x float64) float64 {
	return math.Round(x*1000) / 1000
}
