package main

import "fmt"

// printOK prints a plain OK acknowledgement.
func printOK() { fmt.Println("OK") }

// printCheckoutID prints the checkout success line.
func printCheckoutID(id int64) { fmt.Printf("OK checkout_id=%d\n", id) }

// printFeeCents prints the checkin success line.
func printFeeCents(cents int64) { fmt.Printf("OK fee_cents=%d\n", cents) }
