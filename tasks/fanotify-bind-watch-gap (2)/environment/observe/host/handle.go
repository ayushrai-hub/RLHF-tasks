package host

import "os"

type Handle struct {
	Gen  int
	Path string
	File *os.File
}
