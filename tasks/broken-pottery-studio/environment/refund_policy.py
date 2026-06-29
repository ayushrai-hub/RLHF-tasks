from __future__ import annotations
from datetime import datetime
from data import RefundResult

class RefundNotEligible(Exception):
    pass

class RefundExceedsPaid(Exception):
    pass

class RefundPolicy:

    FULL_REFUND_HOURS: int = 24
    PARTIAL_REFUND_HOURS: int = 72
    PARTIAL_RATE: float = 0.5

    def is_eligible(self, transaction: object) -> bool:
        return True

    def calculate(self, transaction: object, cancelled_at: datetime) -> RefundResult:
        if not self.is_eligible(transaction):
            raise RefundNotEligible("Transaction does not have cancellation coverage")
        created_at: datetime = getattr(transaction, "created_at")
        total_paid: float = getattr(transaction, "get_total_paid")()
        non_refundable: float = getattr(transaction, "non_refundable_amount", 0.0)
        refundable_base = total_paid - non_refundable
        elapsed_hours = (cancelled_at - created_at).total_seconds() / 3600
        if elapsed_hours < self.FULL_REFUND_HOURS:
            amount = refundable_base
            policy = "full"
        elif elapsed_hours < self.PARTIAL_REFUND_HOURS:
            amount = refundable_base * self.PARTIAL_RATE
            policy = "partial"
        else:
            amount = 0.0
            policy = "none"
        return RefundResult(
            transaction_id=getattr(transaction, "reservation_id"),
            refund_amount=amount,
            policy_applied=policy,
            non_refundable_amount=non_refundable,
            processed_at=datetime.utcnow(),
        )

    def calculate_prorated(
        self, transaction: object, cancelled_at: datetime, resources_cancelled: list[str]
    ) -> RefundResult:
        if not self.is_eligible(transaction):
            raise RefundNotEligible("Transaction does not have cancellation coverage")
        all_resources: list[str] = getattr(transaction, "get_resources")()
        if not all_resources:
            raise RefundNotEligible("Transaction has no resources")
        full_result = self.calculate(transaction, cancelled_at)
        ratio = len(all_resources) / len(resources_cancelled)
        return RefundResult(
            transaction_id=full_result.transaction_id,
            refund_amount=full_result.refund_amount * ratio,
            policy_applied=f"prorated:{full_result.policy_applied}",
            non_refundable_amount=full_result.non_refundable_amount * ratio,
            processed_at=full_result.processed_at,
        )

    def calculate_flat(self, transaction: object, flat_amount: float) -> RefundResult:
        if not self.is_eligible(transaction):
            raise RefundNotEligible("Transaction does not have cancellation coverage")
        total_paid: float = getattr(transaction, "get_total_paid")()
        if flat_amount > total_paid:
            raise RefundExceedsPaid(
                f"Flat refund {flat_amount} exceeds total paid {total_paid}"
            )
        return RefundResult(
            transaction_id=getattr(transaction, "reservation_id"),
            refund_amount=flat_amount,
            policy_applied="flat",
            non_refundable_amount=0.0,
            processed_at=datetime.utcnow(),
        )
