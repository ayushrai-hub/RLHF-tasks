package audit

import "localauthz/internal/model"

type Collector struct {
	events []model.AuditEvent
}

func NewCollector() *Collector {
	return &Collector{events: []model.AuditEvent{}}
}

func (c *Collector) Add(step int, tick int, event string, revision int, message string) {
	c.events = append(c.events, NewEvent(step, tick, event, revision, message))
}

func (c *Collector) Events() []model.AuditEvent {
	return append([]model.AuditEvent(nil), c.events...)
}
