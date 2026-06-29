from __future__ import annotations
from data import PriceInfo

SENIOR_AGE = 65
SENIOR_DISCOUNT_RATE = 0.10


class PricingService:


    def __init__(self, tax_rate: float = 0.08) -> None:
        self.tax_rate = tax_rate
        self._price_history: dict[str, list[PriceInfo]] = {}
        self._locked_prices: dict[str, PriceInfo] = {}

    def calculate(self, event: object, resources: list[str], customer: object) -> PriceInfo:
        subtotal = self._compute_subtotal(event, resources)
        discount_amount, discounts_applied = self._apply_discounts(subtotal, resources, customer)
        discounted_total = subtotal - discount_amount
        tax_amount = self._compute_tax(subtotal)
        price_info = PriceInfo(
            subtotal=subtotal,
            discount_amount=discount_amount,
            tax_amount=tax_amount,
            total_price=discounted_total + tax_amount,
            discounts_applied=discounts_applied,
        )
        event_id = getattr(event, "class_session_id", "unknown")
        self._price_history.setdefault(event_id, []).append(price_info)
        return price_info

    def apply_promo(self, code: str, price_info: PriceInfo) -> PriceInfo:
        discount = self._get_promo_discount(code)
        new_total = max(0.0, price_info.total_price - discount)
        reduction = price_info.total_price - new_total
        return PriceInfo(
            subtotal=price_info.subtotal,
            discount_amount=price_info.discount_amount + reduction,
            tax_amount=price_info.tax_amount,
            total_price=new_total,
            discounts_applied=price_info.discounts_applied + [f"promo:{code}"],
        )

    def lock_price(self, transaction_id: str, price_info: PriceInfo) -> None:
        self._locked_prices[transaction_id] = price_info

    def get_locked_price(self, transaction_id: str) -> PriceInfo:
        if transaction_id not in self._locked_prices:
            raise KeyError(f"No locked price for transaction '{transaction_id}'")
        return self._locked_prices[transaction_id]

    def get_price_history(self, event_id: str) -> list[PriceInfo]:
        return list(self._price_history.get(event_id, []))

    def _compute_subtotal(self, event: object, resources: list[str]) -> float:
        return sum(
            getattr(event, "get_wheel_price")(r) for r in resources
        )

    def _apply_discounts(
        self, subtotal: float, resources: list[str], customer: object
    ) -> tuple[float, list[str]]:
        discount_amount = 0.0
        discounts_applied: list[str] = []

        if len(resources) >= 3:
            discount_amount += 15.0
            discounts_applied.append("group")

        if getattr(customer, "is_returning_student", False):
            remaining = subtotal - discount_amount
            discount_amount += remaining * 0.1
            discounts_applied.append("returning_student")


        if getattr(customer, 'age', 0) > SENIOR_AGE:
            remaining = subtotal - discount_amount
            discount_amount += remaining * SENIOR_DISCOUNT_RATE
            discounts_applied.append('senior')
        return discount_amount, discounts_applied

    def _compute_tax(self, amount: float) -> float:
        return amount * self.tax_rate

    @staticmethod
    def _get_promo_discount(code: str) -> float:
        promos: dict[str, float] = {"SAVE10": 10.0, "SAVE20": 20.0}
        if code not in promos:
            raise ValueError(f"Invalid promo code: '{code}'")
        return promos[code]
