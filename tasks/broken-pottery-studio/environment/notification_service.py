from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Notification:
    notification_id: str
    recipient_id: str
    subject: str
    body: str
    sent_at: datetime
    channel: str = "email"


class NotificationService:
    def __init__(self) -> None:
        self._sent: list[Notification] = []

    def send(self, recipient_id: str, subject: str, body: str, channel: str = "email") -> Notification:
        import uuid
        n = Notification(
            notification_id=str(uuid.uuid4()),
            recipient_id=recipient_id,
            subject=subject,
            body=body,
            sent_at=datetime.utcnow(),
            channel=channel,
        )
        self._sent.append(n)
        return n

    def get_sent(self, recipient_id: str) -> list[Notification]:
        return [n for n in self._sent if n.recipient_id == recipient_id]
