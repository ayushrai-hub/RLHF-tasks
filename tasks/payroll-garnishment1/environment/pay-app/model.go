package main

// Employee is one payee. Gross is gross pay for the period in cents; Mandatory
// is the total mandated deductions in cents.
type Employee struct {
	ID        int64
	Name      string
	Gross     int64
	Mandatory int64
}

// Order is one garnishment order. Priority ranks orders for allocation (lower
// paid first); Cap is the per-order net target in cents used by the gross-up.
type Order struct {
	ID         int64
	EmployeeID int64
	Kind       string
	Priority   int64
	Cap        int64
}

// Remit is one order's gross-up figure for a remittance run: the smallest gross
// whose forward net clears the order's cap.
type Remit struct {
	Order  Order
	Amount int64
}

// AuditEntry is one link in the tamper-evident hash chain over a remittance
// run. Seq is 1-based.
type AuditEntry struct {
	Seq        int64
	EmployeeID int64
	OrderID    int64
	Kind       string
	Amount     int64
	PrevHash   string
	EntryHash  string
}
