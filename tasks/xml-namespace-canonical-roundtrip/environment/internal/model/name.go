package model

import "fmt"

type Name struct {
	URI   string `json:"uri"`
	Local string `json:"local"`
}

func (n Name) Key() string {
	return n.URI + "\x00" + n.Local
}

func (n Name) String() string {
	if n.URI == "" {
		return n.Local
	}
	return fmt.Sprintf("{%s}%s", n.URI, n.Local)
}
