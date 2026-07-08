"""Environment rules (#13–#20)."""

from __future__ import annotations

import re

from validate_task import RUNTIME_INSTALL_PATTERNS

from task_audit.context import TaskContext
from task_audit.models import EvidenceRef
from task_audit.registry import register
from task_audit.rules._helpers import fail, pass_, unknown

WEB_FETCH_PATTERNS = [
    re.compile(r"urllib\.request\.urlopen", re.I),
    re.compile(r"requests\.get\s*\(", re.I),
    re.compile(r"curl\s+https?://", re.I),
    re.compile(r"wget\s+https?://", re.I),
]


@register(13, "ENVIRONMENT", "Dockerfile does not grab content from the web (other than packages)")
def check_13(ctx: TaskContext):
    label = "Dockerfile does not grab content from the web (other than packages)"
    env_dir = ctx.task_dir / "environment"
    if not env_dir.is_dir():
        return fail(13, "ENVIRONMENT", label, "Missing environment/", evidence=[EvidenceRef("environment/")])
    web_hits: list[EvidenceRef] = []
    for f in env_dir.rglob("*"):
        if f.is_file() and f.suffix in {".py", ".sh", ".js", ".go", ".rs"}:
            try:
                ft = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for pat in WEB_FETCH_PATTERNS:
                if pat.search(ft):
                    web_hits.append(EvidenceRef(ctx.rel(f)))
                    break
    if web_hits:
        return fail(13, "ENVIRONMENT", label, f"Runtime web fetch in {len(web_hits)} file(s)", evidence=web_hits[:5])
    return pass_(13, "ENVIRONMENT", label, "No runtime web fetch in environment code")


@register(14, "ENVIRONMENT", "All Python/pip dependencies use pinned versions with == (no ranges)")
def check_14(ctx: TaskContext):
    label = "All Python/pip dependencies use pinned versions with == (no ranges)"
    text = ctx.dockerfile_text()
    if not text:
        return fail(14, "ENVIRONMENT", label, "Missing Dockerfile")
    unpinned = [ln.strip()[:80] for ln in text.splitlines() if re.search(r"pip\s+install", ln, re.I) and "==" not in ln]
    if unpinned:
        return fail(14, "ENVIRONMENT", label, f"Unpinned pip: {unpinned[0]}", evidence=[EvidenceRef("environment/Dockerfile")])
    return pass_(14, "ENVIRONMENT", label, "pip packages pinned or absent", evidence=[EvidenceRef("environment/Dockerfile")])


@register(15, "ENVIRONMENT", "Base Docker image is pinned by digest (@sha256:...)")
def check_15(ctx: TaskContext):
    label = "Base Docker image is pinned by digest (@sha256:...)"
    text = ctx.dockerfile_text()
    from_lines = [ln for ln in text.splitlines() if re.match(r"^\s*FROM\s+", ln, re.I)]
    bad = [ln.strip() for ln in from_lines if "@sha256:" not in ln.lower()]
    if bad:
        return fail(15, "ENVIRONMENT", label, f"Unpinned FROM: {bad[0]}", evidence=[EvidenceRef("environment/Dockerfile", 1)])
    if not from_lines:
        return fail(15, "ENVIRONMENT", label, "No FROM statements", evidence=[EvidenceRef("environment/Dockerfile")])
    return pass_(15, "ENVIRONMENT", label, "All FROM lines digest-pinned", evidence=[EvidenceRef("environment/Dockerfile")])


@register(16, "ENVIRONMENT", "Environment does not use context from outside the environment directory")
def check_16(ctx: TaskContext):
    label = "Environment does not use context from outside the environment directory"
    if re.findall(r"COPY\s+(\.\./|\.\.\\)", ctx.dockerfile_text(), re.I):
        return fail(16, "ENVIRONMENT", label, "COPY references parent of build context")
    return pass_(16, "ENVIRONMENT", label, "No COPY outside environment/")


@register(17, "ENVIRONMENT", "Environment does not contain solution or ground truth answers")
def check_17(ctx: TaskContext):
    label = "Environment does not contain solution or ground truth answers"
    env_dir = ctx.task_dir / "environment"
    solve_in_env = list(env_dir.rglob("solve.sh")) + list(env_dir.rglob("answer*"))
    if solve_in_env:
        return fail(17, "ENVIRONMENT", label, "Solution-like files in environment/", evidence=[EvidenceRef(ctx.rel(solve_in_env[0]))])
    hint_errors = [f for f in ctx.validator_warnings() if f.check == "solution-hints"]
    if len(hint_errors) > 5:
        return fail(
            17, "ENVIRONMENT", label,
            f"{len(hint_errors)} possible hint patterns in environment files",
            blocking=False,
            suggestion="Review environment comments/docs for answer leakage.",
        )
    return unknown(
        17, "ENVIRONMENT", label,
        "No obvious solution files; manual review needed for comment/doc leakage.",
        suggestion="Scan environment docs and comments for walkthroughs or golden answers.",
    )


@register(18, "ENVIRONMENT", "Dockerfile does not execute dangerous operations (no privileged, SYS_ADMIN, docker.sock)")
def check_18(ctx: TaskContext):
    label = "Dockerfile does not execute dangerous operations (no privileged, SYS_ADMIN, docker.sock)"
    lower = ctx.dockerfile_text().lower()
    if "privileged: true" in lower.replace(" ", "") or "docker.sock" in lower or "sys_admin" in lower:
        return fail(18, "ENVIRONMENT", label, "Privileged/dangerous Docker config")
    return pass_(18, "ENVIRONMENT", label, "No privileged/SYS_ADMIN/docker.sock")


@register(19, "ENVIRONMENT", "Docker compose does not alter reserved harbor mounts (/logs/artifacts, /logs/verifier, /tests, /solution)")
def check_19(ctx: TaskContext):
    label = "Docker compose does not alter reserved harbor mounts (/logs/artifacts, /logs/verifier, /tests, /solution)"
    compose = ctx.task_dir / "environment" / "docker-compose.yaml"
    if not compose.exists():
        return pass_(19, "ENVIRONMENT", label, "No docker-compose.yaml")
    ct = compose.read_text(encoding="utf-8", errors="replace")
    if re.search(r"/tests|/solution|/logs/verifier", ct):
        return fail(19, "ENVIRONMENT", label, "Compose may conflict with Harbor mounts", evidence=[EvidenceRef("environment/docker-compose.yaml")])
    return pass_(19, "ENVIRONMENT", label, "Compose present; no reserved mount overrides")


@register(20, "ENVIRONMENT", "Verifier deps baked in image; test.sh does NOT install packages at runtime")
def check_20(ctx: TaskContext):
    label = "Verifier deps baked in image; test.sh does NOT install packages at runtime"
    df = ctx.dockerfile_text()
    for ts in ctx.test_sh_paths():
        ttext = ts.read_text(encoding="utf-8", errors="replace")
        for pat in RUNTIME_INSTALL_PATTERNS:
            if pat.search(ttext):
                return fail(20, "ENVIRONMENT", label, "test.sh installs packages at runtime", evidence=[EvidenceRef(ctx.rel(ts))])
    if ctx.test_sh_paths() and "pytest" not in df.lower():
        return fail(20, "ENVIRONMENT", label, "pytest not in Dockerfile — verifier deps must be baked in image")
    tmux_ok = "tmux" in df.lower()
    asci_ok = "asciinema" in df.lower()
    extra = ""
    if not tmux_ok or not asci_ok:
        extra = f" (also missing: {'' if tmux_ok else 'tmux'}{', ' if not tmux_ok and not asci_ok else ''}{'' if asci_ok else 'asciinema'})"
        return fail(20, "ENVIRONMENT", label, f"Dockerfile missing agent runtime tools{extra}")
    return pass_(20, "ENVIRONMENT", label, "Verifier deps in image; no runtime installs in test.sh")
