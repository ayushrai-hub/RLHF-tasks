package replay

type Step struct {
	Name    string
	BatchID string
	Phase   string
}

type Plan struct {
	Name  string
	Steps []Step
}

func CrashRetryPlan() Plan {
	return Plan{Name: "crash-retry", Steps: []Step{
		{Name: "initial", BatchID: "north-0001", Phase: "committed"},
		{Name: "checkpoint", BatchID: "north-0002", Phase: "committed"},
		{Name: "interrupted", BatchID: "north-0003-crash", Phase: "prepared"},
		{Name: "rerun", BatchID: "north-0003-rerun", Phase: "committed"},
	}}
}
