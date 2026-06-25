package events

func Dedupe(records []Event) []Event {
	seen := map[string]bool{}
	out := []Event{}
	for _, event := range records {
		key := event.Source + ":" + event.EventID
		if seen[key] {
			continue
		}
		seen[key] = true
		out = append(out, event)
	}
	return out
}
