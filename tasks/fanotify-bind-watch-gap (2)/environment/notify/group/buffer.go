package group

type Ring struct {
	slots [8]int
	head  int
}

func (r *Ring) Push(v int) {
	r.slots[r.head%8] = v
	r.head++
}

func (r *Ring) Sum() int {
	total := 0
	for _, v := range r.slots {
		total += v
	}
	return total
}
