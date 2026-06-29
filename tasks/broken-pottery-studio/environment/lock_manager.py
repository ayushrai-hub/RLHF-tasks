from __future__ import annotations
from datetime import datetime, timedelta
from typing import Callable
from data import LeaseInfo

class ResourceAlreadyLeased(Exception):
    pass

class AcquireDebounced(Exception):
    pass

class LeaseNotFound(Exception):
    pass

class LeaseExpired(Exception):
    pass

class NotLeaseOwner(Exception):
    pass

class LockManager:

    def __init__(
        self,
        debounce_seconds: int = 30,
        time_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self._debounce_seconds = debounce_seconds
        self._time_fn = time_fn or datetime.utcnow
        self._leases: dict[str, LeaseInfo] = {}
        self._debounce: dict[tuple[str, str], datetime] = {}

    def acquire(self, resource_id: str, owner_id: str, ttl_seconds: int) -> LeaseInfo:
        now = self._time_fn()
        debounce_key = (resource_id, owner_id)
        if debounce_key in self._debounce and now < self._debounce[debounce_key]:
            raise AcquireDebounced(
                f"Owner '{owner_id}' is debounced on resource '{resource_id}'"
            )
        existing = self._leases.get(resource_id)
        if existing is not None and now <= existing.expires_at:
            self._debounce[debounce_key] = now + timedelta(seconds=self._debounce_seconds)
            raise ResourceAlreadyLeased(f"Resource '{resource_id}' is already leased")
        lease = LeaseInfo(
            resource_id=resource_id,
            owner_id=owner_id,
            acquired_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
        )
        self._leases[resource_id] = lease
        self._debounce.pop(debounce_key, None)
        return lease

    def renew(self, resource_id: str, owner_id: str) -> LeaseInfo:
        lease = self._leases.get(resource_id)
        if lease is None:
            raise LeaseNotFound(f"No lease for resource '{resource_id}'")
        if lease.owner_id != owner_id:
            raise NotLeaseOwner(f"Owner '{owner_id}' does not hold lease on '{resource_id}'")
        now = self._time_fn()
        if now > lease.expires_at:
            raise LeaseExpired(f"Lease on '{resource_id}' has expired")
        ttl = int((lease.expires_at - lease.acquired_at).total_seconds())
        renewed = LeaseInfo(
            resource_id=resource_id,
            owner_id=owner_id,
            acquired_at=lease.acquired_at,
            expires_at=now + timedelta(seconds=ttl),
            renewal_count=lease.renewal_count + 1,
        )
        self._leases[resource_id] = renewed
        return renewed

    def release(self, resource_id: str, owner_id: str) -> None:
        lease = self._leases.get(resource_id)
        if lease is None:
            raise LeaseNotFound(f"No lease for resource '{resource_id}'")
        if lease.owner_id != owner_id:
            raise NotLeaseOwner(f"Owner '{owner_id}' does not hold lease on '{resource_id}'")
        del self._leases[resource_id]

    def is_leased(self, resource_id: str) -> bool:
        lease = self._leases.get(resource_id)
        if lease is None:
            return False
        return self._time_fn() <= lease.expires_at

    def get_lease(self, resource_id: str) -> LeaseInfo | None:
        lease = self._leases.get(resource_id)
        if lease is None or self._time_fn() > lease.expires_at:
            return None
        return lease
