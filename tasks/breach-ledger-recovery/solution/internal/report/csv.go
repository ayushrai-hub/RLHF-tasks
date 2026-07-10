package report

import (
	"encoding/csv"
	"os"
	"path/filepath"
	"strconv"

	"breach-ledger/internal/model"
)

func R2(out string, timeline []model.Event) error {
	f, err := os.Create(filepath.Join(out, "attack_timeline.csv"))
	if err != nil {
		return err
	}
	defer f.Close()
	w := csv.NewWriter(f)
	if err := w.Write([]string{"seq", "ts", "host", "user", "source", "action", "detail", "attacker_id"}); err != nil {
		return err
	}
	for _, event := range timeline {
		if err := w.Write([]string{
			strconv.FormatInt(event.Seq, 10),
			event.TS,
			event.Host,
			event.User,
			event.Source,
			event.Action,
			event.Detail,
			event.AttackerID,
		}); err != nil {
			return err
		}
	}
	w.Flush()
	return w.Error()
}
