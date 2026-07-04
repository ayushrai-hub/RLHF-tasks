package middleware

func (m *Middleware) Execute(payload []byte) error {
	if m.Mode == ModeRemote {
		return m.ExecuteRemote()
	}
	return m.ExecuteLocal(payload)
}
