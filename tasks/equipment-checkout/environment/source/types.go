package main

// Equipment represents a piece of borrowable equipment.
type Equipment struct {
	EquipmentID    string
	Name           string
	Category       string
	DailyRateCents int64
	Status         string
}

// Borrower represents a person who can borrow equipment.
type Borrower struct {
	BorrowerID string
	Name       string
}

// Checkout represents an active or completed equipment loan.
type Checkout struct {
	CheckoutID     int64
	EquipmentID    string
	BorrowerID     string
	CheckoutDate   string
	CheckinDate    *string
	FeeCents       *int64
	Status         string
}

// ChainEntry represents one row in the audit_chain table.
type ChainEntry struct {
	ID             int64
	ChainID        int64
	EquipmentID    string
	CheckoutID     int64
	BorrowerID     string
	DailyRateCents int64
	CheckoutDate   string
	PrevHash       string
	Hash           string
}
