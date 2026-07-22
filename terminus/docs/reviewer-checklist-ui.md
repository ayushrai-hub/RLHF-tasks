# Reviewer UI Checklist (55 items)

Maps to the Snorkel reviewer portal checkboxes. Use with:

```bash
./scripts/terminus validate <task-dir>
./scripts/terminus audit <task-dir> [--report report.txt]
./scripts/terminus review <task-dir> [--report report.txt]
```

**Rule:** Check an item only if it **passes**. Leave **unchecked** = failed or not applicable.

## Sections

| IDs | Section | N/A when |
|-----|---------|----------|
| 1–12 | Instruction prompt | — |
| 13–20 | Environment | — |
| 21–23 | Oracle | — |
| 24–31 | Verifiers | — |
| 32–39 | Rubrics | No rubric anywhere (see rubric note below) |
| 40–41 | Task structure | — |
| 42–45 | Metadata | — |
| 46–49 | Milestones | `number_of_milestones = 0` |
| 50–53 | Anti-cheating | — |
| 54–55 | Difficulty | 54 needs agent report |

## Item 20 note (important)

Portal text: *"Test dependencies installed in test.sh, NOT in the Dockerfile"*.

**Correct interpretation for Terminus 2:** PASS when pytest/verifier deps are **baked in the Docker image** and **test.sh does NOT** `pip install` / `apt-get` at runtime. The portal wording is misleading — follow [writing-tests.md](guidelines/writing-tests.md) and [common-errors.md](guidelines/common-errors.md).

## Rubric checkboxes (#32–39)

Rubrics are authored on the **submission platform**, not in the task zip. For review:

1. **Use the platform rubric** from the submission export (`entire-report.txt`, Snorkel download, or `--report` / `--rubric` input).
2. **Do not mark #32–39 N/A** merely because `rubric.txt` is missing from the task folder — that is expected.
3. **Mark N/A only** when no platform rubric is available in the report or reviewer package.

**Source priority:** `--rubric rubric.txt` → `task-dir/rubric.txt` → `platform_rubric` section in `--report`.

**Section map:** Submission exports bundle author form fields, difficulty stats, LLMaJ quality checks, review reports, platform rubric, **Comments for Reviewer**, and **Reviewer Feedback** into one file. Parse sections before use — see [submission-export-format.md](guidelines/submission-export-format.md).

Validate format with `./scripts/terminus rubric-validate <file> --milestones N` when a rubric file is saved locally. See [rubrics.md](guidelines/rubrics.md).

**Positive point cap (mandatory):** Sum all `+N` criteria in the platform rubric. **>40 total** on a non-milestone task, or **>40 in any milestone block**, is a **main blocker** — disposition **Revise**, error category **Rubric**. Not Low/optional.

## Automation coverage

| Symbol | Meaning |
|--------|---------|
| 🤖 | Automated in `scripts/task_audit/` (via `terminus audit`) and `review_checklist.py` |
| 👁 | Manual verification required before CHECK |
| 📊 | Needs `--report` agent stats |

**Output files:**
- `./scripts/terminus audit` → `<task-dir>/audit-report.md` (55-item statuses + verdict)
- `./scripts/terminus review` → `<task-dir>/review-report.md` (portal CHECK/UNCHECK)

## Portal rules (critical)

1. **CHECK** only checkbox numbers that **pass** after full audit
2. **UNCHECK** everything else: failed, unverified (manual), or N/A
3. Manual items (#2, #7, #8, #9, #27, #28, #55) stay **UNCHECKED** until you verify and move them to CHECK in the report

## Difficulty checkbox (#45, #54)

From [difficulty.md](guidelines/difficulty.md):

| Observed worst-model pass rate | Tier |
|-------------------------------|------|
| ≤20% | Hard |
| 20–60% | Medium |
| 60–80% | Easy |
| >80% | Rejected (too easy) |

**Worst model** = **lowest** pass rate among reference agents (GPT-5.5, Claude Opus 4.8). **Best model** = highest.

**#45 (mandatory):** **CHECK** when `difficulty` is set in `task.toml`. Declared vs platform classified difficulty, or vs agent-rate tier, is **never** a failure — record both values in section 7 only.

**#54:** **CHECK** when worst-model rate ≤80%; **UNCHECK** only when worst-model **>80%** (too easy).

**Single-model Hard (Jul 21, 2026):** Platform runs Claude Opus 4.8 first; if ≤20% (Hard), GPT-5.5 may be skipped. One-model Hard results are expected — do **not** UNCHECK or request revision for missing GPT-5.5. See [difficulty.md](guidelines/difficulty.md).

**Reviewer policy:** `task.toml` `difficulty` differing from platform `Difficulty: …` or from agent-run tiers is **never** a revision blocker, never a Main blocker row, and never drives **Revise** on its own. **#54** (>80% worst model) remains the only difficulty-related blocker.

**Portal reviewer note (section 9):** Human tone for the author — acknowledge strengths, then fixes; no framework citations or audit-bot phrasing. See `prompt.md` §9.

Python tasks: declared `hard` required for new submissions even if observed medium.
