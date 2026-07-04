package service

import (
	"errors"
	"strings"
)

func (s *Service) guardMiddlewareAPI(token string) error {
	if !s.enableMiddlewareAPI {
		return errors.New("middleware_api: middleware api disabled")
	}
	if !tokenMatches(token, s.adminToken) {
		return errors.New("middleware_api: invalid token")
	}
	return nil
}

func tokenMatches(provided, expected string) bool {
	return strings.EqualFold(strings.TrimSpace(provided), strings.TrimSpace(expected))
}
