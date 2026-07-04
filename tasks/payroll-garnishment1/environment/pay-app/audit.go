package main

import "fmt"

// AuditSecret returns the HMAC key from PAY_AUDIT_SECRET, or the default.
func AuditSecret() string {
	return "pay-audit-key"
}

// AppendAudit appends one audit entry for a remittance line.
func AppendAudit(employeeID int64, r Remit) error {
	_, _ = employeeID, r
	return fmt.Errorf("not_implemented")
}

// AuditChain returns the stored audit chain ordered by seq.
func AuditChain() ([]AuditEntry, error) {
	return nil, fmt.Errorf("not_implemented")
}

// VerifyChain recomputes the chain and reports the first break.
func VerifyChain(entries []AuditEntry) (bool, int64, string) {
	_ = entries
	return false, 0, "not_implemented"
}
