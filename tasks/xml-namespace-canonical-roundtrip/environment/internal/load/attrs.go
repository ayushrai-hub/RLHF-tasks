package load

import (
	"encoding/xml"

	"nsx/internal/model"
)

func Declarations(attrs []xml.Attr) []model.Binding {
	var decls []model.Binding
	for _, attr := range attrs {
		if attr.Name.Space == "" && attr.Name.Local == "xmlns" {
			decls = append(decls, model.Binding{Prefix: "", URI: attr.Value})
			continue
		}
		if attr.Name.Space == "xmlns" {
			decls = append(decls, model.Binding{Prefix: attr.Name.Local, URI: attr.Value})
		}
	}
	return decls
}

func RegularAttributes(attrs []xml.Attr, frame model.Frame) []model.Attribute {
	out := make([]model.Attribute, 0, len(attrs))
	for _, attr := range attrs {
		if attr.Name.Space == "" && attr.Name.Local == "xmlns" {
			continue
		}
		if attr.Name.Space == "xmlns" {
			continue
		}
		uri := attr.Name.Space
		if uri == "" {
			uri = frame.Lookup("")
		}
		out = append(out, model.Attribute{
			Name:  model.Name{URI: uri, Local: attr.Name.Local},
			Value: attr.Value,
		})
	}
	return out
}
