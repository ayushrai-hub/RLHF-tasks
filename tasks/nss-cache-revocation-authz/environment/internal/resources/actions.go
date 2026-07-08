package resources

import "localauthz/internal/model"

func ActionsFor(resource model.Resource) []string {
	out := make([]string, 0, len(resource.Actions))
	for action := range resource.Actions {
		out = append(out, action)
	}
	return out
}
