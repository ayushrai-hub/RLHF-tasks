#!/usr/bin/env python3
"""Local CI-aligned validator for Project Terminus Edition 2 tasks."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class Finding:
    severity: Severity
    check: str
    message: str
    path: str | None = None

    def format(self) -> str:
        loc = f" [{self.path}]" if self.path else ""
        return f"{self.severity.value}: {self.check}{loc}: {self.message}"


AI_SCAFFOLDING = {
    "CLAUDE.md",
    "claude.md",
    "skills.md",
    "AGENTS.md",
    "agents.md",
    ".cursorrules",
}

HINT_PATTERNS = [
    re.compile(r"step\s+\d+\s*:", re.I),
    re.compile(r"first,?\s+(run|edit|open|create|install)", re.I),
    re.compile(r"then,?\s+(run|edit|open|create|install)", re.I),
    re.compile(r"you should (run|use|execute)", re.I),
    re.compile(r"hint:", re.I),
    re.compile(r"solution:", re.I),
    re.compile(r"todo:\s*fix", re.I),
]

RUNTIME_INSTALL_PATTERNS = [
    re.compile(r"apt-get\s+install", re.I),
    re.compile(r"apt\s+install", re.I),
    re.compile(r"pip\s+install", re.I),
    re.compile(r"pip3\s+install", re.I),
    re.compile(r"npm\s+install", re.I),
    re.compile(r"curl\s+", re.I),
    re.compile(r"wget\s+", re.I),
]

FROM_DIGEST = re.compile(r"FROM\s+[^\s]+@sha256:[a-f0-9]{64}", re.I)
FROM_LINE = re.compile(r"^\s*FROM\s+", re.I)

CANONICAL_BASE_IMAGES: dict[str, str] = {
    "public.ecr.aws/docker/library/python:3.13-slim-bookworm": "01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb",
    "public.ecr.aws/docker/library/node:22-bookworm-slim": "f3a68cf41a855d227d1b0ab832bed9749469ef38cf4f58182fb8c893bc462383",
    "public.ecr.aws/docker/library/golang:1.24-bookworm": "1a6d4452c65dea36aac2e2d606b01b4a029ec90cc1ae53890540ce6173ea77ac",
    "public.ecr.aws/docker/library/rust:1.85-slim": "9f841bbe9e7d8e37ceb96ed907265a3a0df7f44e3737d0b100e7907a679acb36",
    "public.ecr.aws/docker/library/eclipse-temurin:21-jdk-jammy": "25d1276565738d3c805e632a4542c3a7598866ef967f4def6544c15de3a74b14",
    "public.ecr.aws/docker/library/gcc:13-bookworm": "930f2ebe239275fa67226654cb79273ea34eee672ae61c8a39f689c37fb7ac5c",
    "public.ecr.aws/docker/library/ruby:3.3-slim-bookworm": "e76733e94b3a5893e4a141024ef3a583dc10781dc24becebf74f9c9f9a33e3df",
    "public.ecr.aws/docker/library/maven:3.9.9-eclipse-temurin-21": "3a4ab3276a087bf276f79cae96b1af04f53731bec53fb2e651aca79e4b10211e",
    "public.ecr.aws/docker/library/debian:bookworm-slim": "4724b8cc51e33e398f0e2e15e18d5ec2851ff0c2280647e1310bc1642182655d",
    "public.ecr.aws/docker/library/ubuntu:24.04": "0d39fcc8335d6d74d5502f6df2d30119ff4790ebbb60b364818d5112d9e3e932",
}

PROMPT_ANTI_PATTERNS = [
    (re.compile(r"you are an expert", re.I), "LLM-style opener"),
    (re.compile(r"step\s+\d+\s*:", re.I), "step-by-step walkthrough"),
    (re.compile(r"#####\s+step", re.I), "structured step headers"),
    (re.compile(r"detection guidance", re.I), "hint section"),
    (re.compile(r"look for:", re.I), "hint list"),
    (re.compile(r"[\U0001F300-\U0001FAFF]"), "emoji in prompt"),
]

VALID_CATEGORIES = {
    "system-administration",
    "build-and-dependency-management",
    "data-processing",
    "games",
    "software-engineering",
    "machine-learning",
    "debugging",
    "security",
    "scientific-computing",
}

VALID_SUBCATEGORIES = {
    "long_context",
    "tool_specific",
    "api_integration",
    "db_interaction",
    "ui_building",
}


class TaskValidator:
    def __init__(self, task_dir: Path) -> None:
        self.task_dir = task_dir.resolve()
        self.findings: list[Finding] = []
        self.is_milestone = (self.task_dir / "steps").is_dir()

    def add(self, severity: Severity, check: str, message: str, path: str | None = None) -> None:
        self.findings.append(Finding(severity, check, message, path))

    def validate(self) -> list[Finding]:
        if not self.task_dir.is_dir():
            self.add(Severity.ERROR, "structure", f"Task directory not found: {self.task_dir}")
            return self.findings

        self._check_structure()
        self._check_task_toml()
        self._check_diversity()
        self._check_dockerfile()
        self._check_environment_size()
        self._check_ai_scaffolding()
        self._check_hints()
        self._check_instructions()
        self._check_test_docstrings()
        self._check_dockerignore()
        if self.is_milestone:
            self._check_milestone_structure()
        else:
            self._check_regular_tests()
        return self.findings

    def _rel(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.task_dir))
        except ValueError:
            return str(path)

    def _check_structure(self) -> None:
        required = ["task.toml", "environment"]
        if not self.is_milestone:
            required.extend(["instruction.md", "solution", "tests"])
        for name in required:
            p = self.task_dir / name
            if not p.exists():
                self.add(Severity.ERROR, "structure", f"Missing required: {name}")

        if self.is_milestone:
            for forbidden in ("instruction.md", "solution", "tests"):
                if (self.task_dir / forbidden).exists():
                    self.add(
                        Severity.ERROR,
                        "structure",
                        f"Milestone task must not have root-level {forbidden}/",
                        forbidden,
                    )

        dockerfile = self.task_dir / "environment" / "Dockerfile"
        if not dockerfile.exists():
            self.add(Severity.ERROR, "structure", "Missing environment/Dockerfile", "environment/Dockerfile")

    def _check_task_toml(self) -> None:
        toml_path = self.task_dir / "task.toml"
        if not toml_path.exists():
            return
        text = toml_path.read_text(encoding="utf-8", errors="replace")
        rel = self._rel(toml_path)

        if 'version = "2.0"' not in text and "version = '2.0'" not in text:
            self.add(Severity.ERROR, "task.toml", 'version must be "2.0"', rel)

        if not re.search(r"allow_internet\s*=\s*(true|false)\b", text, re.IGNORECASE):
            self.add(
                Severity.ERROR,
                "task.toml",
                "allow_internet must be set to true or false in [environment] "
                "(true only when the task genuinely requires internet)",
                rel,
            )

        if "number_of_milestones" not in text:
            self.add(Severity.WARNING, "task.toml", "number_of_milestones field recommended", rel)

        steps_count = text.count("[[steps]]")
        milestone_match = re.search(r"number_of_milestones\s*=\s*(\d+)", text)
        if milestone_match and steps_count:
            declared = int(milestone_match.group(1))
            if declared != steps_count:
                self.add(
                    Severity.ERROR,
                    "task.toml",
                    f"number_of_milestones ({declared}) != [[steps]] count ({steps_count})",
                    rel,
                )
            if self.is_milestone and declared < 2:
                self.add(
                    Severity.ERROR,
                    "task.toml",
                    "Milestone tasks require number_of_milestones >= 2",
                    rel,
                )

        # tags: 3-6 recommended
        tags_match = re.search(r"tags\s*=\s*\[(.*?)\]", text, re.S)
        if tags_match:
            tag_count = len(re.findall(r'"[^"]+"|\'[^\']+\'', tags_match.group(1)))
            if tag_count < 3:
                self.add(Severity.WARNING, "task.toml", f"tags should have 3-6 entries (found {tag_count})", rel)
            elif tag_count > 6:
                self.add(Severity.WARNING, "task.toml", f"tags should have 3-6 entries (found {tag_count})", rel)
        else:
            self.add(Severity.WARNING, "task.toml", "tags field recommended (3-6 keywords)", rel)

        for field in ("category", "languages", "codebase_size", "expert_time_estimate_min"):
            if field not in text:
                self.add(Severity.WARNING, "task.toml", f"Missing recommended field: {field}", rel)

        cat_match = re.search(r'category\s*=\s*"([^"]+)"', text)
        if cat_match:
            cat = cat_match.group(1).lower()
            if cat not in VALID_CATEGORIES:
                self.add(
                    Severity.ERROR,
                    "task.toml",
                    f"Invalid category '{cat_match.group(1)}' — must be one of: {', '.join(sorted(VALID_CATEGORIES))}",
                    rel,
                )
        else:
            self.add(Severity.WARNING, "task.toml", "category field recommended", rel)

        for sub in re.findall(r'subcategories\s*=\s*\[([^\]]*)\]', text, re.S):
            for m in re.findall(r'"([^"]+)"', sub):
                if m not in VALID_SUBCATEGORIES:
                    self.add(
                        Severity.WARNING,
                        "task.toml",
                        f"Unknown subcategory '{m}' — valid: {', '.join(sorted(VALID_SUBCATEGORIES))}",
                        rel,
                    )

        if self.is_milestone:
            self._check_milestone_toml(text, rel)
        elif re.search(r"^\[agent\]", text, re.M) is None and "[agent]" not in text:
            self.add(Severity.WARNING, "task.toml", "Missing [agent] timeout block for regular task", rel)

    def _check_milestone_toml(self, text: str, rel: str) -> None:
        if re.search(r"^\[agent\]", text, re.M):
            self.add(
                Severity.ERROR,
                "task.toml",
                "Milestone tasks must not have top-level [agent] — use [steps.agent] per milestone",
                rel,
            )
        if re.search(r"^\[verifier\]", text, re.M):
            self.add(
                Severity.ERROR,
                "task.toml",
                "Milestone tasks must not have top-level [verifier] — use [steps.verifier] per milestone",
                rel,
            )
        if "workdir" not in text:
            self.add(
                Severity.WARNING,
                "task.toml",
                "Milestone tasks should set workdir in [environment] (e.g., workdir = \"/app\")",
                rel,
            )

        step_names = re.findall(r'name\s*=\s*"([^"]+)"', text)
        steps_blocks = text.count("[[steps]]")
        milestone_names = [n for n in step_names if n.startswith("milestone_")]
        if steps_blocks and len(milestone_names) != steps_blocks:
            self.add(
                Severity.WARNING,
                "task.toml",
                "Each [[steps]] block should have name = \"milestone_N\"",
                rel,
            )
        for i, name in enumerate(milestone_names, start=1):
            expected = f"milestone_{i}"
            if name != expected:
                self.add(
                    Severity.ERROR,
                    "task.toml",
                    f"[[steps]] name '{name}' should be '{expected}' (sequential snake_case)",
                    rel,
                )
            if f"[steps.agent]" not in text and "steps.agent" not in text:
                pass  # checked per block below
        for n in range(1, steps_blocks + 1):
            if f'name = "milestone_{n}"' not in text:
                continue
            # crude: ensure agent/verifier appear after each steps block
            block = text.split(f'name = "milestone_{n}"', 1)
            if len(block) > 1 and "timeout_sec" not in block[1][:400]:
                self.add(
                    Severity.WARNING,
                    "task.toml",
                    f"milestone_{n} should have [steps.agent] and [steps.verifier] timeouts",
                    rel,
                )

    def _check_diversity(self) -> None:
        toml_path = self.task_dir / "task.toml"
        if not toml_path.exists():
            return
        text = toml_path.read_text(encoding="utf-8", errors="replace")
        rel = self._rel(toml_path)

        if re.search(r'difficulty\s*=\s*"easy"', text, re.I):
            self.add(
                Severity.WARNING,
                "submission-diversity",
                "New submissions rated 'easy' by agent eval are blocked — target medium/hard",
                rel,
            )

        langs = re.findall(r'languages\s*=\s*\[(.*?)\]', text, re.S)
        if langs:
            lang_list = [m.lower() for m in re.findall(r'"([^"]+)"', langs[0])]
            if "python" in lang_list:
                self.add(
                    Severity.INFO,
                    "submission-diversity",
                    "Python tasks must achieve hard model difficulty (≤20% worst-model) for new submissions",
                    rel,
                )

        ms_match = re.search(r"number_of_milestones\s*=\s*(\d+)", text)
        if ms_match and int(ms_match.group(1)) == 0:
            self.add(
                Severity.INFO,
                "submission-diversity",
                "Milestone tasks are preferred for new submissions (non-milestone not blocked)",
                rel,
            )

        self._check_long_context(text, rel)

    def _check_canonical_base(self, from_line: str, dockerfile_text: str, rel: str) -> None:
        """Verify final FROM uses canonical digest or has justification."""
        digest_match = re.search(r"@sha256:([a-f0-9]{64})", from_line, re.I)
        if not digest_match:
            return
        digest = digest_match.group(1).lower()
        image_part = from_line.split("@sha256:")[0].replace("FROM", "").strip()

        for canonical_image, canonical_digest in CANONICAL_BASE_IMAGES.items():
            if canonical_digest == digest or canonical_image in image_part:
                return

        has_justification = bool(
            re.search(r"#.*(justif|reason|because|requires|need|non-canonical)", dockerfile_text, re.I)
            or (self.task_dir / "README.md").exists()
        )
        if not has_justification:
            self.add(
                Severity.WARNING,
                "check_sanctioned_base_images",
                "Non-canonical final base — use docs/guidelines/dockerfile.md list or add justification",
                rel,
            )
        elif digest not in CANONICAL_BASE_IMAGES.values():
            self.add(
                Severity.INFO,
                "check_pinned_images",
                "Non-canonical base with justification — will be surfaced to reviewers",
                rel,
            )

    def _check_long_context(self, text: str, rel: str) -> None:
        if "long_context" not in text:
            return
        env = self.task_dir / "environment"
        large_files = []
        for f in env.rglob("*") if env.is_dir() else []:
            if f.is_file() and f.stat().st_size > 200_000:  # ~50k tokens rough lower bound
                large_files.append(self._rel(f))
        if not large_files:
            self.add(
                Severity.WARNING,
                "long_context",
                "long_context subtype: include ≥50k-token document in environment/ (verify manually)",
                rel,
            )

    def _check_dockerfile(self) -> None:
        dockerfile = self.task_dir / "environment" / "Dockerfile"
        if not dockerfile.exists():
            return
        text = dockerfile.read_text(encoding="utf-8", errors="replace")
        rel = self._rel(dockerfile)
        lines = text.splitlines()

        from_lines = [ln for ln in lines if FROM_LINE.match(ln)]
        if not from_lines:
            self.add(Severity.ERROR, "dockerfile", "No FROM statements found", rel)
        for ln in from_lines:
            if "@sha256:" not in ln.lower():
                self.add(Severity.ERROR, "dockerfile", f"FROM must be digest-pinned: {ln.strip()}", rel)

        lower = text.lower()
        if "tmux" not in lower:
            self.add(Severity.ERROR, "dockerfile", "tmux must be installed (agent runtime requirement)", rel)
        if "asciinema" not in lower:
            self.add(Severity.ERROR, "dockerfile", "asciinema must be installed (agent runtime requirement)", rel)

        if re.search(r"COPY\s+.*\bsolution\b", text, re.I):
            self.add(Severity.ERROR, "dockerfile", "Must not COPY solution/ into image", rel)
        if re.search(r"COPY\s+.*\btests\b", text, re.I):
            self.add(Severity.ERROR, "dockerfile", "Must not COPY tests/ into image", rel)

        if "privileged" in lower and "privileged: true" in lower.replace(" ", ""):
            self.add(Severity.ERROR, "dockerfile", "Privileged mode not allowed", rel)

        if "WORKDIR" not in text:
            self.add(Severity.WARNING, "dockerfile", "WORKDIR should be set before tests run", rel)

        # Check final stage base (last FROM)
        if from_lines:
            last_from = from_lines[-1]
            self._check_canonical_base(last_from, text, rel)

        # Unpinned pip packages
        for ln in lines:
            if re.search(r"pip\s+install", ln, re.I) and "==" not in ln:
                self.add(
                    Severity.WARNING,
                    "pinned_dependencies",
                    f"Pin pip packages with == versions: {ln.strip()[:80]}",
                    rel,
                )

    def _check_environment_size(self) -> None:
        env_dir = self.task_dir / "environment"
        if not env_dir.is_dir():
            return
        total = 0
        for f in env_dir.rglob("*"):
            if f.is_file():
                size = f.stat().st_size
                total += size
                if size > 50 * 1024 * 1024:
                    self.add(
                        Severity.ERROR,
                        "environment-size",
                        f"File exceeds 50 MiB: {self._rel(f)} ({size // (1024*1024)} MiB)",
                        self._rel(f),
                    )
        if total > 100 * 1024 * 1024:
            self.add(
                Severity.ERROR,
                "environment-size",
                f"environment/ exceeds 100 MiB total ({total // (1024*1024)} MiB)",
                "environment/",
            )

    def _check_ai_scaffolding(self) -> None:
        for f in self.task_dir.rglob("*"):
            if not f.is_file():
                continue
            if f.name in AI_SCAFFOLDING:
                self.add(
                    Severity.ERROR,
                    "ai-scaffolding",
                    f"AI scaffolding filename not allowed: {f.name}",
                    self._rel(f),
                )

    def _check_hints(self) -> None:
        scan_dirs = [self.task_dir / "environment"]
        if not self.is_milestone:
            scan_dirs.append(self.task_dir)
        for d in scan_dirs:
            if not d.is_dir():
                continue
            for f in d.rglob("*"):
                if not f.is_file() or f.suffix in {".pyc", ".so", ".bin"}:
                    continue
                if f.name in {"Dockerfile", "task.toml"}:
                    continue
                try:
                    text = f.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                for pat in HINT_PATTERNS:
                    if pat.search(text):
                        self.add(
                            Severity.WARNING,
                            "solution-hints",
                            f"Possible solution hint pattern ({pat.pattern}): review content",
                            self._rel(f),
                        )
                        break

    def _check_instructions(self) -> None:
        paths: list[Path] = []
        if self.is_milestone:
            steps = self.task_dir / "steps"
            if steps.is_dir():
                paths.extend(steps.glob("milestone_*/instruction.md"))
        else:
            p = self.task_dir / "instruction.md"
            if p.exists():
                paths.append(p)

        relative_path = re.compile(r"(?<![/\w])(\.\./|\./|~/)")
        for inst in paths:
            text = inst.read_text(encoding="utf-8", errors="replace")
            rel = self._rel(inst)
            if relative_path.search(text):
                self.add(
                    Severity.WARNING,
                    "check_task_absolute_path",
                    "instruction.md may use relative paths — use absolute paths",
                    rel,
                )
            if not re.search(r"/[\w.-]+", text):
                self.add(
                    Severity.INFO,
                    "check_task_absolute_path",
                    "No absolute paths detected — verify instructions use /app/... paths",
                    rel,
                )
            for pat, label in PROMPT_ANTI_PATTERNS:
                if pat.search(text):
                    self.add(
                        Severity.WARNING,
                        "prompt-styling",
                        f"Possible synthetic prompt pattern ({label})",
                        rel,
                    )
                    break

    def _check_test_docstrings(self) -> None:
        test_files: list[Path] = []
        if self.is_milestone:
            steps = self.task_dir / "steps"
            if steps.is_dir():
                test_files.extend(steps.glob("milestone_*/tests/test_m*.py"))
        else:
            p = self.task_dir / "tests" / "test_outputs.py"
            if p.exists():
                test_files.append(p)

        import ast

        for tf in test_files:
            rel = self._rel(tf)
            try:
                tree = ast.parse(tf.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                self.add(Severity.WARNING, "informative_test_docstrings", "Test file has syntax errors", rel)
                continue
            if not (
                tree.body
                and isinstance(tree.body[0], ast.Expr)
                and isinstance(tree.body[0].value, ast.Constant)
                and isinstance(tree.body[0].value.value, str)
            ):
                self.add(
                    Severity.INFO,
                    "informative_test_docstrings",
                    "Test file has no module-level docstring (recommended)",
                    rel,
                )
            for node in tree.body:
                if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
                    continue
                if not (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                ):
                    self.add(
                        Severity.WARNING,
                        "informative_test_docstrings",
                        f"Test function {node.name}() should have a docstring",
                        rel,
                    )

    def _check_dockerignore(self) -> None:
        env_dir = self.task_dir / "environment"
        if not env_dir.is_dir():
            return
        file_count = sum(1 for f in env_dir.rglob("*") if f.is_file())
        dockerignore = env_dir / ".dockerignore"
        if file_count > 5 and not dockerignore.exists():
            self.add(
                Severity.WARNING,
                "check_dockerignore",
                "Non-trivial environment/ should include .dockerignore",
                "environment/",
            )

    def _check_test_sh(self, test_sh: Path) -> None:
        if not test_sh.exists():
            self.add(Severity.ERROR, "test.sh", "Missing test.sh", self._rel(test_sh))
            return
        text = test_sh.read_text(encoding="utf-8", errors="replace")
        rel = self._rel(test_sh)

        if "/logs/verifier/reward.txt" not in text:
            self.add(Severity.ERROR, "test.sh", "Must write to /logs/verifier/reward.txt", rel)
        if "pytest" not in text:
            self.add(Severity.WARNING, "test.sh", "Expected pytest invocation", rel)

        for pat in RUNTIME_INSTALL_PATTERNS:
            if pat.search(text):
                self.add(Severity.ERROR, "test.sh", f"Runtime network install not allowed: {pat.pattern}", rel)

        # Trailing exit after reward block is discouraged but not an error
        if re.search(r"reward\.txt.*\n.*\bexit\b", text, re.I | re.S):
            self.add(Severity.INFO, "test.sh", "Trailing exit after reward block is unnecessary (not an error)", rel)

    def _check_regular_tests(self) -> None:
        self._check_test_sh(self.task_dir / "tests" / "test.sh")
        test_py = self.task_dir / "tests" / "test_outputs.py"
        if not test_py.exists():
            self.add(Severity.ERROR, "tests", "Missing tests/test_outputs.py", "tests/test_outputs.py")
        else:
            self._check_test_docstrings_for_file(test_py)
        solve = self.task_dir / "solution" / "solve.sh"
        if not solve.exists():
            self.add(Severity.ERROR, "solution", "Missing solution/solve.sh", "solution/solve.sh")

    def _check_test_docstrings_for_file(self, tf: Path) -> None:
        text = tf.read_text(encoding="utf-8", errors="replace")
        rel = self._rel(tf)
        funcs = re.findall(r"def (test_\w+)\(", text)
        if not funcs:
            self.add(Severity.WARNING, "tests", "No test functions found in test_outputs.py", rel)

    def _check_milestone_structure(self) -> None:
        steps_dir = self.task_dir / "steps"
        if not steps_dir.is_dir():
            return
        milestones = sorted(steps_dir.glob("milestone_*"))
        if not milestones:
            self.add(Severity.ERROR, "milestone", "steps/ exists but no milestone_* directories found", "steps/")
            return

        if len(milestones) > 5:
            self.add(
                Severity.WARNING,
                "milestone",
                f"{len(milestones)} milestones — best practice is 2-5; consider combining related steps",
                "steps/",
            )

        for i, ms_dir in enumerate(milestones, start=1):
            rel = self._rel(ms_dir)
            expected_dir = f"milestone_{i}"
            if ms_dir.name != expected_dir:
                self.add(
                    Severity.ERROR,
                    "milestone",
                    f"Directory '{ms_dir.name}' should be '{expected_dir}'",
                    rel,
                )
            for req in ("instruction.md", "tests", "solution"):
                if not (ms_dir / req).exists():
                    self.add(Severity.ERROR, "milestone", f"Missing {req}", f"{rel}/{req}")

            self._check_test_sh(ms_dir / "tests" / "test.sh")
            test_py = ms_dir / "tests" / f"test_m{i}.py"
            if not test_py.exists():
                self.add(Severity.ERROR, "milestone", f"Missing test_m{i}.py", f"{rel}/tests/test_m{i}.py")
            else:
                tp_text = test_py.read_text(encoding="utf-8", errors="replace")
                if f"TestMilestone{i}" not in tp_text:
                    self.add(
                        Severity.WARNING,
                        "milestone",
                        f"test_m{i}.py should define class TestMilestone{i}",
                        f"{rel}/tests/test_m{i}.py",
                    )

            solve_n = ms_dir / "solution" / f"solve{i}.sh"
            solve_wrapper = ms_dir / "solution" / "solve.sh"
            if not solve_n.exists():
                self.add(Severity.ERROR, "milestone", f"Missing solve{i}.sh", f"{rel}/solution/solve{i}.sh")
            if not solve_wrapper.exists():
                self.add(Severity.ERROR, "milestone", "Missing solve.sh wrapper", f"{rel}/solution/solve.sh")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Terminus Edition 2 task")
    parser.add_argument("task_dir", type=Path, help="Path to task directory")
    parser.add_argument("--json", action="store_true", help="Output findings as JSON lines")
    args = parser.parse_args()

    validator = TaskValidator(args.task_dir)
    findings = validator.validate()

    errors = warnings = infos = 0
    for f in findings:
        if args.json:
            import json

            print(json.dumps({"severity": f.severity.value, "check": f.check, "message": f.message, "path": f.path}))
        else:
            print(f.format())
        if f.severity == Severity.ERROR:
            errors += 1
        elif f.severity == Severity.WARNING:
            warnings += 1
        else:
            infos += 1

    if not args.json:
        print()
        print(f"Summary: {errors} error(s), {warnings} warning(s), {infos} info")
        task_type = "milestone" if validator.is_milestone else "regular"
        print(f"Task type detected: {task_type}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
