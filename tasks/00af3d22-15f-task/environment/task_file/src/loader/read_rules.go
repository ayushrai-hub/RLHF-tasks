package loader

import "tabsettle/model"

// ReadRules loads the hard-limit rules.
func ReadRules(path string) (model.Rules, error) {
	var r model.Rules
	if err := readJSON(path, &r); err != nil {
		return model.Rules{}, err
	}
	return r, nil
}
