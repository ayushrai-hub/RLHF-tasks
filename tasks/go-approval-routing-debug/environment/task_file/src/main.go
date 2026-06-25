package main

import (
	"log"
	"net/http"
	"os"
)

func main() {
	svc := NewService()
	handler := NewHandler(svc)

	addr := ":8080"
	if p := os.Getenv("PORT"); p != "" {
		addr = ":" + p
	}

	log.Printf("approval-routing service listening on %s", addr)
	if err := http.ListenAndServe(addr, handler); err != nil {
		log.Fatal(err)
	}
}
