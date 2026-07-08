"""Task artifact loader — single read-only snapshot for all rule evaluators."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

from rubric_points import (
    RubricPositiveAnalysis,
    analyze_rubric_positives,
    extract_rubric_text_from_report,
    positive_points_from_entire_report,
    positive_points_from_rubric_text,
)
from validate_task import Severity, TaskValidator

from task_audit.submission_export import AgentStats, SubmissionExport, parse_report, parse_submission_export


@dataclass
class TaskContext:
    task_dir: Path
    report_path: Path | None = None
    rubric_path: Path | None = None

    is_milestone: bool = False
    toml_text: str = ""
    milestone_count: int = 0
    report_text: str = ""
    export: SubmissionExport = field(default_factory=SubmissionExport)
    agent_stats: AgentStats = field(default_factory=AgentStats)
    validator_findings: list = field(default_factory=list)
    rubric_positive: RubricPositiveAnalysis = field(default_factory=RubricPositiveAnalysis)

    def __post_init__(self) -> None:
        self.task_dir = self.task_dir.resolve()
        self.is_milestone = (self.task_dir / "steps").is_dir()
        toml = self.task_dir / "task.toml"
        if toml.exists():
            self.toml_text = toml.read_text(encoding="utf-8", errors="replace")
            ms = re.search(r"number_of_milestones\s*=\s*(\d+)", self.toml_text)
            self.milestone_count = int(ms.group(1)) if ms else 0
        if self.report_path and self.report_path.is_file():
            self.report_text = self.report_path.read_text(encoding="utf-8", errors="replace")
            self.export = parse_submission_export(self.report_text)
            self.agent_stats = parse_report(self.report_text, self.export)
        validator = TaskValidator(self.task_dir)
        self.validator_findings = validator.validate()
        self.rubric_positive = self._load_rubric_analysis()

    def rel(self, path: Path | str) -> str:
        p = Path(path)
        try:
            return str(p.relative_to(self.task_dir))
        except ValueError:
            return str(p)

    def instruction_paths(self) -> list[Path]:
        if self.is_milestone:
            steps = self.task_dir / "steps"
            return sorted(steps.glob("milestone_*/instruction.md")) if steps.is_dir() else []
        p = self.task_dir / "instruction.md"
        return [p] if p.exists() else []

    def combined_instruction(self) -> str:
        return "\n".join(
            p.read_text(encoding="utf-8", errors="replace") for p in self.instruction_paths()
        )

    def test_py_paths(self) -> list[Path]:
        if self.is_milestone:
            return sorted((self.task_dir / "steps").glob("milestone_*/tests/test_m*.py"))
        p = self.task_dir / "tests" / "test_outputs.py"
        return [p] if p.exists() else []

    def test_sh_paths(self) -> list[Path]:
        if self.is_milestone:
            return sorted((self.task_dir / "steps").glob("milestone_*/tests/test.sh"))
        p = self.task_dir / "tests" / "test.sh"
        return [p] if p.exists() else []

    def solve_paths(self) -> list[Path]:
        if self.is_milestone:
            return sorted((self.task_dir / "steps").glob("milestone_*/solution/solve*.sh"))
        p = self.task_dir / "solution" / "solve.sh"
        return [p] if p.exists() else []

    def dockerfile_path(self) -> Path:
        return self.task_dir / "environment" / "Dockerfile"

    def dockerfile_text(self) -> str:
        p = self.dockerfile_path()
        return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""

    def rubric_text(self) -> str | None:
        if self.rubric_path and self.rubric_path.is_file():
            return self.rubric_path.read_text(encoding="utf-8", errors="replace")
        for candidate in (self.task_dir / "rubric.txt", self.task_dir / "rubrics.txt"):
            if candidate.exists():
                return candidate.read_text(encoding="utf-8", errors="replace")
        if self.report_text:
            text, _ = extract_rubric_text_from_report(self.report_text)
            if text:
                return text
            if self.export.platform_rubric.strip():
                return self.export.platform_rubric.strip()
        return None

    def validator_errors(self) -> list:
        return [f for f in self.validator_findings if f.severity == Severity.ERROR]

    def validator_warnings(self) -> list:
        return [f for f in self.validator_findings if f.severity == Severity.WARNING]

    def test_functions_missing_docstrings(self) -> list[tuple[str, str]]:
        """Return (file, function_name) pairs missing docstrings — AST-based."""
        missing: list[tuple[str, str]] = []
        for tf in self.test_py_paths():
            try:
                tree = ast.parse(tf.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                missing.append((self.rel(tf), "<syntax-error>"))
                continue
            for node in tree.body:
                if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
                    continue
                if not (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                ):
                    missing.append((self.rel(tf), node.name))
        return missing

    def _load_rubric_analysis(self) -> RubricPositiveAnalysis:
        n_ms = self.milestone_count
        if self.rubric_path and self.rubric_path.is_file():
            return positive_points_from_rubric_text(
                self.rubric_path.read_text(encoding="utf-8", errors="replace"),
                num_milestones=n_ms,
                rubric_source=str(self.rel(self.rubric_path)),
            )
        for candidate in (self.task_dir / "rubric.txt", self.task_dir / "rubrics.txt"):
            if candidate.exists():
                return positive_points_from_rubric_text(
                    candidate.read_text(encoding="utf-8", errors="replace"),
                    num_milestones=n_ms,
                    rubric_source=str(self.rel(candidate)),
                )
        if self.report_path and self.report_path.is_file():
            return positive_points_from_entire_report(self.report_path, num_milestones=n_ms)
        return RubricPositiveAnalysis()
