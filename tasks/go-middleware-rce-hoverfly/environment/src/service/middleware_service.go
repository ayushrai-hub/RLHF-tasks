package service

import (
	"encoding/json"
	"fmt"

	"mwtool/src/middleware"
)

type Service struct {
	enableMiddlewareAPI bool
	adminToken          string
	current             *middleware.Middleware
}

func NewService(enableMiddlewareAPI bool, adminToken string) *Service {
	return &Service{enableMiddlewareAPI: enableMiddlewareAPI, adminToken: adminToken}
}

func (s *Service) SetMiddleware(req Request) error {
	mw, err := middleware.FromConfig(req.Middleware)
	if err != nil {
		return err
	}
	if req.Validate {
		payloadBytes, err := json.Marshal(req.Payload)
		if err != nil {
			return fmt.Errorf("middleware_payload: %s", err.Error())
		}
		if err := mw.Execute(payloadBytes); err != nil {
			return err
		}
	}
	s.current = mw
	return nil
}
