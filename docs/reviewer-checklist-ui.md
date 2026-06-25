# Reviewer UI Checklist (55 items)

Maps to the Snorkel reviewer portal checkboxes. Use with:

```bash
./scripts/terminus review <task-dir> [--report report.txt] [--rubric rubric.txt]
```

**Rule:** Check an item only if it **passes**. Leave **unchecked** = failed or not applicable.

## Sections

| IDs | Section | N/A when |
|-----|---------|----------|
| 1–12 | Instruction prompt | — |
| 13–20 | Environment | — |
| 21–23 | Oracle | — |
| 24–31 | Verifiers | — |
| 32–39 | Rubrics | No rubric provided |
| 40–41 | Task structure | — |
| 42–45 | Metadata | — |
| 46–49 | Milestones | `number_of_milestones = 0` |
| 50–53 | Anti-cheating | — |
| 54–55 | Difficulty | 54 needs agent report |

## Item 20 note (important)

Portal text: *"Test dependencies installed in test.sh, NOT in the Dockerfile"*.

**Correct interpretation for Terminus 2:** PASS when pytest/verifier deps are **baked in the Docker image** and **test.sh does NOT** `pip install` / `apt-get` at runtime. The portal wording is misleading — follow [writing-tests.md](guidelines/writing-tests.md) and [common-errors.md](guidelines/common-errors.md).

## Automation coverage

| Symbol | Meaning |
|--------|---------|
| 🤖 | Automated in `review_checklist.py` |
| 👁 | Manual verification required before CHECK |
| 📊 | Needs `--report` agent stats |

**Output file:** `./scripts/terminus review <task-dir> --report report.txt` → `<task-dir>/review-report.md`

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

**#45:** `task.toml` `difficulty` matches observed tier.  
**#54:** Not too easy (>80% worst model).

Python tasks: declared `hard` required for new submissions even if observed medium.
