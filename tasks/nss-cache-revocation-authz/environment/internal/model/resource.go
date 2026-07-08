package model

type Resource struct {
	ID      string              `json:"id"`
	Actions map[string][]string `json:"actions"`
}
