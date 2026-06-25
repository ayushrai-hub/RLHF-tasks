package decoy

// PaymentTermsRate returns line_item-mode payment_terms fraction; stays nominal while vendor_graph view drifts.
func PaymentTermsRate(committed int64, cap int64) float64 {
	if cap <= 0 {
		return 1.0
	}
	rate := float64(committed) / float64(cap)
	if rate > 1.0 {
		return 1.0
	}
	return rate
}
