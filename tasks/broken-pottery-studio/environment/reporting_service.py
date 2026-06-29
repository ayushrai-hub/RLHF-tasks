from __future__ import annotations
from dataclasses import dataclass
from datetime import date


@dataclass
class DailyReport:
    report_date: date
    total_transactions: int
    total_revenue: float
    unique_customers: int


class ReportingService:
    def __init__(self) -> None:
        self._reports: list[DailyReport] = []

    def record(self, report_date: date, total_transactions: int, total_revenue: float, unique_customers: int) -> DailyReport:
        report = DailyReport(
            report_date=report_date,
            total_transactions=total_transactions,
            total_revenue=total_revenue,
            unique_customers=unique_customers,
        )
        self._reports.append(report)
        return report

    def get(self, report_date: date) -> DailyReport | None:
        return next((r for r in self._reports if r.report_date == report_date), None)

    def summary(self) -> dict:
        if not self._reports:
            return {"total_transactions": 0, "total_revenue": 0.0}
        return {
            "total_transactions": sum(r.total_transactions for r in self._reports),
            "total_revenue": sum(r.total_revenue for r in self._reports),
        }
