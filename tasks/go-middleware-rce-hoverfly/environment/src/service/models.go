package service

import "mwtool/src/middleware"

type Payload struct {
	RequestID string `json:"request_id"`
	Path      string `json:"path"`
	Method    string `json:"method"`
	Body      string `json:"body"`
}

type Request struct {
	EnableMiddlewareAPI bool             `json:"enable_middleware_api"`
	AuthToken           string           `json:"auth_token"`
	Validate            bool             `json:"validate"`
	Middleware          middleware.Config `json:"middleware"`
	Payload             Payload          `json:"payload"`
}
