package resources

import "localauthz/internal/model"

func Names(resources []model.Resource) []string {
	out := make([]string, 0, len(resources))
	for _, resource := range resources {
		out = append(out, resource.ID)
	}
	return out
}
