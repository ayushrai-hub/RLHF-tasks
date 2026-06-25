package report

import (
	"bytes"
	"encoding/csv"

	"service-ledger/internal/summary"
)

func ToCSV(rep summary.Report) ([]byte, error) {
	var buf bytes.Buffer
	writer := csv.NewWriter(&buf)
	for _, service := range rep.Services {
		for metric, values := range service.Metrics {
			if err := writer.Write([]string{service.Service, metric, floatString(values.Sum)}); err != nil {
				return nil, err
			}
		}
	}
	writer.Flush()
	return buf.Bytes(), writer.Error()
}
