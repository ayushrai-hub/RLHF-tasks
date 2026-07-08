"""Task audit orchestrator — runs all registered checks read-only."""

from __future__ import annotations

from pathlib import Path

from validate_task import Severity

from task_audit.context import TaskContext
from task_audit.models import AuditReport, CheckStatus, Verdict
from task_audit.registry import CHECKBOXES, get_registry


class TaskAuditor:
    """Read-only evaluator for all 55 portal checklist items."""

    def __init__(
        self,
        task_dir: Path,
        report_path: Path | None = None,
        rubric_path: Path | None = None,
    ) -> None:
        self.task_dir = task_dir.resolve()
        self.ctx = TaskContext(task_dir, report_path=report_path, rubric_path=rubric_path)

    def run(self) -> AuditReport:
        registry = get_registry()
        results = []
        for item_id, section, label in CHECKBOXES:
            defn = registry.get(item_id)
            if defn is None:
                from task_audit.models import CheckResult, EvaluationKind

                results.append(
                    CheckResult(
                        item_id=item_id,
                        section=section,
                        label=label,
                        status=CheckStatus.CANNOT_DETERMINE,
                        explanation="No evaluator registered for this checklist item.",
                        kind=EvaluationKind.OBJECTIVE,
                    )
                )
                continue
            results.append(defn.evaluate(self.ctx))

        results.sort(key=lambda r: r.item_id)
        report = AuditReport(
            task_dir=str(self.task_dir),
            task_name=self.task_dir.name,
            is_milestone=self.ctx.is_milestone,
            results=results,
            validator_errors=[f.format() for f in self.ctx.validator_errors()],
            validator_warnings=[f.format() for f in self.ctx.validator_warnings()],
        )
        report.verdict = self._compute_verdict(report)
        return report

    def _compute_verdict(self, report: AuditReport) -> Verdict:
        critical = report.critical_issues()
        structural_errors = len(self.ctx.validator_errors())

        if structural_errors >= 3 or any(
            r.item_id in (15, 20, 40, 50) and r.status == CheckStatus.FAIL and r.blocking
            for r in report.results
        ):
            # Hard infrastructure failures
            hard_ids = {r.item_id for r in critical if r.kind.value == "objective"}
            if len(critical) >= 3 or hard_ids & {15, 20, 40, 50}:
                return Verdict.REJECTED

        if critical:
            return Verdict.REQUIRES_CHANGES

        heuristic_fails = [r for r in report.warnings()]
        cannot = report.cannot_determine()

        if heuristic_fails and not critical:
            return Verdict.APPROVED_WITH_WARNINGS

        if cannot and not critical and not heuristic_fails:
            # All objective checks pass but manual/external items remain
            objective_fails = [r for r in report.results if r.status == CheckStatus.FAIL]
            if objective_fails:
                return Verdict.REQUIRES_CHANGES
            return Verdict.APPROVED_WITH_WARNINGS

        objective_fails = [r for r in report.results if r.status == CheckStatus.FAIL]
        if objective_fails:
            return Verdict.REQUIRES_CHANGES

        return Verdict.APPROVED
