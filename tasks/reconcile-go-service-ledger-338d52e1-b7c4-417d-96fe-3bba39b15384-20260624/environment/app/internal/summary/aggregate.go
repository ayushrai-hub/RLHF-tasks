package summary

import (
	"service-ledger/internal/config"
	"service-ledger/internal/events"
)

func Build(cfg config.NormalizedConfig, records []events.Event) Report {
	grouped := map[string]*ServiceSummary{}
	for _, event := range events.Dedupe(records) {
		service := event.Service
		rule := cfg.Services[service]
		if grouped[service] == nil {
			grouped[service] = &ServiceSummary{
				Service: service,
				Tier:    rule.Tier,
				Metrics: map[string]MetricSummary{},
			}
		}
		row := grouped[service]
		row.EventCount++
		metric := row.Metrics[event.Metric]
		metric.Count++
		metric.Sum += event.Value
		metric.Avg = metric.Sum
		if metric.Count == 1 || event.Value < metric.Min {
			metric.Min = event.Value
		}
		if event.Value > metric.Max {
			metric.Max = event.Value
		}
		row.Metrics[event.Metric] = metric
	}
	out := Report{}
	for _, row := range grouped {
		out.Services = append(out.Services, *row)
		out.Totals.EventCount += row.EventCount
	}
	out.Totals.ServiceCount = len(out.Services)
	return out
}
