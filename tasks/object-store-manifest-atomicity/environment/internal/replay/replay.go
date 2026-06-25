package replay

import "strings"

func Describe(plan Plan) string {
	parts := make([]string, 0, len(plan.Steps))
	for _, step := range plan.Steps {
		parts = append(parts, step.Name+":"+step.BatchID+":"+step.Phase)
	}
	return strings.Join(parts, ",")
}
