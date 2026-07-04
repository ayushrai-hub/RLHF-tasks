package main

import "fmt"

// AddEmployee creates a new employee and returns the new id, or "exists".
func AddEmployee(name string, gross, mandatory int64) (int64, error) {
	_, _, _ = name, gross, mandatory
	return 0, fmt.Errorf("not_implemented")
}

// LookupEmployee returns the employee with the given name, or nil when unknown.
func LookupEmployee(name string) (*Employee, error) {
	_ = name
	return nil, fmt.Errorf("not_implemented")
}

// ListEmployees returns every employee sorted by name.
func ListEmployees() ([]Employee, error) {
	return nil, fmt.Errorf("not_implemented")
}

// AddOrder records a garnishment order and returns the new id.
func AddOrder(employeeID int64, kind string, priority, cap int64) (int64, error) {
	_, _, _, _ = employeeID, kind, priority, cap
	return 0, fmt.Errorf("not_implemented")
}

// ListOrders returns an employee's orders ordered by priority then id.
func ListOrders(employeeID int64) ([]Order, error) {
	_ = employeeID
	return nil, fmt.Errorf("not_implemented")
}
