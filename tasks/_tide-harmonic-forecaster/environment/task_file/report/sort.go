package report

import "sort"

func sortDocument(doc *Document) {
	sort.Slice(doc.Samples, func(i, j int) bool {
		if doc.Samples[i].GaugeID != doc.Samples[j].GaugeID {
			return doc.Samples[i].GaugeID < doc.Samples[j].GaugeID
		}
		return doc.Samples[i].TimeMin < doc.Samples[j].TimeMin
	})
	sort.Slice(doc.Alerts, func(i, j int) bool {
		if doc.Alerts[i].GaugeID != doc.Alerts[j].GaugeID {
			return doc.Alerts[i].GaugeID < doc.Alerts[j].GaugeID
		}
		if doc.Alerts[i].StartMin != doc.Alerts[j].StartMin {
			return doc.Alerts[i].StartMin < doc.Alerts[j].StartMin
		}
		return doc.Alerts[i].Kind < doc.Alerts[j].Kind
	})
	sort.Slice(doc.Turns, func(i, j int) bool {
		if doc.Turns[i].GaugeID != doc.Turns[j].GaugeID {
			return doc.Turns[i].GaugeID < doc.Turns[j].GaugeID
		}
		if doc.Turns[i].TimeMin != doc.Turns[j].TimeMin {
			return doc.Turns[i].TimeMin < doc.Turns[j].TimeMin
		}
		return doc.Turns[i].Kind < doc.Turns[j].Kind
	})
	sort.Slice(doc.Windows, func(i, j int) bool {
		if doc.Windows[i].Segment != doc.Windows[j].Segment {
			return doc.Windows[i].Segment < doc.Windows[j].Segment
		}
		if doc.Windows[i].StartMin != doc.Windows[j].StartMin {
			return doc.Windows[i].StartMin < doc.Windows[j].StartMin
		}
		return doc.Windows[i].GaugeID < doc.Windows[j].GaugeID
	})
	sort.Slice(doc.SelectedWindows, func(i, j int) bool {
		return doc.SelectedWindows[i].Segment < doc.SelectedWindows[j].Segment
	})
	sort.Slice(doc.RoutePlans, func(i, j int) bool {
		return doc.RoutePlans[i].RouteID < doc.RoutePlans[j].RouteID
	})
}
