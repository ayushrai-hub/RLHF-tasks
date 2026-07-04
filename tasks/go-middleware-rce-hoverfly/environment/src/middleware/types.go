package middleware

type Mode string

const (
	ModeLocal  Mode = "local"
	ModeRemote Mode = "remote"
)

type Middleware struct {
	Mode       Mode
	Binary     string
	Script     string
	RemotePath string
}

type Config struct {
	Mode       string `json:"mode"`
	Binary     string `json:"binary"`
	Script     string `json:"script"`
	RemotePath string `json:"remote_path"`
}
