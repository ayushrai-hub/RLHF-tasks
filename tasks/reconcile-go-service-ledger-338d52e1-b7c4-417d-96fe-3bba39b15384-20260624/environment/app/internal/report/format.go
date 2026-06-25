package report

import "strconv"

func floatString(value float64) string {
	return strconv.FormatFloat(value, 'f', -1, 64)
}
