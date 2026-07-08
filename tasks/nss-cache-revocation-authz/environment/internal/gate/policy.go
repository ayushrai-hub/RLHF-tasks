package gate

import (
	"fmt"

	"localauthz/internal/model"
)

type Catalog map[string]map[string][]string

func BuildCatalog(resources []model.Resource) Catalog {
	catalog := Catalog{}
	for _, resource := range resources {
		catalog[resource.ID] = resource.Actions
	}
	return catalog
}

func (c Catalog) RequiredGroups(resource string, action string) ([]string, error) {
	actions, ok := c[resource]
	if !ok {
		return nil, fmt.Errorf("unknown resource %q", resource)
	}
	groups, ok := actions[action]
	if !ok {
		return nil, fmt.Errorf("unknown action %q for resource %q", action, resource)
	}
	return append([]string(nil), groups...), nil
}
