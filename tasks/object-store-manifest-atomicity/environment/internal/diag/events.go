package diag

import "fmt"

type Event struct {
	BatchID string
	State   string
	Files   int
}

func FormatEvent(e Event) string {
	return fmt.Sprintf("batch=%s state=%s files=%d", e.BatchID, e.State, e.Files)
}
