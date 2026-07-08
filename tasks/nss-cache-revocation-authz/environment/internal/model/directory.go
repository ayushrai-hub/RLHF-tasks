package model

type DirectorySnapshot struct {
	Revision   int         `json:"revision"`
	Proof      Proof       `json:"proof"`
	Principals []Principal `json:"principals"`
}

type Principal struct {
	Username   string   `json:"username"`
	SubjectID  string   `json:"subject_id"`
	Generation int      `json:"generation"`
	Groups     []string `json:"groups"`
	Active     bool     `json:"active"`
}

type Proof struct {
	Revision int    `json:"revision"`
	IssuedAt int    `json:"issued_at"`
	Nonce    string `json:"nonce"`
}
