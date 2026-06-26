package meter

func Batch(n int) int {
	if n <= 0 {
		return 0
	}
	return (n + 7) / 8
}
