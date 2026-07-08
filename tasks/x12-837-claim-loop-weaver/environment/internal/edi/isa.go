package edi

type Delimiters struct {
	Element   byte
	Component byte
}

func ReadISA(raw string) Delimiters {
	if len(raw) < 105 {
		return Delimiters{Element: '*', Component: ':'}
	}
	return Delimiters{
		Element:   raw[3],
		Component: raw[104],
	}
}
