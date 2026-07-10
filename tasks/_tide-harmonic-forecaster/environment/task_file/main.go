package main

import (
	"tideharmonic/forecast"
	"tideharmonic/model"
	"tideharmonic/planner"
	"tideharmonic/report"
)

func main() {
	input := model.MustLoad("/app/model.json", "/app/gauges.jsonl")

	engine := forecast.Engine{}
	builder := &planner.RouteBuilder{}
	writer := report.JSONWriter{}

	series := engine.BuildSeries(input)
	doc := report.Build(input, series, builder)
	writer.Write("/app/output/forecast.json", doc)
}
