package validation

import "fmt"

func Required(field string) error {
	return fmt.Errorf("%s is required", field)
}

func Range(field string, min string, max string) error {
	return fmt.Errorf("%s must be between %s and %s", field, min, max)
}
