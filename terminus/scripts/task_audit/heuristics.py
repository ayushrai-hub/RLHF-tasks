"""Structured heuristic evaluators for subjective checklist items."""

from __future__ import annotations

import re
from dataclasses import dataclass

from validate_task import PROMPT_ANTI_PATTERNS, VALID_CATEGORIES

RELATIVE_PATH = re.compile(r"(?<![/\w])(\.\./|\./|~/)")
CANARY_PATTERNS = [
    re.compile(r"canary", re.I),
    re.compile(r"terminus-canary", re.I),
    re.compile(r"do not remove this string", re.I),
]

CATEGORY_SIGNALS: dict[str, set[str]] = {
    "system-administration": {"systemd", "nginx", "useradd", "chmod", "service", "sysctl", "iptables"},
    "build-and-dependency-management": {"cmake", "meson", "cargo", "maven", "gradle", "npm install", "pip install"},
    "data-processing": {"csv", "jsonl", "aggregate", "etl", "parse", "transform"},
    "software-engineering": {"implement", "refactor", "api", "feature", "module", "class"},
    "debugging": {"debug", "fix", "bug", "crash", "leak", "failing", "repair", "broken"},
    "security": {"injection", "tls", "auth", "crypto", "vulnerability", "pentest"},
    "machine-learning": {"model", "train", "inference", "pytorch", "tensorflow"},
    "scientific-computing": {"simulation", "numerical", "matrix", "solver"},
    "games": {"puzzle", "vimgolf", "adventure", "score"},
}


@dataclass
class HeuristicScore:
    passed: bool
    confidence: str  # high | medium | low
    explanation: str
    signals: list[str]


def evaluate_concise(instruction: str) -> HeuristicScore:
    # Prose paragraphs: split on blank lines, exclude bullet-only blocks
    raw_paras = [p for p in re.split(r"\n\s*\n", instruction.strip()) if p.strip()]
    prose_paras = [
        p for p in raw_paras
        if not all(ln.strip().startswith(("-", "*")) or not ln.strip() for ln in p.splitlines())
    ]
    word_count = len(instruction.split())
    bullet_lines = len(re.findall(r"^\s*[-*]\s", instruction, re.M))

    # Word count is the primary gate — Terminus tasks often use short paragraphs + bullets
    if word_count <= 450:
        return HeuristicScore(
            True,
            "high",
            f"Instruction within concise word budget (~{word_count} words, {len(prose_paras)} prose blocks).",
            [f"words={word_count}", f"prose_blocks={len(prose_paras)}"],
        )
    if word_count > 1200 or len(prose_paras) > 10:
        return HeuristicScore(
            False,
            "high",
            f"Instruction is very long ({len(prose_paras)} prose blocks, ~{word_count} words, {bullet_lines} bullets).",
            [f"prose_blocks={len(prose_paras)}", f"words={word_count}"],
        )
    if len(prose_paras) > 4 or word_count > 700:
        return HeuristicScore(
            False,
            "medium",
            f"Instruction may exceed concise bar ({len(prose_paras)} prose blocks, ~{word_count} words).",
            [f"prose_blocks={len(prose_paras)}", f"words={word_count}"],
        )
    return HeuristicScore(
        True,
        "high",
        f"Instruction length within heuristic bounds ({len(prose_paras)} prose blocks, ~{word_count} words).",
        [f"prose_blocks={len(prose_paras)}", f"words={word_count}"],
    )


def evaluate_natural_tone(instruction: str) -> HeuristicScore:
    hits = [label for pat, label in PROMPT_ANTI_PATTERNS if pat.search(instruction)]
    if hits:
        return HeuristicScore(False, "high", f"Synthetic/LLM patterns detected: {', '.join(hits)}", hits)
    spec_markers = len(re.findall(r"^(#{1,3}\s|[-*]\s*\*\*|Table of Contents)", instruction, re.M | re.I))
    if spec_markers >= 5:
        return HeuristicScore(
            False,
            "medium",
            f"Reads spec-like ({spec_markers} structural markers).",
            [f"spec_markers={spec_markers}"],
        )
    if re.search(r"^(Objective|Requirements|Deliverables|Scope):", instruction, re.M | re.I):
        return HeuristicScore(False, "medium", "Formal spec section headers detected.", ["spec_headers"])
    return HeuristicScore(True, "medium", "No automated synthetic-pattern hits; tone appears conversational.", [])


def evaluate_well_specified(instruction: str) -> HeuristicScore:
    abs_paths = re.findall(r"/[\w][\w./-]*", instruction)
    verbs = re.findall(r"\b(write|create|fix|implement|repair|output|run)\b", instruction, re.I)
    if not abs_paths:
        return HeuristicScore(False, "high", "No absolute paths — goal likely underspecified.", [])
    if len(abs_paths) < 2 and not verbs:
        return HeuristicScore(False, "medium", "Few measurable actions or paths.", [f"paths={len(abs_paths)}"])
    vague = re.findall(r"\b(fix issues|optimize|handle properly|improve)\b", instruction, re.I)
    if vague:
        return HeuristicScore(False, "medium", f"Vague requirements: {vague[:3]}", vague)
    return HeuristicScore(
        True,
        "medium",
        f"Contains {len(abs_paths)} absolute path(s) and actionable verbs.",
        [f"paths={len(abs_paths)}", f"verbs={len(verbs)}"],
    )


def evaluate_category_fit(category: str, tags: list[str], languages: list[str], instruction: str) -> HeuristicScore:
    if category not in VALID_CATEGORIES:
        return HeuristicScore(False, "high", f"Unknown category '{category}'.", [])

    corpus = " ".join([instruction.lower()] + [t.lower() for t in tags] + [l.lower() for l in languages])
    scores: dict[str, int] = {cat: 0 for cat in CATEGORY_SIGNALS}
    matched: dict[str, list[str]] = {cat: [] for cat in CATEGORY_SIGNALS}

    for cat, signals in CATEGORY_SIGNALS.items():
        for sig in signals:
            if sig in corpus:
                scores[cat] += 1
                matched[cat].append(sig)

    declared_score = scores.get(category, 0)
    best_cat = max(scores, key=lambda c: scores[c])
    best_score = scores[best_cat]

    # Strong mismatch: sysadmin category on pure code-repair tasks
    code_signals = {"debug", "fix", "repair", "refactor", "implement", "raft", "consensus", "javascript", "nodejs", "golang", "go"}
    if category == "system-administration" and (code_signals & set(tags + languages) or any(s in corpus for s in ("repair", "fix", "debug", "refactor"))):
        return HeuristicScore(
            False,
            "medium",
            f"Category '{category}' mismatches code-repair work (consider software-engineering or debugging).",
            list(code_signals & set(tags + languages))[:4],
        )

    if declared_score == 0 and best_score >= 2 and best_cat != category:
        return HeuristicScore(
            False,
            "medium",
            f"Category '{category}' mismatches content signals (best fit: '{best_cat}' via {matched[best_cat][:4]}).",
            matched[best_cat][:6],
        )
    if declared_score >= 1 or best_score <= 1:
        return HeuristicScore(
            True,
            "low" if declared_score == 0 else "medium",
            f"Category '{category}' consistent with available signals (score={declared_score}).",
            matched.get(category, [])[:4],
        )
    return HeuristicScore(
        False,
        "low",
        f"Weak category alignment for '{category}' (signals={declared_score}, best={best_cat}).",
        [],
    )


def evaluate_spec_test_alignment(instruction: str, test_source: str) -> HeuristicScore:
    """Heuristic: flag numeric thresholds asserted in tests but absent from instruction."""
    test_thresholds = set(re.findall(r'assert[^#\n]*?(?:>=|>|==)\s*(\d+)', test_source))
    inst_numbers = set(re.findall(r'\b(\d+)\b', instruction))
    phantom = sorted(int(t) for t in test_thresholds if t not in inst_numbers and int(t) > 3)
    if len(phantom) >= 3:
        return HeuristicScore(
            False,
            "medium",
            f"Tests assert numeric thresholds not found in instruction: {phantom[:6]}.",
            [str(p) for p in phantom[:6]],
        )
    if phantom:
        return HeuristicScore(
            True,
            "low",
            f"Minor phantom thresholds in tests (not in instruction): {phantom}.",
            [str(p) for p in phantom],
        )
    return HeuristicScore(True, "medium", "No obvious phantom numeric thresholds detected.", [])


def evaluate_correctness_vs_format(test_source: str) -> HeuristicScore:
    format_only = len(re.findall(r'assert\s+["\'][\w_]+["\']\s+in\s+', test_source))
    behavior = len(re.findall(r'(run_cli|subprocess|returncode|read_json|read_text)', test_source))
    if format_only > behavior * 2 and behavior < 3:
        return HeuristicScore(False, "medium", "Tests appear format-heavy vs behavior checks.", [])
    return HeuristicScore(True, "medium", "Tests include behavioral integration patterns.", [])
