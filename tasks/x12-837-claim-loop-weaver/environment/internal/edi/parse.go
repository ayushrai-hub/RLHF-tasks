package edi

func ElementSeparator(_ string) byte {
	return '*'
}

func ComponentSeparator(isa string) byte {
	d := ReadISA(isa)
	return d.Component
}
