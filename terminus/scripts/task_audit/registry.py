"""Checklist item registry — single source of truth for all 55 portal items."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from task_audit.context import TaskContext
from task_audit.models import CheckResult


@dataclass(frozen=True)
class CheckDefinition:
    item_id: int
    section: str
    label: str
    evaluate: Callable[[TaskContext], CheckResult]


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

_REGISTRY: dict[int, CheckDefinition] = {}


def register(item_id: int, section: str, label: str):
    """Decorator to register a check evaluator function."""

    def decorator(fn: Callable[[TaskContext], CheckResult]):
        _REGISTRY[item_id] = CheckDefinition(item_id, section, label, fn)
        return fn

    return decorator


def get_registry() -> dict[int, CheckDefinition]:
    if not _REGISTRY:
        # Import rule modules for side-effect registration
        from task_audit.rules import load_all  # noqa: WPS433

        load_all()
    return dict(_REGISTRY)
