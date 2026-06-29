package main

import "fmt"

var validCategories = map[string]bool{
	"tool":        true,
	"electronics": true,
	"furniture":   true,
}

// validateCategory returns an error if category is not one of the allowed values.
func validateCategory(category string) error {
	if !validCategories[category] {
		return fmt.Errorf("invalid category %q: must be tool|electronics|furniture", category)
	}
	return nil
}

// validateNonEmpty returns an error when s is empty.
func validateNonEmpty(label, s string) error {
	if s == "" {
		return fmt.Errorf("%s must not be empty", label)
	}
	return nil
}

// validatePositive returns an error when n is not positive.
func validatePositive(label string, n int64) error {
	if n <= 0 {
		return fmt.Errorf("%s must be positive", label)
	}
	return nil
}
