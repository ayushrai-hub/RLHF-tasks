package audit

import "localauthz/internal/model"

func NewEvent(step int, tick int, event string, revision int, message string) model.AuditEvent {
	return model.AuditEvent{Step: step, Tick: tick, Event: event, Revision: revision, Message: message}
}
