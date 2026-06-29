package main

import "fmt"

type notFoundError struct{ kind, id string }

func (e *notFoundError) Error() string { return fmt.Sprintf("%s not found: %s", e.kind, e.id) }

type alreadyExistsError struct{ kind, id string }

func (e *alreadyExistsError) Error() string {
	return fmt.Sprintf("%s already exists: %s", e.kind, e.id)
}

type unavailableError struct{ equipmentID string }

func (e *unavailableError) Error() string {
	return fmt.Sprintf("equipment not available: %s", e.equipmentID)
}

type alreadyClosedError struct{ checkoutID int64 }

func (e *alreadyClosedError) Error() string {
	return fmt.Sprintf("checkout already closed: %d", e.checkoutID)
}
