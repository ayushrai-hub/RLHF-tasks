# Terminus Review Report: fits-wcs-sky-atlas-generator2

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | not executed |
| **CHECK count** | 48 |
| **UNCHECK count** | 7 |

**Error categories (internal):** Test Alignment/Coverage Issues, Instruction Styling

**Decision (concise):** Strong FITS/WCS C++ task with digest-pinned env, hidden fixtures, independent Python reference, and clean rubric (29/40, flat non-milestone format). NAXIS=0 export behavior is now documented and aligned with tests. One real blocker remains: the fingerprint field is documented only as “lowercase hex digest” while `test_fingerprint_stable_and_non_empty` hard-requires a 16-character hex string (FNV-1a 64-bit behavior in the baseline stub), causing systematic 27/28 near-misses when agents reasonably choose SHA-256.

**Insights (concise):**

- Prior reviewer note at top of `entire-report.txt` (NAXIS=0 export `0` vs `1`) is **stale** — current `atlas-schema.md:9` documents export `1` and matches `test_header_only_naxis_zero`.
- ChatGPT fingerprint finding is **confirmed** with file evidence; agent stats show 8/10 pass on `test_fingerprint_stable_and_non_empty`.
- Automated `terminus review` blockers for #14, #20, #31 are **false positives** — `requirements.lock` uses `==` + hashes, pytest is baked in the image, and all 28 tests have docstrings.
- Platform rubric is **not** in milestone format: single flat `Agent …, ±N` block (29 positives, 4 negatives); no `# Rubric 2+` headers.
- Non-canonical `gcc:13-bookworm` base is digest-pinned and justified for C++; advisory only, not a blocker.
- Weak checks on `axis_midpoints` (count only) and `pixel_scale_arcsec` (positive only) are Low polish, not blockers.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues, Instruction Styling | #27, #55 | Fingerprint contract under-specified: schema says “lowercase hex digest of canonical keyword string” with no algorithm or length; test enforces exactly 16 lowercase hex chars | `environment/docs/atlas-schema.md:17`; `tests/test_outputs.py:471-477`; baseline FNV-1a in `environment/src/atlas_writer.cpp:10-24` | Document required fingerprint algorithm and 16-char length in `atlas-schema.md` (and optionally `keyword-snapshot-schema.md`), e.g. FNV-1a 64-bit over `canonical\|projection\|corner_count\|corner_ra,dec…` per baseline `atlas_fingerprint`, **or** relax the test to accept any lowercase hex digest described in the schema |

*No other High/Medium blockers identified.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Fingerprint under-specified vs 16-char test; agents used SHA-256 and failed 27/28 (ChatGPT High) | **Agree** | `atlas-schema.md:17` — no length/algorithm; `test_outputs.py:477` — `len(fp1) == 16`; `entire-report.txt:87-88,119-121` — two trials failed only on fingerprint; 8/10 pass rate on `test_fingerprint_stable_and_non_empty` |
| 2 | NAXIS=0 schema says export `0` but tests expect `1` (ChatGPT Medium / `entire-report.txt` line 1) | **Disagree (stale)** | Current `atlas-schema.md:9` — “export 1 for both fields”; `test_outputs.py:337` — `assert data["naxis1"] == 1`; `test_header_only_naxis_zero` 10/10 agent passes |
| 3 | axis_midpoints checked only by count (ChatGPT Low) | **Agree (Low only)** | `test_outputs.py:347-352` — `assert len(mids) == 4` only |
| 4 | pixel_scale_arcsec checked only as positive (ChatGPT Low) | **Agree (Low only)** | `test_outputs.py:340-345` — `assert scale > 0` only |
| 5 | Category should be scientific-computing (Harbor review / ChatGPT Low) | **Partially agree (Low only)** | `task.toml:7` — `data-processing`; tags include `scientific-computing`; not a blocker |
| 6 | Non-canonical gcc base image (Harbor review warning) | **Partially agree (advisory)** | `environment/Dockerfile:1` — digest-pinned `gcc:13-bookworm`; C++ toolchain justified; not a Terminus blocker |
| 7 | WCS linear transform CDELT phrasing ambiguous (Harbor suggestion) | **Partially agree (Low)** | `wcs-linear-transform.md:15` — parenthetical “first index” ambiguous; formula matches oracle/tests |
| 8 | Portal rubric format fine for non-milestone (`entire-report.txt` line 1) | **Agree** | `task.toml:9` — `number_of_milestones = 0`; rubric lines 390-405 — flat list, no `# Rubric 2`; 29 positive pts ≤40 |
| 9 | LLMaJ `task_specification` FAIL on fingerprint (entire-report) | **Agree** | Same evidence as claim 1 |
| 10 | Automated review blockers #14, #20, #31 | **Disagree** | `#14`: `requirements.lock` uses `package==version` + hashes; `#20`: `Dockerfile:18-20` installs pytest in image, `test.sh` has no pip/apt; `#31`: all `test_*` methods have docstrings (`test_outputs.py:243-486`) |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction is concise (1 sentence to 3 paragraphs max) | Five short paragraphs; slightly over 3-paragraph guideline but acceptable with doc references | `instruction.md` |
| 2 | CHECK | Instruction reads like a natural prompt, not a spec document | Problem-first tone; defers detail to `/app/docs` | `instruction.md` |
| 3 | CHECK | No excessive markdown formatting | Plain prose, no headers/tables | `instruction.md` |
| 4 | CHECK | No step by step instructions | States outcomes and doc contracts, not implementation steps | `instruction.md` |
| 5 | CHECK | No hints or solving strategies | WHAT to build; formulas in separate docs | `instruction.md` |
| 6 | CHECK | No design doc style tables | No I/O mapping tables in instruction | `instruction.md` |
| 7 | CHECK | Instruction is well specified | Clear outputs, paths, projection families, idempotency | `instruction.md` |
| 8 | CHECK | Instruction is interesting | Real FITS/WCS astronomy tooling | — |
| 9 | CHECK | Instruction is unique | FITS lexer + WCS + hidden fixtures combo is distinctive | — |
| 10 | CHECK | All paths in instruction are absolute | `/app/bin/wcs-atlas`, `/app/output/...`, `/app/var/...`, `/app/docs/...` | `instruction.md:3-7` |
| 11 | CHECK | Task name does not appear in instruction.md | No task slug in instruction | `instruction.md` |
| 12 | CHECK | No canary string in instruction.md | No canary patterns | `instruction.md` |
| 13 | CHECK | Dockerfile does not grab content from the web | No runtime fetch in env code | `environment/Dockerfile` |
| 14 | CHECK | All Python/pip dependencies use pinned versions with == | `requirements.lock` pins with `==` and hashes; `--require-hashes` in Dockerfile | `environment/requirements.lock`, `environment/Dockerfile:18-20` |
| 15 | CHECK | Base Docker image is pinned by digest | `FROM ...@sha256:930f2e...` | `environment/Dockerfile:1` |
| 16 | CHECK | Environment does not use context from outside environment directory | COPY only from environment tree | `environment/Dockerfile:24-30` |
| 17 | CHECK | Environment does not contain solution or ground truth answers | No `solution/` or `tests/` COPY; stubs are intentionally broken, not golden outputs | `environment/Dockerfile` |
| 18 | CHECK | Dockerfile does not execute dangerous operations | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Docker compose does not alter reserved harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps baked in image; test.sh does NOT install packages | pytest installed at image build; test.sh only invokes `/opt/verifier-venv/bin/python -m pytest` | `environment/Dockerfile:18-20`, `tests/test.sh:27-28` |
| 21 | UNCHECK | Oracle passes consistently (no flaky behavior) | Oracle not executed locally (Docker build unavailable in review session) | — |
| 22 | CHECK | Oracle does not require internet or downloading packages | `solve.sh` copies files and runs `build.sh` only | `solution/solve.sh` |
| 23 | CHECK | Oracle is reflective of instruction | Copies five implementation `.cpp` files and rebuilds; no hardcoded JSON echo | `solution/solve.sh:8-14` |
| 24 | CHECK | test.sh writes reward.txt; handles failure path | Canonical reward block with failure writes `0` | `tests/test.sh:5-6,21-34` |
| 25 | CHECK | Verifiers use same logic for oracle and agent | No `/oracle` branching | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Verifier applies binary rewards only | `0` or `1` in reward.txt | `tests/test.sh:30-33` |
| 27 | UNCHECK | All tests aligned with instructions | Fingerprint length/algorithm tested but not specified in schema | `atlas-schema.md:17`, `test_outputs.py:477` |
| 28 | CHECK | Tests check for correctness, not just format | Independent Python WCS reference for corners; hidden fixture numerical checks | `test_outputs.py:266-275,384-393` |
| 29 | CHECK | Tests verify behavior, not implementation | Subprocess CLI + JSON output assertions | `tests/test_outputs.py` |
| 30 | CHECK | No brittle exact string matching where flexible checks would work | Numeric tolerances for RA/Dec; exact pixel set appropriate for discrete corners | `test_outputs.py` |
| 31 | CHECK | Tests have informative names or docstrings | All 28 `test_*` methods have docstrings | `test_outputs.py:243-486` |
| 32 | CHECK | Rubrics contain at least 3 negative penalty criteria | 4 negative lines | `entire-report.txt:402-405` |
| 33 | CHECK | Rubric scores from {1,2,3,5,-1,-2,-3,-5} | All lines use ±1,2,3 | `entire-report.txt:390-405` |
| 34 | CHECK | Each rubric criterion one line starting with Agent | 16 Agent lines | `entire-report.txt:390-405` |
| 35 | CHECK | Rubric criteria detailed and precise | 29 positive pts (≤40 cap) | `entire-report.txt:390-401` |
| 36 | CHECK | Rubric criteria use positive language | Penalties describe observable bad traces with negative scores | `entire-report.txt:402-405` |
| 37 | CHECK | Rubric does not reference /tests/ | No test path references | `entire-report.txt:390-405` |
| 38 | CHECK | Rubric does not reference task.toml or instruction.md | No metadata refs | `entire-report.txt:390-405` |
| 39 | CHECK | Rubric does not mention oracle or NOP | No oracle/NOP mentions | `entire-report.txt:390-405` |
| 40 | CHECK | All required files present | Dockerfile, solve.sh, test.sh, instruction.md, task.toml present | task root |
| 41 | CHECK | No unnecessary files in parent directory | Clean task folder | task root |
| 42 | CHECK | author_name and author_email present | Fields in task.toml | `task.toml:4-5` |
| 43 | CHECK | All other required metadata fields present | version, difficulty, category, timeouts, allow_internet=false | `task.toml` |
| 44 | CHECK | Tags, languages, categories applicable | cpp/cmake/fits/wcs tags match content | `task.toml:7-12` |
| 45 | CHECK | Difficulty matches observed agent pass rates | `difficulty=hard` present; worst-model 60% → medium tier — informational mismatch only, not a blocker | `task.toml:6`, `entire-report.txt:17-23` |
| 46 | UNCHECK | steps/ layout for milestones | N/A — `number_of_milestones = 0` | `task.toml:9` |
| 47 | UNCHECK | Each milestone has solveN.sh | N/A — not a milestone task | `task.toml:9` |
| 48 | UNCHECK | Each milestone has test_mN.py | N/A — not a milestone task | `task.toml:9` |
| 49 | UNCHECK | Milestone tests scoped per milestone | N/A — not a milestone task | `task.toml:9` |
| 50 | CHECK | Tests NOT baked into Docker image | No COPY tests/ | `environment/Dockerfile` |
| 51 | CHECK | Solution not accessible in environment | solution/ not copied to image | `environment/Dockerfile` |
| 52 | CHECK | Agent cannot trivially modify input data | Hidden fixtures at `/opt/verifier-fixtures/fits/` | `environment/Dockerfile:34-35`, `tests/test_outputs.py` |
| 53 | CHECK | Git repos pinned to specific commit | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Task is not too easy (>80% pass) | Worst-model 60% ≤80% | `entire-report.txt:21-23` |
| 55 | UNCHECK | Task is not too hard or unfair | Fingerprint length enforced without schema spec caused fair-agent 27/28 failures | `entire-report.txt:75-76,119-121`, `test_outputs.py:477` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 50, 51, 52, 53, 54 |
| **UNCHECK** | 21, 27, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Build subcommand writes `/app/output/wcs-atlas.json` | `test_atlas_writes_output_path` | covered | `instruction.md:3`, `test_outputs.py:420-424` |
| Keyword snapshot `/app/var/wcs-keyword-snapshot.json` | `test_keyword_snapshot_written` | covered | `instruction.md:3`, `test_outputs.py:305-313` |
| TAN/SIN corner RA/Dec vs reference | `test_tan_corners_match_reference`, `test_sin_projection_family` | covered | `test_outputs.py:266-294` |
| CONTINUE merge / hidden CONTINUE CRVAL | `test_hidden_continue_crval_tb3`, `test_hidden_continue_crval_value` | covered | `test_outputs.py:364-382` |
| HIERARCH in snapshot | `test_hidden_hierarch_snapshot_keyword` | covered | `test_outputs.py:395-402` |
| PC matrix composition | `test_pc_skew_matrix_corners`, `test_hidden_pc_sin_projection` | covered | `test_outputs.py:296-303,384-393` |
| Corner sort RA then Dec | `test_corners_sorted_by_ra_dec` | covered | `test_outputs.py:277-283` |
| NAXIS=0 → naxis1/naxis2 export 1 | `test_header_only_naxis_zero` | covered | `atlas-schema.md:9`, `test_outputs.py:332-338` |
| TB3_FITS_PATH override | `test_tb3_overrides_positional_path`, `test_hidden_continue_crval_tb3` | covered | `instruction.md:7`, `test_outputs.py:364-418` |
| Idempotent byte-identical rebuild | `test_build_idempotent_bytes` | covered | `instruction.md:9`, `test_outputs.py:322-330` |
| Missing file non-zero exit | `test_build_missing_file_fails` | covered | `test_outputs.py:457-461` |
| Ingest stamp path | `test_ingest_stamp_written` | covered | `test_outputs.py:404-409` |
| Fingerprint: lowercase hex digest | `test_fingerprint_stable_and_non_empty` | **gap** | `atlas-schema.md:17` vs `test_outputs.py:477` requires `len==16` |
| Axis midpoint coordinates | `test_axis_midpoints_count` | partial (count only) | `test_outputs.py:347-352` |
| Pixel scale magnitude | `test_pixel_scale_positive` | partial (positive only) | `test_outputs.py:340-345` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1-12, spec alignment |
| `task.toml` | #42-45, milestone N/A |
| `environment/Dockerfile` | #13-20, #50-53 |
| `environment/requirements.lock` | #14 |
| `environment/docs/atlas-schema.md` | Blocker 1, NAXIS adjudication |
| `environment/docs/keyword-snapshot-schema.md` | Fingerprint schema |
| `environment/src/atlas_writer.cpp` | FNV-1a baseline behavior |
| `tests/test.sh` | #20, #24-26 |
| `tests/test_outputs.py` | #27-31, spec alignment, fingerprint |
| `solution/solve.sh` | #22-23 |
| `entire-report.txt` | Agent stats, rubric, external claims |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate fits-wcs-sky-atlas-generator2/
Summary: 0 error(s), 29 warning(s), 2 info
```

Warnings are mostly false-positive docstring detections on class methods; all tests have docstrings.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 60.0% (3/5) | 2 failures other |
| terminus-claude-opus-4-8 | 60.0% (3/5) | 1 timeout, 1 other |
| oracle | 100.0% (3/3) | per platform report |
| nop | 0.0% | expected |

| Metric | Value |
|--------|-------|
| Worst-model rate | 60.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Platform classified | medium |
| Tier match (#45) | informational only — CHECK #45 per policy |

**Rubric positive points:** 29/40 (PASS). **Format:** flat non-milestone list under `# Rubrics` header; no per-milestone `# Rubric N` blocks — correct for `number_of_milestones = 0`.

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `fits-wcs-sky-atlas-generator2`; regular (non-milestone) layout |
| 1 Instruction | ☑ | Clear WHAT; fingerprint under-specified in referenced schema |
| 2 Environment | ☑ | Digest-pinned gcc; tmux+asciinema; pytest in image; no tests/solution COPY |
| 3 Oracle | ☑ | Derives via copied impl + build; not executed locally |
| 4 Verifiers | ☑ | Canonical test.sh; 28 behavior tests; fingerprint gap |
| 5 Metadata | ☑ | allow_internet=false; cpp/cmake; category acceptable |
| 6 Rubric | ☑ | 29 pts, 4 negatives, flat format — not milestone rubric layout |
| 7 Agent evidence | ☑ | 60% worst-model; fingerprint 8/10; NAXIS 10/10 |
| 8 Fairness | ☑ | Fingerprint ambiguity drives unfair near-misses |
| 9 Long context | ☐ | N/A — no long_context subcategory |

---

## 9. Reviewer note (copy-paste to portal)

Really strong FITS/WCS work overall — the digest-pinned C++ environment, hidden CONTINUE/HIERARCH fixtures, independent Python reference checks, and deterministic rebuild coverage are all well thought out. The NAXIS=0 export behavior is now documented correctly in `atlas-schema.md` and lines up with the tests. One thing to fix before acceptance: the fingerprint field. The schema only says “lowercase hex digest,” but the grader requires exactly 16 characters (matching the FNV-1a behavior in the baseline stub). Two near-perfect agent runs failed 27/28 because they reasonably switched to a 64-character SHA-256 hex digest. Please document the required fingerprint algorithm and length in `atlas-schema.md`, or align the test with whatever digest format you intend to specify.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Alignment/Coverage Issues | yes | 1 |
| Instruction Styling | yes | 1 |
| Environment | no | — |
| Rubric | no | — |
| Pinning Issues | no | — |
| Metadata Issues | no | — |
| Task Difficulty | no | — |
| Milestones | no | — |
