package main

// validateGroup checks that an approver group is well-formed.
func validateGroup(name string, members []string) error {
	if name == "" {
		return ErrValidation
	}
	return nil
}
