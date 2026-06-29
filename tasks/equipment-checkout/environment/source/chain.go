package main

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
)

// computeHMAC returns the HMAC-SHA256 of data using key, encoded as lowercase hex.
func computeHMAC(key, data string) string {
	mac := hmac.New(sha256.New, []byte(key))
	mac.Write([]byte(data))
	return hex.EncodeToString(mac.Sum(nil))
}

// checkoutChainData formats the HMAC data string for an audit chain entry.
func checkoutChainData(chainID, checkoutID int64, equipmentID, borrowerID string, dailyRateCents int64, checkoutDate, prevHash string) string {
	return fmt.Sprintf("%d|CHECKOUT|%d|%s|%s|%d|%s|%s",
		chainID, checkoutID, equipmentID, borrowerID, dailyRateCents, checkoutDate, prevHash)
}
