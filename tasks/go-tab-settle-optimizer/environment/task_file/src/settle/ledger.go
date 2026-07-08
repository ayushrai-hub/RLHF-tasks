package settle

// min3 returns the smallest of three integers. It is used to size a single
// transfer to the smaller of the debtor's remaining debt, the creditor's
// remaining credit, and the per-transfer cap.
func min3(a, b, c int) int {
	m := a
	if b < m {
		m = b
	}
	if c < m {
		m = c
	}
	return m
}
