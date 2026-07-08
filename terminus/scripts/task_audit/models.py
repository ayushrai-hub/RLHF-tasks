"""Core data models for the task audit framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT APPLICABLE"
    CANNOT_DETERMINE = "CANNOT DETERMINE"


class EvaluationKind(str, Enum):
    OBJECTIVE = "objective"
    HEURISTIC = "heuristic"
    EXTERNAL = "external"


class Verdict(str, Enum):
    APPROVED = "APPROVED"
    APPROVED_WITH_WARNINGS = "APPROVED WITH WARNINGS"
    REQUIRES_CHANGES = "REQUIRES CHANGES"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class EvidenceRef:
    path: str
    line: int | None = None

    def format(self) -> str:
        if self.line is not None:
            return f"{self.path}:{self.line}"
        return self.path


@dataclass
class CheckResult:
    item_id: int
    label: str
    section: str
    status: CheckStatus
    explanation: str
    kind: EvaluationKind = EvaluationKind.OBJECTIVE
    blocking: bool = False
    evidence: list[EvidenceRef] = field(default_factory=list)
    suggestion: str = ""

    def evidence_str(self) -> str:
        if not self.evidence:
            return "—"
        return "; ".join(e.format() for e in self.evidence)


@dataclass
class AuditReport:
    task_dir: str
    task_name: str
    is_milestone: bool
    results: list[CheckResult]
    validator_errors: list[str] = field(default_factory=list)
    validator_warnings: list[str] = field(default_factory=list)
    verdict: Verdict = Verdict.REQUIRES_CHANGES

    @property
    def counts(self) -> dict[str, int]:
        totals = {s.value: 0 for s in CheckStatus}
        for r in self.results:
            totals[r.status.value] += 1
        return totals

    def critical_issues(self) -> list[CheckResult]:
        return [r for r in self.results if r.status == CheckStatus.FAIL and r.blocking]

    def warnings(self) -> list[CheckResult]:
        return [r for r in self.results if r.status == CheckStatus.FAIL and not r.blocking]

    def cannot_determine(self) -> list[CheckResult]:
        return [r for r in self.results if r.status == CheckStatus.CANNOT_DETERMINE]
