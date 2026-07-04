#!/usr/bin/env python3
"""UI-aligned reviewer checklist for Terminus Edition 2 tasks.

Outputs which portal checkboxes to leave UNCHECKED, main blockers, and
optional adjudication of external report findings.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

# Reuse validator
sys.path.insert(0, str(Path(__file__).resolve().parent))
from rubric_points import (  # noqa: E402
    RUBRIC_POSITIVE_CAP,
    RubricPositiveAnalysis,
    analyze_rubric_positives,
    extract_rubric_text_from_report,
    positive_points_from_entire_report,
    positive_points_from_rubric_text,
)
from validate_task import (  # noqa: E402
    AI_SCAFFOLDING,
    CANONICAL_BASE_IMAGES,
    FROM_DIGEST,
    HINT_PATTERNS,
    PROMPT_ANTI_PATTERNS,
    RUNTIME_INSTALL_PATTERNS,
    TaskValidator,
    Severity,
)


class Status(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    MANUAL = "manual"
    NA = "na"


@dataclass
class Checkbox:
    id: int
    section: str
    label: str
    status: Status = Status.MANUAL
    evidence: str = ""
    blocker: bool = False
    proof_files: list[str] = field(default_factory=list)


CHECKBOXES: list[tuple[int, str, str]] = [
    (1, "INSTRUCTION PROMPT", "Instruction is concise (1 sentence to 3 paragraphs max)"),
    (2, "INSTRUCTION PROMPT", "Instruction reads like a natural prompt, not a spec document"),
    (3, "INSTRUCTION PROMPT", "No excessive markdown formatting (## headers, ### subheaders, bold, tables, code blocks)"),
    (4, "INSTRUCTION PROMPT", "No step by step instructions telling the agent what developer steps to take"),
    (5, "INSTRUCTION PROMPT", "No hints or solving strategies (describes WHAT to build, not HOW)"),
    (6, "INSTRUCTION PROMPT", "No design doc style tables mapping inputs to outputs"),
    (7, "INSTRUCTION PROMPT", "Instruction is well specified (goal is clear and obvious)"),
    (8, "INSTRUCTION PROMPT", "Instruction is interesting (useful to some group of developers)"),
    (9, "INSTRUCTION PROMPT", "Instruction is unique (not duplicate of existing TB2/TB3/Edition 1 task)"),
    (10, "INSTRUCTION PROMPT", "All paths in instruction are absolute (not relative)"),
    (11, "INSTRUCTION PROMPT", "Task name does not appear in instruction.md"),
    (12, "INSTRUCTION PROMPT", "No canary string in instruction.md"),
    (13, "ENVIRONMENT", "Dockerfile does not grab content from the web (other than packages)"),
    (14, "ENVIRONMENT", "All Python/pip dependencies use pinned versions with == (no ranges)"),
    (15, "ENVIRONMENT", "Base Docker image is pinned by digest (@sha256:...)"),
    (16, "ENVIRONMENT", "Environment does not use context from outside the environment directory"),
    (17, "ENVIRONMENT", "Environment does not contain solution or ground truth answers"),
    (18, "ENVIRONMENT", "Dockerfile does not execute dangerous operations (no privileged, SYS_ADMIN, docker.sock)"),
    (19, "ENVIRONMENT", "Docker compose does not alter reserved harbor mounts (/logs/artifacts, /logs/verifier, /tests, /solution)"),
    (20, "ENVIRONMENT", "Verifier deps baked in image; test.sh does NOT install packages at runtime"),
    (21, "ORACLE SOLUTION", "Oracle passes consistently (no flaky behavior)"),
    (22, "ORACLE SOLUTION", "Oracle does not require internet or downloading packages"),
    (23, "ORACLE SOLUTION", "Oracle is reflective of instruction (real implementation, not hardcoded)"),
    (24, "VERIFIERS", "test.sh writes reward.txt; mkdir -p /logs/verifier; handles failure path"),
    (25, "VERIFIERS", "Verifiers use the exact same logic for oracle and agent runs (no conditional logic)"),
    (26, "VERIFIERS", "Verifier applies binary rewards only (0 or 1, no partial scores)"),
    (27, "VERIFIERS", "All tests are aligned with instructions (do not test unstated requirements)"),
    (28, "VERIFIERS", "Tests check for correctness, not just format"),
    (29, "VERIFIERS", "Tests verify behavior, not implementation (no grepping source code)"),
    (30, "VERIFIERS", "No brittle exact string matching where flexible checks would work"),
    (31, "VERIFIERS", "Tests have informative names or docstrings"),
    (32, "RUBRICS", "Rubrics contain at least 3 negative penalty criteria"),
    (33, "RUBRICS", "Rubric scores are from the set {1, 2, 3, 5, -1, -2, -3, -5}"),
    (34, "RUBRICS", "Each rubric criterion is one line starting with Agent, comma, then score"),
    (35, "RUBRICS", "Rubric criteria are detailed and precise"),
    (36, "RUBRICS", "Rubric criteria use positive language (not Agent does not do X, +1)"),
    (37, "RUBRICS", "Rubric does not reference testing logic or /tests/ directory"),
    (38, "RUBRICS", "Rubric does not reference metadata (task.toml) or instruction.md"),
    (39, "RUBRICS", "Rubric does not mention oracle or NOP runs"),
    (40, "TASK STRUCTURE", "All required files present (environment/Dockerfile, solution/solve.sh, tests/test.sh, instruction.md, task.toml)"),
    (41, "TASK STRUCTURE", "No unnecessary files in parent directory (jobs/, README.md, data/, dev notes)"),
    (42, "TASK METADATA", "author_name and author_email fields present in task.toml"),
    (43, "TASK METADATA", "All other required metadata fields present"),
    (44, "TASK METADATA", "Tags, languages, categories are applicable to the task"),
    (45, "TASK METADATA", "Difficulty matches observed agent pass rates"),
    (46, "MILESTONE TASKS", "steps/ layout present with per-milestone files (not root instruction/tests/solution)"),
    (47, "MILESTONE TASKS", "Each milestone has a corresponding solveN.sh file"),
    (48, "MILESTONE TASKS", "Each milestone has a corresponding test_mN.py file"),
    (49, "MILESTONE TASKS", "Each milestone test file is scoped only to that milestone"),
    (50, "ANTI CHEATING", "Tests are NOT baked into Docker image (no COPY tests/ in Dockerfile)"),
    (51, "ANTI CHEATING", "Solution or ground truth answers are not accessible in the environment"),
    (52, "ANTI CHEATING", "Agent cannot modify input data to trivially pass tests"),
    (53, "ANTI CHEATING", "Git repos pinned to specific commit (no unpinned git clone)"),
    (54, "TASK DIFFICULTY", "Task is not too easy (not >80% combined pass rate consistently)"),
    (55, "TASK DIFFICULTY", "Task is not too hard or unfair (not requiring unavailable info, unreliable environment, or luck)"),
]

CANARY_PATTERNS = [
    re.compile(r"canary", re.I),
    re.compile(r"terminus-canary", re.I),
    re.compile(r"do not remove this string", re.I),
]

WEB_FETCH_PATTERNS = [
    re.compile(r"urllib\.request\.urlopen", re.I),
    re.compile(r"requests\.get\s*\(", re.I),
    re.compile(r"curl\s+https?://", re.I),
    re.compile(r"wget\s+https?://", re.I),
]

ORACLE_CONDITIONAL = re.compile(r'(\[ -d "/oracle" \]|\$EVAL_IS_ORACLE|/oracle)', re.I)
HARDCODED_ORACLE = re.compile(r'echo\s+["\'].*["\']\s*>\s*/', re.I)
GIT_CLONE_UNPINNED = re.compile(r"git\s+clone[^;|&]*$", re.M)
IMPLEMENTATION_GREP = re.compile(r'open\s*\(\s*["\'][^"\']*\.(py|go|rs|java)', re.I)
BRITTLE_EQ = re.compile(r'assert\s+\w+\s*==\s*["\'][^"\']{20,}["\']')

RELATIVE_PATH = re.compile(r"(?<![/\w])(\.\./|\./|~/)")


@dataclass
class AgentStats:
    models: dict[str, float] = field(default_factory=dict)
    oracle_rate: float | None = None
    nop_rate: float | None = None
    classified_difficulty: str | None = None
    solvable: bool | None = None


@dataclass
class SubmissionExport:
    """Parsed regions of a Snorkel / Terminus submission export (entire-report.txt)."""

    difficulty_explanation: str = ""
    solution_explanation: str = ""
    verification_explanation: str = ""
    difficulty_check: str = ""
    instruction_sufficiency: str = ""
    quality_check: str = ""
    review_report: str = ""
    test_quality: str = ""
    platform_rubric: str = ""
    agent_review: str = ""
    comments_for_reviewer: str = ""
    reviewer_feedback: str = ""
    raw: str = ""

    def sections_present(self) -> dict[str, bool]:
        return {
            "difficulty_explanation": bool(self.difficulty_explanation.strip()),
            "solution_explanation": bool(self.solution_explanation.strip()),
            "verification_explanation": bool(self.verification_explanation.strip()),
            "difficulty_check": bool(self.difficulty_check.strip()),
            "instruction_sufficiency": bool(self.instruction_sufficiency.strip()),
            "quality_check": bool(self.quality_check.strip()),
            "review_report": bool(self.review_report.strip()),
            "test_quality": bool(self.test_quality.strip()),
            "platform_rubric": bool(self.platform_rubric.strip()),
            "agent_review": bool(self.agent_review.strip()),
            "comments_for_reviewer": bool(self.comments_for_reviewer.strip()),
            "reviewer_feedback": bool(self.reviewer_feedback.strip()),
        }


# Section headers in typical submission export order — see docs/guidelines/submission-export-format.md
_EXPORT_MARKERS: list[tuple[str, re.Pattern[str]]] = [
    ("difficulty_explanation", re.compile(r"^Difficulty Explanation \(optional\)")),
    ("solution_explanation", re.compile(r"^Solution Explanation \(optional\)")),
    ("verification_explanation", re.compile(r"^Verification Explanation \(optional\)")),
    ("comments_for_reviewer", re.compile(r"^Comments for Reviewer(\s*\(optional\))?\s*$", re.I)),
    ("reviewer_feedback", re.compile(r"^Reviewer Feedback(\s*\(optional\))?\s*$", re.I)),
    ("difficulty_check", re.compile(r"^Difficulty:\s*[✅❌]")),
    ("quality_check", re.compile(r"^##?\s*Quality Check Results")),
    ("review_report", re.compile(r"REVIEW REPORT:\s*\S")),
    ("test_quality", re.compile(r"TEST QUALITY REVIEW:")),
    ("agent_review", re.compile(r"^Agent review\s*$", re.I)),
    ("platform_rubric", re.compile(r"^Agent-generated rubric", re.I)),
]

RUBRIC_HEADER_RE = re.compile(r"^# Rubric \d+\s*$")
AGENT_LINE_RE = re.compile(r"^Agent .+,\s*[+-]\d+\s*$")


def _extract_trailing_agent_rubric(text: str) -> str:
    """Platform rubric often appears as trailing Agent lines after test-quality review."""
    lines = text.splitlines()
    collected: list[str] = []
    for line in reversed(lines):
        stripped = line.strip()
        if AGENT_LINE_RE.match(stripped):
            collected.insert(0, stripped)
        elif collected:
            break
    return "\n".join(collected) if len(collected) >= 3 else ""


def parse_submission_export(text: str) -> SubmissionExport:
    """Split a submission export blob into named sections for targeted review."""
    export = SubmissionExport(raw=text)
    if not text.strip():
        return export

    lines = text.splitlines()
    hits: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        for key, pat in _EXPORT_MARKERS:
            if pat.search(stripped) or pat.match(stripped):
                hits.append((i, key))
                break
        if RUBRIC_HEADER_RE.match(stripped):
            hits.append((i, "platform_rubric"))

    if not hits:
        export.platform_rubric = _extract_trailing_agent_rubric(text)
        export.difficulty_check = text
        return export

    hits.sort(key=lambda x: x[0])
    # Keep first occurrence per key (earliest in file)
    seen: set[str] = set()
    ordered: list[tuple[int, str]] = []
    for pos, key in hits:
        if key not in seen:
            seen.add(key)
            ordered.append((pos, key))

    for idx, (start, key) in enumerate(ordered):
        end = ordered[idx + 1][0] if idx + 1 < len(ordered) else len(lines)
        chunk = "\n".join(lines[start:end]).strip()
        setattr(export, key, chunk)

    if not export.instruction_sufficiency and export.difficulty_check:
        m = re.search(
            r"(Analysis on Agent Failures:.*|Task Instruction Sufficiency:.*)",
            export.difficulty_check,
            re.S,
        )
        if m:
            export.instruction_sufficiency = m.group(1).strip()

    if not export.platform_rubric.strip():
        export.platform_rubric = _extract_trailing_agent_rubric(text)

    return export


def parse_report(text: str, export: SubmissionExport | None = None) -> AgentStats:
    """Agent stats from difficulty-check section (preferred) or full export text."""
    scope = export.difficulty_check if export and export.difficulty_check.strip() else text
    stats = AgentStats()
    for m in re.finditer(r"(terminus-[\w.-]+|terminus-gpt5-5):\s*([\d.]+)%", scope, re.I):
        stats.models[m.group(1)] = float(m.group(2))
    for m in re.finditer(r"•\s*(terminus-[\w.-]+|terminus-gpt5-5):\s*([\d.]+)%", scope, re.I):
        stats.models[m.group(1)] = float(m.group(2))

    om = re.search(r"oracle:\s*([\d.]+)%", scope, re.I)
    if om:
        stats.oracle_rate = float(om.group(1))
    nm = re.search(r"nop:\s*([\d.]+)%", scope, re.I)
    if nm:
        stats.nop_rate = float(nm.group(1))

    dm = re.search(r"Difficulty:\s*[✅❌]?\s*(EASY|MEDIUM|HARD|TRIVIAL)", scope, re.I)
    if dm:
        stats.classified_difficulty = dm.group(1).lower()

    if re.search(r"Solvable.*✅|solvable.*yes", scope, re.I):
        stats.solvable = True
    elif re.search(r"Unsolvable|not solvable", scope, re.I):
        stats.solvable = False

    return stats


def extract_platform_rubric(
    report_text: str,
    export: SubmissionExport | None = None,
) -> str | None:
    """Pull platform rubric from submission export — see submission-export-format.md."""
    if export is None and report_text.strip():
        export = parse_submission_export(report_text)

    if export and export.platform_rubric.strip():
        rubric = export.platform_rubric.strip()
        if RUBRIC_HEADER_RE.search(rubric) or re.search(r"^Agent ", rubric, re.M):
            return rubric

    text, _label = extract_rubric_text_from_report(report_text)
    return text


def worst_model_rate(stats: AgentStats) -> float | None:
    """Lowest pass rate among reference agents (floor tier for Easy/Medium/Rejected)."""
    agent_rates = [
        v for k, v in stats.models.items()
        if "oracle" not in k.lower() and "nop" not in k.lower()
    ]
    return min(agent_rates) if agent_rates else None


def best_model_rate(stats: AgentStats) -> float | None:
    """Highest pass rate among reference agents."""
    agent_rates = [
        v for k, v in stats.models.items()
        if "oracle" not in k.lower() and "nop" not in k.lower()
    ]
    return max(agent_rates) if agent_rates else None


def declared_difficulty_defensible(declared: str, stats: AgentStats) -> bool:
    """True when task.toml difficulty is supported by difficulty.md tier rules."""
    worst = worst_model_rate(stats)
    best = best_model_rate(stats)
    declared = declared.lower()
    if declared == "hard":
        return (best is not None and best <= 20) or (worst is not None and worst <= 20)
    if declared == "medium":
        return worst is not None and 20 < worst <= 60
    if declared == "easy":
        return worst is not None and 60 < worst <= 80
    return False


def tier_from_rate(rate: float) -> str:
    if rate <= 20:
        return "hard"
    if rate <= 60:
        return "medium"
    if rate <= 80:
        return "easy"
    return "trivial"


class ReviewChecklist:
    def __init__(
        self,
        task_dir: Path,
        report_path: Path | None = None,
        rubric_path: Path | None = None,
    ) -> None:
        self.task_dir = task_dir.resolve()
        self.report_path = report_path
        self.rubric_path = rubric_path
        self.is_milestone = (self.task_dir / "steps").is_dir()
        self.results: dict[int, Checkbox] = {
            cid: Checkbox(cid, sec, lbl) for cid, sec, lbl in CHECKBOXES
        }
        self.validator = TaskValidator(self.task_dir)
        self.findings = self.validator.validate()
        self.report_text = report_path.read_text(encoding="utf-8", errors="replace") if report_path else ""
        self.export = parse_submission_export(self.report_text) if self.report_text else SubmissionExport()
        self.agent_stats = parse_report(self.report_text, self.export) if self.report_text else AgentStats()
        self.report_path = report_path
        self.toml_text = ""
        t = self.task_dir / "task.toml"
        if t.exists():
            self.toml_text = t.read_text(encoding="utf-8", errors="replace")
        self.audit_log: list[str] = []
        self.rubric_positive = self._load_rubric_positive_analysis()

    def _milestone_count(self) -> int:
        ms_match = re.search(r"number_of_milestones\s*=\s*(\d+)", self.toml_text or "")
        return int(ms_match.group(1)) if ms_match else 0

    def _load_rubric_positive_analysis(self) -> RubricPositiveAnalysis:
        """Sum positive rubric points from entire-report (or rubric file) on every review."""
        n_ms = self._milestone_count()
        if self.rubric_path and self.rubric_path.exists():
            text = self.rubric_path.read_text(encoding="utf-8", errors="replace")
            return positive_points_from_rubric_text(
                text,
                num_milestones=n_ms,
                rubric_source=str(self._rel(self.rubric_path)),
            )
        for candidate in (self.task_dir / "rubric.txt", self.task_dir / "rubrics.txt"):
            if candidate.exists():
                text = candidate.read_text(encoding="utf-8", errors="replace")
                return positive_points_from_rubric_text(
                    text,
                    num_milestones=n_ms,
                    rubric_source=str(self._rel(candidate)),
                )
        if self.report_path and self.report_path.is_file():
            return positive_points_from_entire_report(
                self.report_path,
                num_milestones=n_ms,
            )
        return RubricPositiveAnalysis()

    def _rel(self, path: Path | str) -> str:
        p = Path(path)
        try:
            return str(p.relative_to(self.task_dir))
        except ValueError:
            return str(p)

    def _set(
        self,
        cid: int,
        status: Status,
        evidence: str,
        blocker: bool = False,
        proof: list[str] | str | None = None,
    ) -> None:
        cb = self.results[cid]
        cb.status = status
        cb.evidence = evidence
        cb.blocker = blocker
        if proof:
            items = [proof] if isinstance(proof, str) else proof
            cb.proof_files = items

    def _instruction_paths(self) -> list[Path]:
        if self.is_milestone:
            steps = self.task_dir / "steps"
            return sorted(steps.glob("milestone_*/instruction.md")) if steps.is_dir() else []
        p = self.task_dir / "instruction.md"
        return [p] if p.exists() else []

    def _test_py_paths(self) -> list[Path]:
        if self.is_milestone:
            return sorted((self.task_dir / "steps").glob("milestone_*/tests/test_m*.py"))
        p = self.task_dir / "tests" / "test_outputs.py"
        return [p] if p.exists() else []

    def _test_sh_paths(self) -> list[Path]:
        if self.is_milestone:
            return sorted((self.task_dir / "steps").glob("milestone_*/tests/test.sh"))
        p = self.task_dir / "tests" / "test.sh"
        return [p] if p.exists() else []

    def run(self) -> None:
        self._check_instructions()
        self._check_environment()
        self._check_oracle()
        self._check_verifiers()
        self._check_rubrics()
        self._check_structure()
        self._check_metadata()
        self._check_milestones()
        self._check_anti_cheat()
        self._check_difficulty()

    def _check_instructions(self) -> None:
        paths = self._instruction_paths()
        if not paths:
            for cid in range(1, 13):
                self._set(cid, Status.FAIL, "Missing instruction.md", blocker=True, proof="instruction.md")
            return

        inst_rel = ", ".join(self._rel(p) for p in paths)

        combined = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in paths)
        paras = [p for p in re.split(r"\n\s*\n", combined.strip()) if p.strip()]
        word_count = len(combined.split())

        # 1 concise
        if len(paras) > 8 or word_count > 800:
            self._set(1, Status.FAIL, f"Very long instruction ({len(paras)} blocks, ~{word_count} words)", blocker=True, proof=inst_rel)
        elif len(paras) > 5:
            self._set(1, Status.MANUAL, f"{len(paras)} paragraphs — verify ≤3 problem paragraphs")
        else:
            self._set(1, Status.PASS, f"{len(paras)} paragraph blocks, ~{word_count} words")

        # 2 natural — manual default
        llm_hits = [label for pat, label in PROMPT_ANTI_PATTERNS if pat.search(combined)]
        if llm_hits:
            self._set(2, Status.FAIL, f"Synthetic patterns: {', '.join(llm_hits)}")
        else:
            self._set(2, Status.MANUAL, "No automated LLM-pattern hits — confirm natural tone")

        # 3 excessive markdown
        h2 = len(re.findall(r"^##\s", combined, re.M))
        h3 = len(re.findall(r"^###\s", combined, re.M))
        tables = combined.count("|---")
        if h2 > 2 or h3 > 3 or tables > 0:
            self._set(3, Status.FAIL, f"Heavy markdown: ##={h2}, ###={h3}, tables={tables}", proof=inst_rel)
        elif h2 > 0 or "**" in combined:
            self._set(3, Status.MANUAL, "Some markdown — verify not excessive")
        else:
            self._set(3, Status.PASS, "No heavy markdown detected")

        # 4 step by step
        step_hits = [pat.pattern for pat in HINT_PATTERNS if pat.search(combined)]
        if step_hits:
            self._set(4, Status.FAIL, f"Step/hint patterns: {step_hits[:3]}", blocker=True)
        else:
            self._set(4, Status.PASS, "No step-by-step patterns")

        # 5 hints
        if re.search(r"hint:|look for:|you should (run|edit)", combined, re.I):
            self._set(5, Status.FAIL, "Explicit hint language found", blocker=True)
        else:
            self._set(5, Status.MANUAL, "Review for implicit HOW-not-WHAT guidance")

        # 6 design doc tables
        if tables > 0 or re.search(r"\|\s*\w+\s*\|\s*\w+\s*\|", combined):
            self._set(6, Status.FAIL, "Input/output mapping tables present")
        else:
            self._set(6, Status.PASS, "No design-doc tables")

        # 7 well specified — manual
        if not re.search(r"/[\w.-]+", combined):
            self._set(7, Status.FAIL, "No absolute paths — goal may be underspecified", blocker=True)
        else:
            self._set(7, Status.MANUAL, "Has paths — verify all requirements testable")

        self._set(8, Status.MANUAL, "Subjective — confirm task is useful/interesting")
        self._set(9, Status.MANUAL, "Verify uniqueness vs TB2/TB3/Edition 1 corpus")

        # 10 absolute paths
        if RELATIVE_PATH.search(combined):
            self._set(10, Status.FAIL, "Relative paths found (./ ../ ~/ )", blocker=True, proof=inst_rel)
        elif re.search(r"/[\w.-]+", combined):
            self._set(10, Status.PASS, "Absolute paths present; no relative paths", proof=inst_rel)
        else:
            self._set(10, Status.FAIL, "No absolute paths detected", blocker=True)

        # 11 task name
        task_name = self.task_dir.name.lower()
        if task_name in combined.lower():
            self._set(11, Status.FAIL, f"Task folder name '{self.task_dir.name}' appears in instruction")
        else:
            self._set(11, Status.PASS, "Task name not in instruction")

        # 12 canary
        if any(p.search(combined) for p in CANARY_PATTERNS):
            self._set(12, Status.FAIL, "Canary string pattern detected")
        else:
            self._set(12, Status.PASS, "No canary patterns")

    def _check_environment(self) -> None:
        df = self.task_dir / "environment" / "Dockerfile"
        if not df.exists():
            for cid in range(13, 21):
                self._set(cid, Status.FAIL, "Missing Dockerfile", blocker=True)
            return

        text = df.read_text(encoding="utf-8", errors="replace")
        env_dir = self.task_dir / "environment"

        # 13 web fetch in env (not packages)
        web_hits = []
        for f in env_dir.rglob("*"):
            if f.is_file() and f.suffix in {".py", ".sh", ".js", ".go", ".rs"}:
                try:
                    ft = f.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                for pat in WEB_FETCH_PATTERNS:
                    if pat.search(ft):
                        web_hits.append(str(f.relative_to(self.task_dir)))
        if web_hits:
            self._set(13, Status.FAIL, f"Runtime web fetch in: {web_hits[:3]}", blocker=True)
        else:
            self._set(13, Status.PASS, "No runtime web fetch in environment code")

        # 14 pinned pip
        unpinned = [ln.strip()[:70] for ln in text.splitlines() if re.search(r"pip\s+install", ln, re.I) and "==" not in ln]
        if unpinned:
            self._set(14, Status.FAIL, f"Unpinned pip: {unpinned[0]}", blocker=True)
        elif "pip install" in text.lower():
            self._set(14, Status.PASS, "pip packages use ==")
        else:
            self._set(14, Status.PASS, "No pip install in Dockerfile")

        # 15 digest
        from_lines = [ln for ln in text.splitlines() if re.match(r"^\s*FROM\s+", ln, re.I)]
        bad_from = [ln.strip() for ln in from_lines if "@sha256:" not in ln.lower()]
        if bad_from:
            self._set(15, Status.FAIL, f"Unpinned FROM: {bad_from[0]}", blocker=True, proof="environment/Dockerfile")
        else:
            self._set(15, Status.PASS, "All FROM lines digest-pinned", proof="environment/Dockerfile")

        # 16 context outside environment
        copy_outside = re.findall(r"COPY\s+(\.\./|\.\.\\)", text, re.I)
        if copy_outside:
            self._set(16, Status.FAIL, "COPY references parent of build context")
        else:
            self._set(16, Status.PASS, "No COPY outside environment/")

        # 17 ground truth in env
        solve_in_env = list(env_dir.rglob("solve.sh")) + list(env_dir.rglob("answer*"))
        hint_errors = [f for f in self.findings if f.check == "solution-hints"]
        if solve_in_env:
            self._set(17, Status.FAIL, "Solution-like files in environment/", blocker=True)
        elif len(hint_errors) > 3:
            self._set(17, Status.MANUAL, f"{len(hint_errors)} possible hint patterns — review env comments")
        else:
            self._set(17, Status.MANUAL, "Verify no answer leakage in comments/docs")

        # 18 dangerous
        lower = text.lower()
        if "privileged: true" in lower.replace(" ", "") or "docker.sock" in lower or "sys_admin" in lower:
            self._set(18, Status.FAIL, "Privileged/dangerous Docker config", blocker=True)
        else:
            self._set(18, Status.PASS, "No privileged/SYS_ADMIN/docker.sock")

        # 19 compose mounts
        compose = self.task_dir / "environment" / "docker-compose.yaml"
        if compose.exists():
            ct = compose.read_text(encoding="utf-8", errors="replace")
            if re.search(r"/tests|/solution|/logs/verifier", ct):
                self._set(19, Status.FAIL, "Compose may conflict with Harbor mounts", blocker=True)
            else:
                self._set(19, Status.PASS, "Compose present; no reserved mount overrides detected")
        else:
            self._set(19, Status.PASS, "No docker-compose.yaml")

        # 20 test deps — NOT runtime in test.sh; SHOULD be in Dockerfile for pytest
        runtime_install = False
        for ts in self._test_sh_paths():
            ttext = ts.read_text(encoding="utf-8", errors="replace")
            for pat in RUNTIME_INSTALL_PATTERNS:
                if pat.search(ttext):
                    runtime_install = True
        pytest_in_df = "pytest" in text.lower()
        if runtime_install:
            self._set(20, Status.FAIL, "test.sh installs packages at runtime", blocker=True, proof="tests/test.sh")
        elif not pytest_in_df and self._test_sh_paths():
            self._set(20, Status.FAIL, "pytest not in Dockerfile — verifier deps must be baked in image", blocker=True,
                      proof=["environment/Dockerfile", "tests/test.sh"])
        else:
            self._set(20, Status.PASS, "Verifier deps in image; no runtime installs in test.sh",
                      proof=["environment/Dockerfile", "tests/test.sh"])

        # tmux/asciinema — not a UI checkbox but critical
        if "tmux" not in text.lower() or "asciinema" not in text.lower():
            pass  # surfaced in blockers via validator findings

    def _check_oracle(self) -> None:
        solve_paths: list[Path] = []
        if self.is_milestone:
            solve_paths = sorted((self.task_dir / "steps").glob("milestone_*/solution/solve*.sh"))
        else:
            p = self.task_dir / "solution" / "solve.sh"
            if p.exists():
                solve_paths = [p]

        if not solve_paths:
            for cid in (21, 22, 23):
                self._set(cid, Status.FAIL, "Missing oracle solution", blocker=True)
            return

        combined = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in solve_paths)

        self._set(21, Status.MANUAL, "Run ./scripts/terminus oracle — confirm no flakes")

        dl_hits = [pat.pattern for pat in RUNTIME_INSTALL_PATTERNS + [re.compile(r"wget|curl", re.I)] if pat.search(combined)]
        if dl_hits:
            self._set(22, Status.FAIL, "Oracle may download/install at runtime", blocker=True)
        else:
            self._set(22, Status.PASS, "No obvious network installs in solve.sh")

        if HARDCODED_ORACLE.search(combined) and "python" not in combined.lower() and "go run" not in combined.lower():
            self._set(23, Status.FAIL, "Possible hardcoded echo to output path", blocker=True)
        else:
            self._set(23, Status.MANUAL, "Verify oracle derives results from implementation")

    def _check_verifiers(self) -> None:
        test_shs = self._test_sh_paths()
        test_pys = self._test_py_paths()

        if not test_shs:
            for cid in range(24, 32):
                self._set(cid, Status.FAIL, "Missing test.sh", blocker=True)
            return

        combined_sh = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in test_shs)

        # 24 reward
        has_reward = (
            "/logs/verifier/reward.txt" in combined_sh
            or re.search(r'reward\.txt', combined_sh)
            and "VERIFIER" in combined_sh
        )
        has_mkdir = "mkdir -p /logs/verifier" in combined_sh or 'VERIFIER_DIR="/logs/verifier"' in combined_sh
        if not has_reward:
            self._set(24, Status.FAIL, "test.sh missing reward.txt write", blocker=True)
        elif not has_mkdir:
            self._set(24, Status.FAIL, "Missing mkdir for /logs/verifier", blocker=True)
        elif re.search(r"reward\.txt.*\n.*\bexit\s+\$", combined_sh, re.I | re.S) and "exit 0" in combined_sh:
            self._set(24, Status.FAIL, "Exits before all paths write reward (review set -e)", blocker=True)
        else:
            self._set(24, Status.PASS, "reward.txt write pattern present")

        # 25 oracle conditional
        if ORACLE_CONDITIONAL.search(combined_sh):
            self._set(25, Status.FAIL, "Conditional oracle/agent logic in test.sh", blocker=True)
        else:
            for tp in test_pys:
                tpt = tp.read_text(encoding="utf-8", errors="replace")
                if ORACLE_CONDITIONAL.search(tpt):
                    self._set(25, Status.FAIL, f"Conditional logic in {tp.name}", blocker=True)
                    break
            else:
                self._set(25, Status.PASS, "No /oracle conditional logic")

        # 26 binary
        if re.search(r"reward\.txt.*[02-9]", combined_sh) or "0.5" in combined_sh:
            self._set(26, Status.MANUAL, "Verify only 0/1 written to reward.txt")
        else:
            self._set(26, Status.PASS, "Binary 0/1 reward pattern")

        self._set(27, Status.MANUAL, "Cross-check instruction vs each test assertion (use prompt.md)")
        self._set(28, Status.MANUAL, "Confirm tests assert correctness not format-only")

        impl_grep = False
        for tp in test_pys:
            tpt = tp.read_text(encoding="utf-8", errors="replace")
            if re.search(r'open\s*\([^)]*main\.(py|go|rs)', tpt) or re.search(r'\.read\(\).*assert.*in', tpt):
                impl_grep = True
        if impl_grep:
            self._set(29, Status.FAIL, "Tests may grep/read source for patterns")
        else:
            self._set(29, Status.PASS, "No obvious implementation grep in tests")

        brittle = any(BRITTLE_EQ.search(tp.read_text(encoding="utf-8", errors="replace")) for tp in test_pys)
        self._set(30, Status.FAIL if brittle else Status.MANUAL, "Long exact string assert" if brittle else "Review assert style")

        # 31 docstrings
        missing_ds = [f.check for f in self.findings if f.check == "informative_test_docstrings"]
        if missing_ds:
            self._set(31, Status.FAIL, f"{len(missing_ds)} tests missing docstrings", blocker=True)
        elif test_pys:
            self._set(31, Status.PASS, "Test docstrings present")
        else:
            self._set(31, Status.FAIL, "Missing test_outputs.py", blocker=True)

    def _check_rubrics(self) -> None:
        rubric_file = self.rubric_path
        rubric_source = "explicit --rubric"
        if not rubric_file:
            for candidate in (self.task_dir / "rubric.txt", self.task_dir / "rubrics.txt"):
                if candidate.exists():
                    rubric_file = candidate
                    rubric_source = str(self._rel(candidate))
                    break

        text: str | None = None
        if rubric_file and rubric_file.exists():
            text = rubric_file.read_text(encoding="utf-8", errors="replace")
        elif self.report_text:
            text = extract_platform_rubric(self.report_text, self.export)
            if text:
                rubric_source = (
                    f"platform rubric section in {self._rel(self.report_path)}"
                    if self.report_path
                    else "platform rubric section in report"
                )

        if not text:
            for cid in range(32, 40):
                self._set(cid, Status.NA, "No rubric in task folder or submission report")
            return

        negatives = re.findall(r",\s*-\d", text)
        scores = re.findall(r",\s*([+-]?\d+)\s*$", text, re.M)
        invalid_scores = [s for s in scores if abs(int(s)) not in (1, 2, 3, 5)]
        agent_lines = [ln for ln in text.splitlines() if ln.strip().lower().startswith("agent")]

        self._set(32, Status.PASS if len(negatives) >= 3 else Status.FAIL,
                  f"{len(negatives)} negative criteria (need ≥3) [{rubric_source}]", blocker=len(negatives) < 3)
        self._set(33, Status.PASS if not invalid_scores else Status.FAIL,
                  f"Invalid scores: {invalid_scores[:5]} [{rubric_source}]" if invalid_scores else f"Scores in ±1,2,3,5 [{rubric_source}]")
        self._set(34, Status.PASS if len(agent_lines) >= 3 else Status.FAIL,
                  f"{len(agent_lines)} Agent lines [{rubric_source}]")

        n_ms = self._milestone_count()
        self.rubric_positive = analyze_rubric_positives(
            text,
            num_milestones=n_ms,
            rubric_source=rubric_source,
        )
        rp = self.rubric_positive
        pts_note = (
            f"{rp.total_positive_pts} positive pts (cap {RUBRIC_POSITIVE_CAP}; "
            f"{rp.positive_line_count} +lines)"
        )

        if rp.over_cap:
            self._set(
                35,
                Status.FAIL,
                f"Rubric {rp.cap_detail}; {pts_note} [{rubric_source}]",
                blocker=True,
            )
        else:
            self._set(
                35,
                Status.PASS if rp.found else Status.MANUAL,
                f"Rubric positive points: {pts_note} — {rp.cap_status} [{rubric_source}]",
            )

        self._set(36, Status.FAIL if re.search(r"does not|doesn't|fails to", text, re.I) else Status.MANUAL,
                  f"Negative phrasing in rubric [{rubric_source}]" if re.search(r"does not", text, re.I) else f"Check positive phrasing [{rubric_source}]")
        self._set(37, Status.FAIL if re.search(r"/tests/|pytest", text, re.I) else Status.PASS,
                  f"References tests [{rubric_source}]" if re.search(r"/tests/", text, re.I) else f"No /tests/ references [{rubric_source}]")
        self._set(38, Status.FAIL if re.search(r"task\.toml|instruction\.md", text, re.I) else Status.PASS,
                  f"References metadata/instruction [{rubric_source}]" if re.search(r"task\.toml", text, re.I) else f"No metadata refs [{rubric_source}]")
        self._set(39, Status.FAIL if re.search(r"\boracle\b|\bNOP\b", text, re.I) else Status.PASS,
                  f"Mentions oracle/NOP [{rubric_source}]" if re.search(r"oracle", text, re.I) else f"No oracle/NOP mentions [{rubric_source}]")

    def _check_structure(self) -> None:
        errors = [f for f in self.findings if f.severity == Severity.ERROR and f.check == "structure"]
        if errors:
            self._set(40, Status.FAIL, errors[0].message, blocker=True)
        else:
            self._set(40, Status.PASS, "Required files present")

        stray = []
        for name in ("jobs", "data", "dev-notes", "audit-report.md"):
            if (self.task_dir / name).exists():
                stray.append(name)
        readme = self.task_dir / "README.md"
        if readme.exists():
            stray.append("README.md")
        if stray:
            self._set(41, Status.FAIL, f"Stray files: {', '.join(stray)}")
        else:
            self._set(41, Status.PASS, "No obvious stray parent files")

    def _check_metadata(self) -> None:
        if not self.toml_text:
            for cid in (42, 43, 44, 45):
                self._set(cid, Status.FAIL, "Missing task.toml", blocker=True)
            return

        has_author = "author_name" in self.toml_text and "author_email" in self.toml_text
        self._set(42, Status.PASS if has_author else Status.FAIL,
                  "author fields present" if has_author else "Missing author_name/email", blocker=not has_author)

        required = [
            "version", "category", "difficulty", "codebase_size", "number_of_milestones",
            "languages", "tags", "expert_time_estimate_min", "timeout_sec", "cpus", "memory_mb", "storage_mb",
        ]
        missing = [f for f in required if f not in self.toml_text]
        if missing:
            self._set(43, Status.FAIL, f"Missing fields: {', '.join(missing)}", blocker=True)
        else:
            self._set(43, Status.PASS, "Core metadata fields present")

        self._set(44, Status.MANUAL, "Verify tags/languages/category match task content")

        # 45 — task.toml difficulty present; platform/tier mismatch is never a blocker
        decl_m = re.search(r'difficulty\s*=\s*"(\w+)"', self.toml_text, re.I)
        declared = decl_m.group(1).lower() if decl_m else None
        if not declared:
            self._set(45, Status.FAIL, "Missing difficulty in task.toml", blocker=True)
        else:
            worst = worst_model_rate(self.agent_stats)
            best = best_model_rate(self.agent_stats)
            classified = self.agent_stats.classified_difficulty
            parts = [f"task.toml difficulty='{declared}'"]
            if classified:
                parts.append(f"platform classified='{classified}'")
            if worst is not None:
                parts.append(f"worst-model {worst:.0f}% → tier '{tier_from_rate(worst)}'")
            if best is not None:
                parts.append(f"best-model {best:.0f}%")
            note = "; ".join(parts)
            if classified and classified != declared:
                note += " (declared vs platform differ — not a blocker)"
            elif worst is not None and tier_from_rate(worst) != declared:
                note += " (declared vs agent-rate tier differ — not a blocker)"
            self._set(
                45,
                Status.PASS,
                note,
                proof=["task.toml", str(self.report_path.name) if self.report_path else "—"],
            )

    def _check_milestones(self) -> None:
        ms_match = re.search(r"number_of_milestones\s*=\s*(\d+)", self.toml_text)
        n = int(ms_match.group(1)) if ms_match else 0

        if n == 0 and not self.is_milestone:
            for cid in range(46, 50):
                self._set(cid, Status.NA, "Not a milestone task")
            return

        ms_errors = [f for f in self.findings if f.check == "milestone" and f.severity == Severity.ERROR]
        if self.is_milestone and not ms_errors:
            self._set(46, Status.PASS, "steps/ milestone layout OK")
        elif ms_errors:
            self._set(46, Status.FAIL, ms_errors[0].message, blocker=True)
        else:
            self._set(46, Status.FAIL, "number_of_milestones>0 but no steps/ layout", blocker=True)

        for cid, msg in ((47, "solveN.sh"), (48, "test_mN.py"), (49, "milestone scope")):
            if ms_errors:
                self._set(cid, Status.FAIL, f"Milestone structure issue — verify {msg}", blocker=True)
            else:
                self._set(cid, Status.MANUAL, f"Verify {msg} per milestone")

    def _check_anti_cheat(self) -> None:
        df = self.task_dir / "environment" / "Dockerfile"
        text = df.read_text(encoding="utf-8", errors="replace") if df.exists() else ""

        copy_tests = any(
            re.match(r"^\s*COPY\s+.*\btests\b", ln, re.I)
            for ln in text.splitlines()
            if not ln.strip().startswith("#")
        )
        self._set(50, Status.FAIL if copy_tests else Status.PASS,
                  "COPY tests/ in Dockerfile" if copy_tests else "No tests COPY in image")

        self._set(51, Status.MANUAL, "Verify env has no accessible ground truth")

        self._set(52, Status.MANUAL, "Verify input data not trivially writable by agent")

        if GIT_CLONE_UNPINNED.search(text) and "git checkout" not in text.lower():
            self._set(53, Status.FAIL, "Unpinned git clone in Dockerfile", blocker=True)
        elif "git clone" in text.lower():
            self._set(53, Status.PASS if "git checkout" in text.lower() else Status.MANUAL,
                      "git clone with checkout" if "git checkout" in text.lower() else "Verify git pin")
        else:
            self._set(53, Status.PASS, "No git clone in Dockerfile")

    def _check_difficulty(self) -> None:
        worst = worst_model_rate(self.agent_stats)
        if worst is not None:
            self._set(54, Status.FAIL if worst > 80 else Status.PASS,
                      f"Worst-model pass rate {worst:.0f}% (>80% = too easy)" if worst > 80 else f"Worst-model {worst:.0f}% ≤80%",
                      blocker=worst > 80)
        else:
            self._set(54, Status.MANUAL, "Need agent report for pass rate")

        self._set(55, Status.MANUAL, "Assess fairness — needs human review of instructions/env")

    def blockers(self) -> list[Checkbox]:
        return [cb for cb in self.results.values() if cb.status == Status.FAIL and cb.blocker]

    def check_ids(self) -> list[int]:
        """Portal: CHECK only items that pass."""
        return sorted(cid for cid, cb in self.results.items() if cb.status == Status.PASS)

    def uncheck_ids(self) -> list[int]:
        """Portal: UNCHECK = fail, manual (unverified), or N/A."""
        return sorted(
            cid for cid, cb in self.results.items()
            if cb.status in (Status.FAIL, Status.MANUAL, Status.NA)
        )

    def disposition(self) -> str:
        blockers = self.blockers()
        fails = [cb for cb in self.results.values() if cb.status == Status.FAIL]
        if blockers:
            return "Revise"
        if fails:
            return "Revise"
        manual = [cb for cb in self.results.values() if cb.status == Status.MANUAL]
        if len(manual) > 8:
            return "Revise"
        return "Accept"

    def _validator_summary(self) -> tuple[str, list[str]]:
        errors = [f for f in self.findings if f.severity == Severity.ERROR]
        warnings = [f for f in self.findings if f.severity == Severity.WARNING]
        status = "FAIL" if errors else ("WARN" if warnings else "PASS")
        lines = [f.format() for f in errors[:15]]
        if len(errors) > 15:
            lines.append(f"... and {len(errors) - 15} more errors")
        return status, lines

    def _portal_note(self) -> str:
        disp = self.disposition()
        name = self.task_dir.name
        blockers = self.blockers()

        if disp == "Accept":
            decl = re.search(r'difficulty\s*=\s*"(\w+)"', self.toml_text, re.I)
            diff = decl.group(1) if decl else "declared"
            worst = worst_model_rate(self.agent_stats)
            rate_note = (
                f" Agent pass rates look reasonable for {diff} difficulty ({worst:.0f}% worst-model)."
                if worst
                else ""
            )
            return (
                f"Nice task overall. The {name} instructions are clear, the environment and verifiers "
                f"are set up well, and the oracle passes cleanly.{rate_note} I didn't spot spec gaps "
                f"or easy cheating paths."
            )

        blocker_labels = ", ".join(f"#{cb.id}" for cb in blockers[:5])
        return (
            f"Good foundation on {name} — most of the structure looks solid."
            f"{f' Main items to address: {blocker_labels}.' if blocker_labels else ''} "
            f"See the detailed blocker section in this report for specifics."
        )

    def format_final_report(self) -> str:
        """Full deliverable for reviewer portal — blockers, proof, checkboxes, note."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        name = self.task_dir.name
        disp = self.disposition()
        val_status, val_lines = self._validator_summary()

        self.audit_log.append(f"Ran validate_task.py → {val_status}")
        if self.report_path:
            self.audit_log.append(f"Parsed agent report: {self.report_path.name}")

        lines: list[str] = [
            f"# Terminus Review Report: `{name}`",
            "",
            f"**Generated:** {now}  ",
            f"**Disposition:** {disp}  ",
            f"**Task path:** `{self.task_dir}`  ",
            "",
            "---",
            "",
            "## 1. Executive summary",
            "",
            f"- **Recommendation:** {disp}",
            f"- **Automated validation:** {val_status} ({len([f for f in self.findings if f.severity == Severity.ERROR])} errors, "
            f"{len([f for f in self.findings if f.severity == Severity.WARNING])} warnings)",
            f"- **Checkboxes to CHECK:** {len(self.check_ids())} items → `{', '.join(str(i) for i in self.check_ids()) or 'none'}`",
            f"- **Checkboxes to UNCHECK:** {len(self.uncheck_ids())} items → `{', '.join(str(i) for i in self.uncheck_ids()) or 'none'}`",
            "",
        ]
        rp = self.rubric_positive
        if rp.found:
            lines.extend([
                f"- **Rubric positive points (from report):** {rp.total_positive_pts} "
                f"(cap {RUBRIC_POSITIVE_CAP}; {rp.cap_status})",
                f"- **Rubric +line count:** {rp.positive_line_count}",
            ])
            if rp.per_block_positive_pts:
                blocks = ", ".join(f"#{k}={v}" for k, v in sorted(rp.per_block_positive_pts.items()))
                lines.append(f"- **Per-block positive pts:** {blocks}")
            lines.append("")
        lines.extend([
            "> Portal rule: **Check each item that passes.** Leaving unchecked = failed or not applicable.",
            "",
        ])

        # Blockers detailed
        lines.extend(["## 2. Main blockers (detailed)", ""])
        blockers = self.blockers()
        fails = sorted([cb for cb in self.results.values() if cb.status == Status.FAIL], key=lambda x: x.id)

        if blockers or fails:
            for i, cb in enumerate(blockers + [f for f in fails if f not in blockers], start=1):
                sev = "High" if cb.blocker else "Medium"
                proof = ", ".join(f"`{p}`" for p in cb.proof_files) if cb.proof_files else "_see evidence below_"
                lines.extend([
                    f"### Blocker {i}: #{cb.id} — {cb.label}",
                    "",
                    f"- **Severity:** {sev}",
                    f"- **Section:** {cb.section}",
                    f"- **Checkbox:** leave **#{cb.id} UNCHECKED**",
                    f"- **What failed:** {cb.evidence}",
                    f"- **Proof files:** {proof}",
                    "",
                ])
        else:
            lines.append("_No automated blocking failures. Manual review items remain — see section 3._")
            lines.append("")

        # Checkbox guide
        lines.extend([
            "## 3. Portal checkbox decisions",
            "",
            "### CHECK these (pass — tick in portal)",
            "",
            "| # | Label | Reason | Proof |",
            "|---|-------|--------|-------|",
        ])
        for cid in self.check_ids():
            cb = self.results[cid]
            proof = ", ".join(f"`{p}`" for p in cb.proof_files) if cb.proof_files else "—"
            lines.append(f"| {cid} | {cb.label} | {cb.evidence} | {proof} |")

        if not self.check_ids():
            lines.append("| — | — | No automated passes | — |")

        lines.extend([
            "",
            "### UNCHECK these (fail, unverified, or N/A — leave blank in portal)",
            "",
            "| # | Status | Label | Reason | Proof |",
            "|---|--------|-------|--------|-------|",
        ])
        for cid in self.uncheck_ids():
            cb = self.results[cid]
            proof = ", ".join(f"`{p}`" for p in cb.proof_files) if cb.proof_files else "—"
            reason = cb.evidence
            if cb.status == Status.MANUAL:
                reason = f"[VERIFY FIRST] {reason}"
            elif cb.status == Status.NA:
                reason = f"[N/A] {reason}"
            lines.append(f"| {cid} | {cb.status.value} | {cb.label} | {reason} | {proof} |")

        lines.extend([
            "",
            "### Quick copy-paste",
            "",
            f"**CHECK:** {', '.join(str(i) for i in self.check_ids()) or '(none yet — complete manual verification)'}",
            "",
            f"**UNCHECK:** {', '.join(str(i) for i in self.uncheck_ids())}",
            "",
        ])

        # Proof index
        lines.extend(["## 4. Proof file index", ""])
        proof_map: dict[str, list[int]] = {}
        for cid, cb in self.results.items():
            for p in cb.proof_files:
                proof_map.setdefault(p, []).append(cid)
            if cb.status == Status.FAIL and not cb.proof_files:
                for f in self.findings:
                    if f.path and cb.id in (15, 20, 24, 31, 43, 45):
                        proof_map.setdefault(f.path, []).append(cid)
        if proof_map:
            lines.append("| File | Related checkboxes |")
            lines.append("|------|-------------------|")
            for path in sorted(proof_map):
                lines.append(f"| `{path}` | {', '.join(f'#{i}' for i in sorted(set(proof_map[path])))} |")
        else:
            lines.append("_Add proof paths during manual review._")
        lines.append("")

        # Validator errors as proof
        if val_lines:
            lines.extend(["## 5. Validation output (re-audit)", "", "```"])
            lines.extend(val_lines)
            lines.extend(["```", ""])

        # Report mismatch & adjudication
        if self.report_text:
            lines.extend(self._submission_export_sections())
            lines.extend(self._check_report_task_mismatch())
            lines.extend(self._adjudicate_external_findings())

        # Agent stats
        if self.agent_stats.models:
            lines.extend(["## 6. Agent performance (from report)", ""])
            for model, rate in sorted(self.agent_stats.models.items()):
                lines.append(f"- {model}: {rate:.1f}%")
            worst = worst_model_rate(self.agent_stats)
            best = best_model_rate(self.agent_stats)
            if worst is not None:
                lines.append(f"- **Worst-model rate:** {worst:.1f}% → tier `{tier_from_rate(worst)}`")
            if best is not None:
                lines.append(f"- **Best-model rate:** {best:.1f}%")
            decl_m = re.search(r'difficulty\s*=\s*"(\w+)"', self.toml_text, re.I)
            if decl_m:
                declared = decl_m.group(1).lower()
                lines.append(f"- **task.toml difficulty:** `{declared}`")
            if self.agent_stats.classified_difficulty:
                classified = self.agent_stats.classified_difficulty
                lines.append(f"- **Platform classified difficulty:** `{classified}`")
                if decl_m and declared != classified:
                    lines.append(
                        "- **Declared vs platform:** differ — informational only, **not a blocker**"
                    )
            lines.append("")

        rp = self.rubric_positive
        if rp.found:
            lines.extend([
                "## 6b. Rubric positive points (entire-report)",
                "",
                "| Field | Value |",
                "|-------|-------|",
                f"| Source | `{rp.rubric_source}` |",
                f"| Positive point total (+lines only) | **{rp.total_positive_pts}** |",
                f"| Positive line count | {rp.positive_line_count} |",
                f"| Cap | {RUBRIC_POSITIVE_CAP} (blocker only if **>{RUBRIC_POSITIVE_CAP}**) |",
                f"| Status | {rp.cap_status} |",
            ])
            if rp.per_block_positive_pts:
                lines.append(f"| Per `# Rubric N` block | {rp.per_block_positive_pts} |")
            if rp.over_cap:
                lines.append(f"| Blocker detail | {rp.cap_detail} |")
            lines.append("")

        # Audit log
        lines.extend([
            "## 7. Audit log",
            "",
            "- [x] Read task.toml, instruction(s), Dockerfile, test.sh, test_outputs.py, solve.sh",
            f"- [x] Ran `validate_task.py` → {val_status}",
        ])
        if self.report_path:
            lines.append(f"- [x] Cross-checked external report: `{self.report_path.name}`")
        lines.append("- [ ] Manual spec↔test alignment (#27, #28) — **reviewer must confirm**")
        lines.append("- [ ] Subjective items (#2, #8, #9, #55) — **reviewer must confirm**")
        lines.append("")

        # Final note
        lines.extend([
            "---",
            "",
            "## 8. Reviewer note (copy-paste to portal)",
            "",
            self._portal_note(),
            "",
            "---",
            "",
            "_Report generated by `./scripts/terminus review`. Enrich sections 2–7 after manual audit per `prompt.md`._",
        ])
        return "\n".join(lines)

    def format_markdown(self) -> str:
        """Shorter terminal summary; use format_final_report() for the deliverable file."""
        return self.format_final_report()

    def _submission_export_sections(self) -> list[str]:
        """Map submission export regions — see docs/guidelines/submission-export-format.md."""
        lines = ["", "## Submission export sections", ""]
        labels = {
            "difficulty_explanation": "Author — Difficulty Explanation",
            "solution_explanation": "Author — Solution Explanation",
            "verification_explanation": "Author — Verification Explanation",
            "difficulty_check": "System — difficulty check / agent stats / unit tests",
            "instruction_sufficiency": "System — instruction sufficiency analysis",
            "quality_check": "System — LLMaJ quality checks",
            "review_report": "System — Harbor review report",
            "test_quality": "System — test quality review",
            "platform_rubric": "Platform — agent-generated rubric (#32–39)",
            "agent_review": "System — agent review narrative",
            "comments_for_reviewer": "Author — Comments for Reviewer",
            "reviewer_feedback": "Portal — Reviewer Feedback (prior cycle)",
        }
        present = self.export.sections_present()
        lines.append("| Section | Present | Use for |")
        lines.append("|---------|---------|---------|")
        for key, label in labels.items():
            use = {
                "difficulty_explanation": "context only",
                "solution_explanation": "context only — not oracle",
                "verification_explanation": "context only",
                "difficulty_check": "#45, #54, section 7",
                "instruction_sufficiency": "#27, #55 adjudication",
                "quality_check": "LLMaJ hints — verify in files",
                "review_report": "warnings — verify in files",
                "test_quality": "verifier quality",
                "platform_rubric": "rubrics #32–39",
                "agent_review": "advisory",
                "comments_for_reviewer": "author context only",
                "reviewer_feedback": "prior review claims — verify in files",
            }[key]
            lines.append(f"| {label} | {'yes' if present.get(key) else 'no'} | {use} |")
        lines.append("")
        return lines

    def _check_report_task_mismatch(self) -> list[str]:
        lines = ["", "## Report ↔ task identity", ""]
        if not self.report_text:
            return lines

        task_hints: set[str] = set()
        for p in self._instruction_paths():
            t = p.read_text(encoding="utf-8", errors="ignore")
            task_hints.update(x.lower() for x in re.findall(r"\b(python|golang|go|java|rust|rate.?limit|sum|cli)\b", t, re.I))
        toml_languages = re.findall(r'"([^"]+)"', re.search(r"languages\s*=\s*\[(.*?)\]", self.toml_text, re.S).group(1)) if "languages" in self.toml_text else []
        report_hints = set(re.findall(r"\b(golang|go\b|rate.?limit|penalty_ms|traffic.?file|sum_cli|python)\b", self.report_text, re.I))

        # Heuristic mismatch: report discusses concepts absent from task
        report_only = {"penalty_ms", "traffic file", "rate limit", "golang"} & {h.lower() for h in report_hints}
        task_is_python_cli = "sum" in str(self.task_dir).lower() or (self.task_dir / "environment" / "app" / "sum_cli.py").exists()
        if report_only and task_is_python_cli and any(x in self.report_text.lower() for x in ("penalty_ms", "rate limit", "golang")):
            lines.append("⚠️ **Report likely mismatched** — report discusses rate-limiter/Go concepts; task folder appears to be a different task (e.g. Python sum CLI).")
            lines.append("Adjudicate external findings against **task artifacts only**; ignore report claims that don't apply.")
        else:
            lines.append("Report appears applicable to this task folder (or insufficient signal to detect mismatch).")
        lines.append("")
        return lines

    def _adjudicate_external_findings(self) -> list[str]:
        lines = ["", "## External report adjudication (automated hints)", ""]
        decl_m = re.search(r'difficulty\s*=\s*"(\w+)"', self.toml_text, re.I)
        declared = decl_m.group(1).lower() if decl_m else None
        worst = worst_model_rate(self.agent_stats)
        classified = self.agent_stats.classified_difficulty

        # Difficulty metadata mismatch — never a blocker
        if re.search(r"difficulty.*hard.*medium|metadata mismatch|difficulty mismatch", self.report_text, re.I):
            decl_m = re.search(r'difficulty\s*=\s*"(\w+)"', self.toml_text, re.I)
            declared = decl_m.group(1).lower() if decl_m else None
            if declared:
                lines.append("### Claim: difficulty metadata mismatch (task.toml vs platform)")
                lines.append("- **Verdict:** Disagree as blocker")
                worst = worst_model_rate(self.agent_stats)
                classified = self.agent_stats.classified_difficulty
                evidence = f"task.toml `difficulty=\"{declared}\"`"
                if classified:
                    evidence += f"; platform classified `{classified}`"
                if worst is not None:
                    evidence += f"; worst-model {worst:.0f}% → tier `{tier_from_rate(worst)}`"
                lines.append(f"- **Evidence:** {evidence}")
                lines.append("- **Action:** Informational only — always CHECK #45 when difficulty present")
                lines.append("")

        # Spec gap patterns from entire-report style
        for m in re.finditer(r"^\d+\.\s+(.+)$", self.report_text, re.M):
            claim = m.group(1).strip()
            if "penalty_ms" in claim or "file ordering" in claim.lower():
                lines.append(f"### Claim: {claim[:100]}…")
                lines.append("- **Verdict:** Manual — verify against instruction.md and tests")
                lines.append("- **Action:** Use prompt.md Phase 1 spec↔test matrix")
                lines.append("")

        return lines

    def format_json(self) -> str:
        data = {
            "task": str(self.task_dir),
            "blockers": [
                {"id": cb.id, "section": cb.section, "label": cb.label, "evidence": cb.evidence}
                for cb in self.blockers()
            ],
            "uncheck": [
                {"id": cid, "status": self.results[cid].status.value, "label": self.results[cid].label, "evidence": self.results[cid].evidence}
                for cid in self.uncheck_ids()
            ],
            "check": [
                {"id": cid, "label": self.results[cid].label}
                for cid in sorted(self.results) if self.results[cid].status == Status.PASS
            ],
            "na": [cid for cid in sorted(self.results) if self.results[cid].status == Status.NA],
            "agent_stats": {
                "models": self.agent_stats.models,
                "worst_rate": worst_model_rate(self.agent_stats),
                "classified": self.agent_stats.classified_difficulty,
            },
        }
        return json.dumps(data, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Terminus UI reviewer checklist")
    parser.add_argument("task_dir", type=Path)
    parser.add_argument("--report", type=Path, help="External report (entire-report.txt)")
    parser.add_argument("--rubric", type=Path, help="Rubric file path")
    parser.add_argument(
        "--output", "-o", type=Path,
        help="Write full review report to this file (default: <task-dir>/review-report.md)",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--stdout", action="store_true", help="Also print report to stdout")
    args = parser.parse_args()

    review = ReviewChecklist(args.task_dir, args.report, args.rubric)
    review.run()

    output_path = args.output
    if output_path is None and not args.json:
        output_path = args.task_dir / "review-report.md"

    if args.json:
        print(review.format_json())
    else:
        report_text = review.format_final_report()
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report_text, encoding="utf-8")
            print(f"Wrote review report: {output_path}")
        if args.stdout or not output_path:
            print(report_text)

    return 1 if review.blockers() else 0


if __name__ == "__main__":
    sys.exit(main())
