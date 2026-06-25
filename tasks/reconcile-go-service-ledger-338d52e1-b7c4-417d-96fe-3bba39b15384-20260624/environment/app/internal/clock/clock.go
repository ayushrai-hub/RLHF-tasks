package clock

import "time"

func ParseRFC3339(value string) (time.Time, error) {
	return time.Parse(time.RFC3339, value)
}
