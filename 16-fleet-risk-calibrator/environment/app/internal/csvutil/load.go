package csvutil

import (
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"strconv"
	"strings"

	"example.com/fleetrisk/internal/domain"
	"example.com/fleetrisk/internal/timeutil"
)

func LoadServiceCalls(path string) ([]domain.ServiceCall, error) {
	rows, err := readRows(path)
	if err != nil {
		return nil, err
	}
	calls := make([]domain.ServiceCall, 0, len(rows))
	for i, row := range rows {
		openedAt, err := timeutil.ParseRFC3339(row["opened_at"])
		if err != nil {
			return nil, fmt.Errorf("%s row %d: %w", path, i+2, err)
		}
		hours, err := parseFloat(row["technician_hours"])
		if err != nil {
			return nil, fmt.Errorf("%s row %d technician_hours: %w", path, i+2, err)
		}
		calls = append(calls, domain.ServiceCall{
			RequestID:       row["request_id"],
			AssetID:         row["asset_id"],
			AssetType:       row["asset_type"],
			Site:            row["site"],
			OpenedAt:        openedAt,
			Priority:        row["priority"],
			TechnicianHours: hours,
			NotesCode:       row["notes_code"],
		})
	}
	return calls, nil
}

func LoadSensorWindows(path string) ([]domain.SensorWindow, error) {
	rows, err := readRows(path)
	if err != nil {
		return nil, err
	}
	windows := make([]domain.SensorWindow, 0, len(rows))
	for i, row := range rows {
		windowEnd, err := timeutil.ParseRFC3339(row["window_end"])
		if err != nil {
			return nil, fmt.Errorf("%s row %d: %w", path, i+2, err)
		}
		var temp *float64
		if strings.TrimSpace(row["temp_c"]) != "" {
			value, err := parseFloat(row["temp_c"])
			if err != nil {
				return nil, fmt.Errorf("%s row %d temp_c: %w", path, i+2, err)
			}
			temp = &value
		}
		vibration, err := parseFloat(row["vibration_mm_s"])
		if err != nil {
			return nil, fmt.Errorf("%s row %d vibration_mm_s: %w", path, i+2, err)
		}
		pressure, err := parseFloat(row["pressure_kpa"])
		if err != nil {
			return nil, fmt.Errorf("%s row %d pressure_kpa: %w", path, i+2, err)
		}
		current, err := parseFloat(row["current_a"])
		if err != nil {
			return nil, fmt.Errorf("%s row %d current_a: %w", path, i+2, err)
		}
		runtimeHours, err := parseFloat(row["runtime_hours"])
		if err != nil {
			return nil, fmt.Errorf("%s row %d runtime_hours: %w", path, i+2, err)
		}
		windows = append(windows, domain.SensorWindow{
			AssetID:      row["asset_id"],
			WindowEnd:    windowEnd,
			TempC:        temp,
			VibrationMMS: vibration,
			PressureKPA:  pressure,
			CurrentA:     current,
			RuntimeHours: runtimeHours,
		})
	}
	return windows, nil
}

func LoadLabels(path string) (map[string]domain.Label, error) {
	rows, err := readRows(path)
	if err != nil {
		return nil, err
	}
	labels := make(map[string]domain.Label, len(rows))
	for i, row := range rows {
		value, err := strconv.Atoi(row["failure_within_30d"])
		if err != nil {
			return nil, fmt.Errorf("%s row %d failure_within_30d: %w", path, i+2, err)
		}
		labels[row["request_id"]] = domain.Label{
			RequestID:       row["request_id"],
			FailureWithin30: value,
		}
	}
	return labels, nil
}

func LoadHistory(path string) ([]domain.HistoryEvent, error) {
	rows, err := readRows(path)
	if err != nil {
		return nil, err
	}
	events := make([]domain.HistoryEvent, 0, len(rows))
	for i, row := range rows {
		eventTime, err := timeutil.ParseRFC3339(row["event_time"])
		if err != nil {
			return nil, fmt.Errorf("%s row %d: %w", path, i+2, err)
		}
		severity, err := strconv.Atoi(row["severity"])
		if err != nil {
			return nil, fmt.Errorf("%s row %d severity: %w", path, i+2, err)
		}
		events = append(events, domain.HistoryEvent{
			AssetID:   row["asset_id"],
			EventTime: eventTime,
			EventType: row["event_type"],
			Severity:  severity,
		})
	}
	return events, nil
}

func LoadCapacity(path string) (map[string]domain.SiteCapacity, error) {
	rows, err := readRows(path)
	if err != nil {
		return nil, err
	}
	capacity := make(map[string]domain.SiteCapacity, len(rows))
	for i, row := range rows {
		dispatchSlots, err := strconv.Atoi(strings.TrimSpace(row["dispatch_slots"]))
		if err != nil {
			return nil, fmt.Errorf("%s row %d dispatch_slots: %w", path, i+2, err)
		}
		inspectSlots, err := strconv.Atoi(strings.TrimSpace(row["inspect_slots"]))
		if err != nil {
			return nil, fmt.Errorf("%s row %d inspect_slots: %w", path, i+2, err)
		}
		site := row["site"]
		capacity[site] = domain.SiteCapacity{
			Site:          site,
			DispatchSlots: dispatchSlots,
			InspectSlots:  inspectSlots,
		}
	}
	return capacity, nil
}

func readRows(path string) ([]map[string]string, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("open %s: %w", path, err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	reader.FieldsPerRecord = -1
	header, err := reader.Read()
	if err != nil {
		return nil, fmt.Errorf("read header %s: %w", path, err)
	}
	var rows []map[string]string
	for {
		record, err := reader.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("read %s: %w", path, err)
		}
		if len(record) != len(header) {
			return nil, fmt.Errorf("%s has row with %d fields, want %d", path, len(record), len(header))
		}
		row := make(map[string]string, len(header))
		for i, key := range header {
			row[key] = record[i]
		}
		rows = append(rows, row)
	}
	return rows, nil
}

func parseFloat(value string) (float64, error) {
	return strconv.ParseFloat(strings.TrimSpace(value), 64)
}
