package middleware

import "errors"

func FromConfig(cfg Config) (*Middleware, error) {
	if cfg.Binary == "" {
		return nil, errors.New("middleware_binary: missing binary")
	}
	if cfg.Mode != string(ModeLocal) && cfg.Mode != string(ModeRemote) {
		return nil, errors.New("middleware_config: invalid mode")
	}
	if cfg.Mode == string(ModeLocal) && cfg.Script == "" {
		return nil, errors.New("middleware_local: script required")
	}
	if cfg.Mode == string(ModeRemote) && cfg.RemotePath == "" {
		return nil, errors.New("middleware_remote: remote path required")
	}

	mw := &Middleware{
		Mode:       Mode(cfg.Mode),
		Binary:     cfg.Binary,
		Script:     cfg.Script,
		RemotePath: cfg.RemotePath,
	}
	return mw, nil
}
