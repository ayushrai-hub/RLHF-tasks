package load

import (
	"encoding/xml"

	"nsx/internal/model"
)

func ElementName(raw xml.Name, frame model.Frame) model.Name {
	if raw.Space != "" {
		return model.Name{URI: raw.Space, Local: raw.Local}
	}
	return model.Name{URI: frame.Lookup(""), Local: raw.Local}
}
