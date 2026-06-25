package report

type Row struct {
	BatchID       string
	LogicalKey    string
	RelativePath  string
	Size          int64
	SHA256        string
	SidecarSHA256 string
}
