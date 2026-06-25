package rate

type Bucket struct {
	Tokens   int `json:"tokens"`
	Capacity int `json:"capacity"`
}

func NewBucket(capacity int, tokens int) Bucket {
	if tokens > capacity {
		tokens = capacity
	}
	return Bucket{Tokens: tokens, Capacity: capacity}
}

func (b *Bucket) TryConsume(cost int) bool {
	if cost <= 0 {
		return true
	}
	if b.Tokens < cost {
		return false
	}
	b.Tokens -= cost
	return true
}
