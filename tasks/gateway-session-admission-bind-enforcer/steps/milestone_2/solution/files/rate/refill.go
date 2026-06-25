package rate

func ApplyRefill(
	buckets map[string]Bucket,
	rates map[string]int,
	currentSeq int,
	lastRefillSeq int,
) {
	delta := currentSeq - lastRefillSeq
	if delta <= 0 {
		return
	}
	for id, bucket := range buckets {
		rateVal := rates[id]
		if rateVal <= 0 {
			continue
		}
		added := rateVal * delta
		tokens := bucket.Tokens + added
		if tokens > bucket.Capacity {
			tokens = bucket.Capacity
		}
		bucket.Tokens = tokens
		buckets[id] = bucket
	}
}
