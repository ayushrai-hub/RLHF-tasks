"""Helpers for building CheckResult objects from rule evaluators."""

from __future__ import annotations

from task_audit.models import CheckResult, CheckStatus, EvaluationKind, EvidenceRef


def _result(
    item_id: int,
    section: str,
    label: str,
    status: CheckStatus,
    explanation: str,
    *,
    kind: EvaluationKind = EvaluationKind.OBJECTIVE,
    blocking: bool = False,
    evidence: list[EvidenceRef] | None = None,
    suggestion: str = "",
) -> CheckResult:
    return CheckResult(
        item_id=item_id,
        section=section,
        label=label,
        status=status,
        explanation=explanation,
        kind=kind,
        blocking=blocking,
        evidence=evidence or [],
        suggestion=suggestion,
    )


def pass_(
    item_id: int,
    section: str,
    label: str,
    explanation: str,
    *,
    kind: EvaluationKind = EvaluationKind.OBJECTIVE,
    evidence: list[EvidenceRef] | None = None,
) -> CheckResult:
    return _result(item_id, section, label, CheckStatus.PASS, explanation, kind=kind, evidence=evidence)


def fail(
    item_id: int,
    section: str,
    label: str,
    explanation: str,
    *,
    kind: EvaluationKind = EvaluationKind.OBJECTIVE,
    blocking: bool = True,
    evidence: list[EvidenceRef] | None = None,
    suggestion: str = "",
) -> CheckResult:
    return _result(
        item_id,
        section,
        label,
        CheckStatus.FAIL,
        explanation,
        kind=kind,
        blocking=blocking,
        evidence=evidence,
        suggestion=suggestion,
    )


def na(item_id: int, section: str, label: str, explanation: str) -> CheckResult:
    return _result(item_id, section, label, CheckStatus.NOT_APPLICABLE, explanation)


def unknown(
    item_id: int,
    section: str,
    label: str,
    explanation: str,
    *,
    kind: EvaluationKind = EvaluationKind.EXTERNAL,
    suggestion: str = "",
) -> CheckResult:
    return _result(
        item_id,
        section,
        label,
        CheckStatus.CANNOT_DETERMINE,
        explanation,
        kind=kind,
        suggestion=suggestion,
    )


def heuristic(
    item_id: int,
    section: str,
    label: str,
    passed: bool,
    explanation: str,
    *,
    blocking: bool = False,
    evidence: list[EvidenceRef] | None = None,
    suggestion: str = "",
) -> CheckResult:
    status = CheckStatus.PASS if passed else CheckStatus.FAIL
    return _result(
        item_id,
        section,
        label,
        status,
        explanation,
        kind=EvaluationKind.HEURISTIC,
        blocking=blocking,
        evidence=evidence,
        suggestion=suggestion,
    )
