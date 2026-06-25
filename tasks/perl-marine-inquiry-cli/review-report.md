# Terminus Review Report: `perl-marine-inquiry-cli`

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | warn |
| **Oracle** | pass (per `entire-report.txt` 3/3; local oracle timed out at 300s) |
| **CHECK count** | 38 |
| **UNCHECK count** | 17 |

**Error categories (internal):** Test Alignment/Coverage Issues, Metadata Issues

**Decision (concise):** Two High blockers drive Revise. `test_inquire_sh_invokes_inquire_pl` enforces a literal `perl … inquire.pl` shell invocation that `instruction.md` never states — 7/8 agent trials in the external report failed only on this regex despite functionally correct Perl clients. `task.toml` declares `difficulty = "hard"` but worst-model pass rate is Claude **40%** (Medium tier 20–60%). ChatGPT’s blanket Accept and “metadata now matches Medium” claims are disproven by artifacts. Environment, anti-cheat, digest pinning, and pip deps are otherwise solid.

**Insights (concise):**

- External report `task_specification` FAIL and per-test `test_inquire_sh_invokes_inquire_pl` 3/10 pass rate confirm a systematic spec gap, not agent incompetence.
- ChatGPT Accept is wrong: `task.toml:8` still says `hard`; invoke-form requirement is unstated.
- Automated `./scripts/terminus review` false-positive on #14 (pip **is** `==`-pinned) and over-weighted #1 length / #31 docstrings as sole High blockers.
- Dossier `08_accusation_rules.md:49` states all four answer particulars in plain text — long-context reasoning reduces to reading one file; integration/Perl work remains substantial.
- Clean-room `conftest.py` design (rebuild DB, inject truth, re-run deliverable) is excellent anti-cheat.
- Rubric lines in `entire-report.txt:303-309` are portal UI only; no `rubric.txt` in task folder.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Test Alignment/Coverage Issues | #27, #55 | `test_inquire_sh_invokes_inquire_pl` requires regex `\bperl\b[^\n]*inquire\.pl` in `inquire.sh`, but instruction only requires HTTP/record/finding logic to run inside Perl — not this literal invocation form | `instruction.md:3`; `tests/test_outputs.py:73-77`; `entire-report.txt:56-66,84-92` | Add explicit normative text to `instruction.md`, e.g. ``inquire.sh` must invoke the Perl client as `perl /app/build/inquire.pl "$mode"` (shebang-only or variable-indirection invocations are not acceptable)` — **or** drop/relax the regex test to match the stated Perl-in-logic requirement |
| 2 | High | Metadata Issues | #45 | Declared `difficulty = "hard"` but worst-model pass rate is **40%** → Medium tier (20–60%) | `task.toml:8`; `entire-report.txt:6-7`; `docs/guidelines/difficulty.md:9-12` | Set `difficulty = "medium"` in `task.toml`, or rebalance task until worst-model ≤20% |

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | Accept — metadata matches Medium, digest-pinned Dockerfile, verifier deps in image, test.sh reward init, oracle passes, solid alignment (ChatGPT) | **Disagree** | `task.toml:8` still `hard`; `tests/test_outputs.py:73-77` unstated invoke regex; ChatGPT contradicts `entire-report.txt:47` task_specification FAIL |
| 2 | No High/Medium/Low severity issues (ChatGPT) | **Disagree** | Blockers #1–#2 above |
| 3 | Difficulty: HARD (entire-report header) | **Partially agree** (declared only) | Platform header reflects `task.toml`; observed worst-model 40% is Medium, not Hard |
| 4 | Claude 40%, GPT-5.5 0%, oracle 100% (entire-report) | **Agree** | `entire-report.txt:6-11` |
| 5 | Task Instruction Sufficiency FAIL — `test_inquire_sh_invokes_inquire_pl` spec gap | **Agree** | `instruction.md:3` vs `tests/test_outputs.py:75`; `entire-report.txt:56-92` |
| 6 | Agents pass 25/26 tests; failures are invoke-regex only (7/8 trials) | **Agree** | `entire-report.txt:50-66,104` |
| 7 | Cache-replay trial TAaHhEW failed runtime audit tests | **Agree** (secondary) | `entire-report.txt:68-71`; `tests/conftest.py:106-133` clean-room re-run |
| 8 | LLMaJ `behavior_in_task_description` / `behavior_in_tests` pass | **Partially agree** | `entire-report.txt:118-119`; LLMaJ missed invoke-regex gap that human/agent analysis caught |
| 9 | Anti-cheat robust; sealed truth injected at verify time | **Agree** | `tests/conftest.py:1-74`; `environment/Dockerfile:34-36` no tests/solution COPY |
| 10 | Answer in dossier `08_accusation_rules.md` reduces reasoning to reading | **Agree** (not blocker) | `environment/dossier/08_accusation_rules.md:49` lists all four particulars explicitly |
| 11 | Unpinned `perl` apt package (entire-report WARNING) | **Agree** (Low only) | `environment/Dockerfile:15`; quality check `entire-report.txt:123` accepts core apt unpinned |
| 12 | Non-canonical Ruby base justified (entire-report SUGGESTION) | **Agree** | `environment/Dockerfile:1` digest-pinned `ruby:3.3-slim-bookworm`; Rails requirement credible |
| 13 | Expected answer in test_outputs.py / conftest.py (entire-report WARNING) | **Agree** (by design) | `tests/test_outputs.py:43-48`; `tests/conftest.py:33-38`; harness keeps `/tests` off agent image |
| 14 | Test quality ROBUST / ACCEPT | **Partially agree** | Clean-room pattern excellent; invoke-regex test is unfair vs instruction |
| 15 | Automated review: #14 unpinned pip | **Disagree** | `environment/Dockerfile:24-27` `pytest==8.4.1`, `pytest-json-ctrf==0.3.5`, `requests==2.32.3` |
| 16 | Automated review: #1 instruction too long | **Partially agree** (not sole blocker) | `instruction.md` ~625 words + `##` schema sections; schemas are normative for structured output |
| 17 | Automated review: #31 22 missing docstrings | **Agree** (Medium, not blocking alone) | Only 4/26 `test_*` have docstrings e.g. `tests/test_outputs.py:80-82`; 22 lack per validate warnings |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | UNCHECK | Instruction concise | ~625 words + two `##` schema sections exceeds 3-paragraph guideline | `instruction.md`; `docs/guidelines/prompt-styling.md:7` |
| 2 | CHECK | Natural prompt tone | Engineer/mystery narrative, not LLM walkthrough | `instruction.md:1-9` |
| 3 | CHECK | No excessive markdown | `##` headers only for normative JSON schemas | `instruction.md:13-35` |
| 4 | CHECK | No step-by-step solve steps | States WHAT to build/deliver, not bug-by-bug guide | `instruction.md` |
| 5 | CHECK | No hints/solving strategies | Requirements without fix walkthrough | `instruction.md` |
| 6 | CHECK | No design-doc I/O tables | No input→output mapping tables | `instruction.md` |
| 7 | CHECK | Well specified | Clear deliverables, API workflow, schemas, anti-bypass rules | `instruction.md:1-35` |
| 8 | CHECK | Interesting | Perl + Rails API + long-context mystery investigation | task content |
| 9 | UNCHECK | Unique | Not verified against TB2/TB3/Edition 1 corpus | — |
| 10 | CHECK | Absolute paths only | `/app/build/`, `/app/output/`, `/app/api/`, `/app/dossier/` | `instruction.md` |
| 11 | CHECK | Task name not in instruction | No `perl-marine-inquiry-cli` string | `instruction.md` |
| 12 | CHECK | No canary string | None found | `instruction.md`, `environment/` |
| 13 | CHECK | No runtime web fetch in env | No curl/wget in env source | `environment/` |
| 14 | CHECK | Pinned pip deps | `pytest==8.4.1`, `pytest-json-ctrf==0.3.5`, `requests==2.32.3` | `environment/Dockerfile:24-27` |
| 15 | CHECK | Base image digest-pinned | `ruby:3.3-slim-bookworm@sha256:e76733e…` | `environment/Dockerfile:1` |
| 16 | CHECK | Context in environment/ only | COPY `api/`, `dossier/`, `data/` only | `environment/Dockerfile:34-36` |
| 17 | CHECK | No ground-truth answers in env | Shipped DB has empty `truth`; sealed answer in tests only | `tests/conftest.py:3-7`; `environment/api/db/seed.sql` |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN/docker.sock | `environment/Dockerfile` |
| 19 | CHECK | Compose doesn't alter Harbor mounts | No `docker-compose.yaml` | task root |
| 20 | CHECK | Verifier deps in image; test.sh no installs | pytest in Dockerfile; test.sh only runs pytest | `environment/Dockerfile:24-27`, `tests/test.sh:10-13` |
| 21 | CHECK | Oracle passes consistently | 100% (3/3) per report | `entire-report.txt:11` |
| 22 | CHECK | Oracle no runtime network | `solve.sh` copies sources and runs locally | `solution/solve.sh:29-37` |
| 23 | CHECK | Oracle derives results | `inquire.pl` drives API, derives finding from records | `solution/src/inquire.pl`; quality check `entire-report.txt:126` |
| 24 | CHECK | reward.txt + failure path | Writes 0 first; 1/0 after pytest | `tests/test.sh:3,16-19` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching in tests | `tests/test.sh`, `tests/test_outputs.py` |
| 26 | CHECK | Binary rewards 0/1 | `echo 0` / `echo 1` only | `tests/test.sh:3,17-19` |
| 27 | UNCHECK | Tests aligned with instructions | `test_inquire_sh_invokes_inquire_pl` tests unstated literal invoke form | `instruction.md:3`; `tests/test_outputs.py:73-77` |
| 28 | CHECK | Tests check correctness | Verdict sound/unsound, particulars, API audit, determinism | `tests/test_outputs.py:137-310` |
| 29 | UNCHECK | Behavior not implementation grep | Greps `inquire.sh`/`inquire.pl` source for `perl`, `HTTP::Tiny`, DB paths | `tests/test_outputs.py:73-88,284-290` |
| 30 | CHECK | No brittle exact strings | Flexible JSON field checks; sealed truth from conftest | `tests/test_outputs.py` |
| 31 | UNCHECK | Informative test docstrings | 22/26 `test_*` lack docstrings | `tests/test_outputs.py:60-320`; validate warnings |
| 32 | UNCHECK | Rubric ≥3 negatives | N/A — no rubric file in task folder | — |
| 33 | UNCHECK | Rubric score set | N/A | — |
| 34 | UNCHECK | Rubric format | N/A | — |
| 35 | UNCHECK | Rubric detailed | N/A | — |
| 36 | UNCHECK | Rubric positive language | N/A | — |
| 37 | UNCHECK | Rubric no /tests/ refs | N/A | — |
| 38 | UNCHECK | Rubric no metadata refs | N/A | — |
| 39 | UNCHECK | Rubric no oracle/NOP | N/A | — |
| 40 | CHECK | Required files present | Dockerfile, solve.sh, test.sh, instruction, task.toml | task root |
| 41 | CHECK | Clean parent directory | No stray jobs/README at task root | task root |
| 42 | CHECK | author_name/email | Present | `task.toml:6-7` |
| 43 | CHECK | Other metadata fields | timeouts, `allow_internet=false`, resources | `task.toml:24-38` |
| 44 | CHECK | Tags/languages/category applicable | `perl`, `rails`, `long_context`, `api_integration`, `games` fit | `task.toml:9-19` |
| 45 | UNCHECK | Difficulty matches pass rates | Declared `hard`; worst-model Claude 40% → Medium | `task.toml:8`; `entire-report.txt:6` |
| 46 | UNCHECK | steps/ layout | N/A — `number_of_milestones = 0` | `task.toml:13` |
| 47 | UNCHECK | solveN.sh per milestone | N/A | `task.toml:13` |
| 48 | UNCHECK | test_mN.py per milestone | N/A | `task.toml:13` |
| 49 | UNCHECK | Milestone scope | N/A | `task.toml:13` |
| 50 | CHECK | Tests not in image | No COPY tests/ in Dockerfile | `environment/Dockerfile:34-36` |
| 51 | CHECK | Solution not in environment | No solution/ COPY; truth injected at verify | `environment/Dockerfile`; `tests/conftest.py:49-74` |
| 52 | CHECK | Agent can't trivially cheat | Clean-room DB rebuild + audit log checks | `tests/conftest.py:106-133`; `tests/test_outputs.py:254-281` |
| 53 | CHECK | Git repos pinned | No git clone in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy (>80% worst model) | Worst model 40% ≤ 80% | `entire-report.txt:6` |
| 55 | UNCHECK | Not too hard/unfair | Systematic failure on unstated `perl inquire.pl` regex; agents pass 25/26 otherwise | `entire-report.txt:47-107`; `tests/test_outputs.py:73-77` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 30, 40, 41, 42, 43, 44, 50, 51, 52, 53, 54 |
| **UNCHECK** | 1, 9, 27, 29, 31, 32, 33, 34, 35, 36, 37, 38, 39, 45, 46, 47, 48, 49, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| Deliver `/app/build/inquire.sh` and `/app/build/inquire.pl` | `test_inquire_sh_present`, `test_inquire_pl_present_and_parses` | covered | `instruction.md:3`; `tests/test_outputs.py:60-70` |
| HTTP/record/finding logic runs inside Perl | `test_inquire_pl_holds_the_logic` | covered | `instruction.md:3`; `tests/test_outputs.py:80-88` |
| `inquire.sh` must invoke `perl … inquire.pl` literally | `test_inquire_sh_invokes_inquire_pl` | **gap (phantom)** | Not in `instruction.md`; enforced at `tests/test_outputs.py:75` |
| `inquire.sh play` → `/app/output/finding.json` | `test_finding_json_present` | covered | `instruction.md:3`; `tests/test_outputs.py:91-92` |
| `inquire.sh wrong` → `/app/output/wrong_finding.json` | `test_wrong_finding_unsound` | covered | `instruction.md:3`; `tests/test_outputs.py:200-215` |
| finding.json schema (all keys) | `test_finding_has_inquiry_id`, `test_finding_echoes_*`, `test_final_state_shape`, `test_actions_*` | covered | `instruction.md:13-27`; `tests/test_outputs.py:104-194` |
| wrong_finding.json schema | `test_wrong_finding_*` | covered | `instruction.md:29-35`; `tests/test_outputs.py:218-239` |
| Correct four particulars from record | `test_finding_particulars_correct` | covered | `instruction.md:7`; `tests/test_outputs.py:137-145` |
| Required records drawn; pass completed | `test_required_records_drawn`, `test_pass_completed` | covered | `instruction.md:7`; `tests/test_outputs.py:121-134` |
| Deterministic play reruns | `test_outputs_deterministic_on_rerun` | covered | `instruction.md:11`; `tests/test_outputs.py:293-309` |
| Do not read `/app/api/db` | `test_client_does_not_bypass_db` | covered | `instruction.md:9`; `tests/test_outputs.py:284-290` |
| Drive API at runtime; single finding | `test_client_drove_api_at_runtime`, `test_play_made_single_finding` | covered | `instruction.md:5`; `tests/test_outputs.py:254-270` |
| Leave port 3000 free on exit | `test_api_server_not_lingering` | covered | `instruction.md:3`; `tests/test_outputs.py:312-320` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `instruction.md` | #1, #3, #7, #10, blocker 1, §5 |
| `task.toml` | #44, #45, blocker 2 |
| `environment/Dockerfile` | #14, #15, #20, #50 |
| `tests/test.sh` | #20, #24 |
| `tests/test_outputs.py` | #27, #29, #31, blocker 1, §5 |
| `tests/conftest.py` | #17, #51, #52 |
| `environment/dossier/08_accusation_rules.md` | adjudication #10 |
| `solution/solve.sh` | #21, #22, #23 |
| `solution/src/inquire.sh` | blocker 1 (oracle uses `perl … inquire.pl`) |
| `entire-report.txt` | #45, #54, #55, agent stats, adjudication |

---

## 7. Validation & agent performance

### Validation

```
./scripts/terminus validate perl-marine-inquiry-cli/
Summary: 0 error(s), 25 warning(s), 2 info
```

Key warnings: 22 missing test docstrings; long_context corpus size verify manually; no `.dockerignore`.

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-claude-opus-4-8 | 40.0% (2/5) | Worst model |
| terminus-gpt5-5 | 0.0% (0/5) | |
| oracle | 100.0% (3/3) | Per report |
| nop | 0.0% (0/1) | |

| Metric | Value |
|--------|-------|
| Worst-model rate | 40.0% |
| Observed tier | medium |
| Declared difficulty | hard |
| Tier match (#45) | no |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | Folder `perl-marine-inquiry-cli` matches report; regular layout |
| 1 Instruction | ☑ | Spec gap on shell invoke form; schemas normative |
| 2 Environment | ☑ | Digest-pinned Ruby base; tmux/asciinema; no tests/solution COPY |
| 3 Oracle | ☑ | Derives via API; 100% per report; local run timed out |
| 4 Verifiers | ☑ | Invoke-regex misalignment; missing docstrings; some source grep |
| 5 Metadata | ☑ | `hard` vs 40% worst-model mismatch |
| 6 Rubric | ☑ | N/A — portal rubric only in report |
| 7 LLMaJ & agent evidence | ☑ | Instruction sufficiency FAIL confirmed; ChatGPT Accept rejected |
| 8 Novelty & fairness | ☑ | Unfair invoke test; otherwise strong anti-cheat |
| 9 Long context | ☑ | ~204 KB dossier (~50k tokens); answer grepable in `08_accusation_rules.md` |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. The verifier enforces a literal `perl … inquire.pl` invocation in `inquire.sh` (`tests/test_outputs.py:75`) that `instruction.md` never states — agent trials passed 25/26 tests and failed only on this regex. Either document the required invoke form in the instruction or relax the test. Also update `task.toml` `difficulty` from `hard` to `medium` (worst-model Claude pass rate 40%). Environment pinning, anti-cheat clean-room design, and oracle quality are otherwise strong.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Test Alignment/Coverage Issues | yes | 1 |
| Metadata Issues | yes | 2 |
| Instruction Styling | no | — (length borderline; not sole blocker) |
| Pinning Issues | no | pip pinned; unpinned `perl` apt accepted |
| Environment | no | — |
| Oracle Solution Issues | no | — |
| Test Build Issues | no | — |
| Rubric | no | N/A |
