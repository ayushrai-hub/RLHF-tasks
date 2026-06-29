package main

type SortOrder string

const (
	SortAsc  SortOrder = "ASC"
	SortDesc SortOrder = "DESC"
)

func isValidSortOrder(s string) bool {
	return s == string(SortAsc) || s == string(SortDesc)
}
