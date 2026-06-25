package events

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"strings"
)

func ReadJSONL(path string) ([]Event, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	var out []Event
	scanner := bufio.NewScanner(file)
	line := 0
	for scanner.Scan() {
		line++
		text := strings.TrimSpace(scanner.Text())
		if text == "" {
			continue
		}
		var event Event
		if err := json.Unmarshal([]byte(text), &event); err != nil {
			return nil, fmt.Errorf("line %d: %w", line, err)
		}
		out = append(out, event)
	}
	return out, scanner.Err()
}
