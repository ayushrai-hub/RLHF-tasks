package edi

func ElementSeparator(isa string) byte {
	return ReadISA(isa).Element
}

func ComponentSeparator(isa string) byte {
	return ReadISA(isa).Component
}
