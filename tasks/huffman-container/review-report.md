# Terminus Review Report: huffman-container

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Accept |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (from submission export) |
| **CHECK count** | 50 |
| **UNCHECK count** | 5 |

**Error categories (internal):** none

**Decision (concise):** Manual re-audit found no real blockers. Prior claims about unpinned verifier dependencies and item #20 were false positives: verifier dependencies are pinned in `environment/requirements-verifier.txt` and installed in the image, with no runtime installs in `tests/test.sh`. The external reviewer claims were already addressed (canonical-table wording and Java-only languages metadata). Non-milestone rubric format is valid and positive cap is exactly 40 (pass).

**Insights (concise):**
- `task.toml` declares `number_of_milestones = 0`; non-milestone structure is correct.
- Platform rubric in `entire-report.txt` has one block (`# Rubric 1`), valid for non-milestone tasks.
- Rubric positive total is exactly 40 (`./scripts/terminus rubric-points entire-report.txt`), so no rubric blocker.
- Worst-model pass rate is 0%, so difficulty is not too easy (#54 pass).

---

## 2. Main blockers

No blockers - task meets High-severity bar.

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | High severity none (ChatGPT) | Agree | `instruction.md`, `task.toml`, `tests/test_outputs.py`, `environment/Dockerfile` |
| 2 | Canonical-table helper ambiguity fixed (ChatGPT) | Agree | `instruction.md` |
| 3 | languages cleaned to java-only (ChatGPT) | Agree | `task.toml` |
| 4 | category tweak to software-engineering is optional only (ChatGPT) | Agree | `task.toml` |
| 5 | optional `set -e` in `tests/test.sh` | Agree (non-blocking) | `tests/test.sh` |
| 6 | Prior reviewer asked to require unusable canonical tables rejection beyond decode path | Agree (already fixed) | `instruction.md`, `entire-report.txt` |
| 7 | Prior reviewer asked to set languages to Java only | Agree (already fixed) | `task.toml`, `entire-report.txt` |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise | Prompt is compact and scoped | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt | Human-task framing, not checklist-heavy spec dump | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Minimal formatting | `instruction.md` |
| 4 | CHECK | No step-by-step solver instructions | Specifies outcomes, not procedural walkthrough | `instruction.md` |
| 5 | CHECK | No hints/solving strategy | No solution leakage or explicit recipe | `instruction.md` |
| 6 | CHECK | No design-doc I/O tables | None present | `instruction.md` |
| 7 | CHECK | Instruction is well specified | Concrete requirements and failure semantics | `instruction.md` |
| 8 | CHECK | Instruction is interesting | Realistic codec/interoperability engineering scope | `instruction.md` |
| 9 | UNCHECK | Instruction is unique | Manual corpus-wide uniqueness not provable from local artifacts | - |
| 10 | CHECK | All instruction paths are absolute | Paths are `/app/...` | `instruction.md` |
| 11 | CHECK | Task name absent from instruction | Task folder name not embedded in prompt text | `instruction.md` |
| 12 | CHECK | No canary strings | No canary markers found | `instruction.md` |
| 13 | CHECK | Dockerfile no non-package web fetch | Only package installs/copies | `environment/Dockerfile` |
| 14 | CHECK | pip deps pinned with == | Requirements file pins all verifier deps | `environment/requirements-verifier.txt` |
| 15 | CHECK | Base image digest-pinned | FROM includes sha256 digest | `environment/Dockerfile` |
| 16 | CHECK | No context use outside environment dir | Docker COPY sources are task-local env payloads | `environment/Dockerfile` |
| 17 | CHECK | Environment has no solution/ground-truth leakage | No solution/tests copied into image; no answer hints | `environment/Dockerfile`, `environment/marrow/README.md` |
| 18 | CHECK | No dangerous Docker operations | No privileged mode or docker socket patterns | `environment/Dockerfile` |
| 19 | CHECK | Docker compose reserved mounts not altered | No custom compose in task | `task.toml` |
| 20 | CHECK | Verifier deps baked in image; no runtime install in test.sh | Deps installed in image, test runner does not install packages | `environment/Dockerfile`, `tests/test.sh` |
| 21 | CHECK | Oracle passes consistently | Submission export shows oracle 100% (3/3) | `entire-report.txt` |
| 22 | CHECK | Oracle does not require internet | Oracle script is local file rewrite/compile flow | `solution/solve.sh` |
| 23 | CHECK | Oracle reflects instruction (not hardcoded output) | Implements codec classes, not static expected outputs | `solution/solve.sh` |
| 24 | CHECK | test.sh writes reward and handles failure | Reward logic writes 1/0 | `tests/test.sh` |
| 25 | CHECK | Same verifier logic for oracle/agent | No branching by runner type | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Binary reward only | Reward is exactly 0/1 | `tests/test.sh` |
| 27 | CHECK | Tests align to instruction | Verifier assertions map to documented requirements | `instruction.md`, `tests/test_outputs.py` |
| 28 | CHECK | Tests check correctness not format only | Byte-level behavior and decoding correctness validated | `tests/test_outputs.py` |
| 29 | CHECK | No implementation-grep tests | Behavior-driven subprocess/harness checks | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact-string-only misuse | Assertions are mostly structured behavior/values | `tests/test_outputs.py` |
| 31 | CHECK | Tests have docstrings/names | Test docstrings present throughout | `tests/test_outputs.py` |
| 32 | CHECK | >=3 negative rubric criteria | Platform rubric has multiple negatives | `entire-report.txt` |
| 33 | CHECK | Rubric uses allowed score set | Scores use allowed ±1/2/3/5 set | `entire-report.txt` |
| 34 | CHECK | Rubric line format valid | Agent..., ±N formatting is valid | `entire-report.txt` |
| 35 | CHECK | Rubric criteria detailed | Criteria are task-specific and concrete | `entire-report.txt` |
| 36 | CHECK | Positive rubric phrasing is valid | Positive lines are action-oriented and affirmative | `entire-report.txt` |
| 37 | CHECK | Rubric avoids tests/ directory references | No `/tests` or test-internal references | `entire-report.txt` |
| 38 | CHECK | Rubric avoids metadata/instruction references | No `task.toml`/`instruction.md` dependency wording | `entire-report.txt` |
| 39 | CHECK | Rubric avoids oracle/NOP references | None present in rubric lines | `entire-report.txt` |
| 40 | CHECK | Required files present | All required regular-task files exist | `task.toml` |
| 41 | CHECK | No unnecessary parent files | Task folder structure is clean | `huffman-container/` |
| 42 | CHECK | author_name and author_email present | Present in metadata | `task.toml` |
| 43 | CHECK | Required metadata fields present | Core fields all populated | `task.toml` |
| 44 | CHECK | Tags/languages/categories applicable | Java codec task with matching metadata | `task.toml`, `instruction.md` |
| 45 | CHECK | Difficulty field present | `difficulty = "hard"` exists | `task.toml` |
| 46 | UNCHECK | Milestone layout present | N/A: non-milestone task | `task.toml` |
| 47 | UNCHECK | solveN.sh per milestone | N/A: non-milestone task | `task.toml` |
| 48 | UNCHECK | test_mN.py per milestone | N/A: non-milestone task | `task.toml` |
| 49 | UNCHECK | milestone test scope isolation | N/A: non-milestone task | `task.toml` |
| 50 | CHECK | Tests not baked into image | Dockerfile does not COPY tests | `environment/Dockerfile` |
| 51 | CHECK | Solution/ground truth not accessible in env | Docker image excludes solution and tests assets | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot trivially pass by mutating input data | Verifier includes generated and fixed-reference checks beyond mutable corpus inputs | `tests/test_outputs.py` |
| 53 | CHECK | git clones pinned/absent | No git clone dependency | `environment/Dockerfile` |
| 54 | CHECK | Not too easy (>80% worst-model) | Worst-model is 0% | `entire-report.txt` |
| 55 | CHECK | Task is fair/not impossible | Strong coverage, solvable by oracle and at least one agent run | `entire-report.txt`, `instruction.md`, `tests/test_outputs.py` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 9, 46, 47, 48, 49 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Deterministic Huffman lengths and tie behavior | `test_huff_lengths_unique_tree`, `test_huffman_internal_tie_tags_are_stable`, stress harness tests | covered | `tests/test_outputs.py` |
| Canonical code build/consume and unusable table rejection | `test_huffcoder_rejects_unusable_canonical_length_tables`, decode/harness tests | covered | `instruction.md`, `tests/test_outputs.py` |
| MSB-first symbol emission and decoding | `test_huffcoder_canonical_codes_and_msb_first_writes`, dense/long-code tests | covered | `tests/test_outputs.py` |
| Block framing and trailing-data rejection | block codec tests around headers/EOB/trailing bytes | covered | `tests/test_outputs.py` |
| MRW1 header, flags, size, CRC, fallback | container and inspect tests | covered | `tests/test_outputs.py` |
| Clean failure behavior and output-file preservation | decompression failure tests | covered | `tests/test_outputs.py` |
| Interoperability with independent implementation | reference interoperability tests | covered | `tests/test_outputs.py` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-12, #27-30, external claim adjudication |
| `task.toml` | #42-49, metadata, non-milestone verification |
| `environment/Dockerfile` | #13-20, #50-53 |
| `environment/requirements-verifier.txt` | #14 and #20 pinning/dependency evidence |
| `solution/solve.sh` | #21-23 oracle design |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, #52, #55 |
| `entire-report.txt` | #21, #32-39, #54, prior-review adjudication |

---

## 7. Validation & agent performance

### Validation

```text
./scripts/terminus validate huffman-container
Summary: 0 error(s), 1 warning(s), 2 info
Warning is non-blocking (pip-line heuristic); manual review confirms pinned verifier requirements file.
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 20.0% | below easy threshold |
| terminus-claude-opus-4-8 | 0.0% | hard-tier behavior |
| oracle | 100.0% | solved runs in submission export |

| Metric | Value |
|--------|-------|
| Worst-model rate | 0% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | yes | Reviewed `huffman-container` as regular (non-milestone) task |
| 1 Instruction | yes | Re-read full prompt and constraints |
| 2 Environment | yes | Verified digest pinning, no solution/tests copy, tmux/asciinema present |
| 3 Oracle | yes | Static review plus submission export oracle evidence |
| 4 Verifiers | yes | Full verifier file reviewed |
| 5 Metadata | yes | Languages/category/difficulty checked |
| 6 Rubric | yes | Rubric formatting and +40 cap verified |
| 7 External adjudication | yes | ChatGPT + prior reviewer findings challenged with evidence |
| 8 Novelty/fairness | yes | No unfair blockers found |

---

## 9. Reviewer note (copy-paste to portal)

Strong task overall. The prior concerns appear resolved: instruction wording now clearly requires rejecting unusable canonical tables wherever codes are built or consumed, and metadata is Java-only. I re-checked the environment, verifier, rubric, and interoperability coverage and did not find any blocking issues. The non-milestone rubric format is valid and sits exactly at the 40-point positive cap.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| none | no | - |