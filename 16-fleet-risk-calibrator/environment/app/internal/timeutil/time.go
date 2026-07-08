package timeutil

import (
	"fmt"
	"time"
)

func ParseRFC3339(value string) (time.Time, error) {
	t, err := time.Parse(time.RFC3339, value)
	if err != nil {
		return time.Time{}, fmt.Errorf("parse timestamp %q: %w", value, err)
	}
	return t.UTC(), nil
}
