from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Address:
    street: str
    city: str
    state: str
    zip: str

@dataclass
class Section:
    name: str
    capacity: int
    resource_ids: list[str]

@dataclass
class PriceInfo:
    subtotal: float
    discount_amount: float
    tax_amount: float
    total_price: float
    discounts_applied: list[str] = field(default_factory=list)

@dataclass
class StatusEntry:
    status: str
    transitioned_at: datetime
    actor_id: str

@dataclass
class CancellationResult:
    transaction_id: str
    status: str
    refund_amount: float
    waitlist_promoted: str | None = None

@dataclass
class RefundResult:
    transaction_id: str
    refund_amount: float
    policy_applied: str
    non_refundable_amount: float
    processed_at: datetime

@dataclass
class WaitlistEntry:
    customer_id: str
    event_id: str
    position: int
    loyalty_tier: str
    joined_at: datetime

@dataclass
class AuditEntry:
    entry_id: str
    event_type: str
    entity_id: str
    actor_id: str
    payload: dict
    timestamp: datetime

@dataclass
class LeaseInfo:
    resource_id: str
    owner_id: str
    acquired_at: datetime
    expires_at: datetime
    renewal_count: int = 0

@dataclass
class Page:
    items: list[object]
    page: int
    page_size: int
    total_count: int
    total_pages: int
    has_next: bool
    has_prev: bool

@dataclass
class BookingStats:
    event_id: str
    total_resources: int
    confirmed_count: int
    available_count: int
    occupancy_rate: float
    total_revenue: float
    cancellation_count: int
