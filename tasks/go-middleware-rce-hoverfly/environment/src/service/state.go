package service

func (s *Service) HasMiddleware() bool {
	return s.current != nil
}
