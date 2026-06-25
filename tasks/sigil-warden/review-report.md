# Terminus Review Report: sigil-warden

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | fail (validator false positives; see §7) |
| **Oracle** | pass (report: 100% 3/3; not re-run locally) |
| **CHECK count** | 43 |
| **UNCHECK count** | 12 |

**Error categories (internal):** Instruction Styling, Test Alignment/Coverage Issues, Rubric

**Decision (concise):** Milestone layout, digest-pinned Go Dockerfile, offline verifier setup, tests/solution exclusion, oracle pass rate, and Hard calibration are solid. Two real High blockers remain: (1) SPEC.md describes third-party/root CLI keys as 32-byte while M1–M3 vectors use valid 16-byte hex keys and the oracle accepts any hex length — this systematically misled agents; (2) the portal rubric has only three `# Rubric N` blocks for a four-milestone task, with `# Rubric 3` covering M4 legacy forgery instead of M3 third-party caveats, and no `# Rubric 4`.

**Insights (concise):**

- 8/9 agent trials failed M1–M3 primarily on self-imposed `len(key)==32` validation after reading SPEC.md §2.6 L109 and v0 §3 L164–165; oracle `mustHex()` has no length check (`warden.go:69–74`).
- M4 length-extension was solved in 7/9 trials — cryptographic reasoning is fair; the ceiling is the key-length spec gap, not task difficulty.
- Automated `validate`/`review` errors on Dockerfile COPY and `[[steps]]` count are false positives from comment text, not real defects.
- Pip packages are pinned (`pytest==8.3.4`, `pytest-json-ctrf==0.5.2`); `#14` automation fails on multi-line `pip install` continuation only.
- Minor non-blocker: `cidr_rejects_malformed_ip` tests `010.0.0.1` without explicit SPEC backing (Low).

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Instruction Styling, Test Alignment/Coverage Issues | #27, #55 | SPEC.md implies 32-byte CLI keys (`tpKey`, v0 server key) but M1–M3 test vectors use 16-byte hex keys; oracle accepts any valid hex length | `environment/app/SPEC.md:109,164–165,198`; `steps/milestone_1/tests/named_m1.json:3` (`00112233445566778899aabbccddeeff` = 16 B); `steps/milestone_3/tests/named_m3.json:14,24` (`tpkey` 16 B); `steps/milestone_1/solution/warden.go:69–74` (`mustHex` no length check); `entire-report.txt:72–76,106` (8/9 trials, same bug) | Clarify in SPEC.md §4 that v1 `--key` / `--tpkey` accept any even-length hex byte string (no fixed input length); keep v0 gateway key explicitly 32 bytes for M4 only. Optionally normalize vectors to 32-byte keys. |
| 2 | High | Rubric | #32–#39 | Portal rubric incomplete for 4 milestones: only `# Rubric 1–3`; `# Rubric 3` is M4 legacy forgery content; no M3 third-party caveat rubric; no `# Rubric 4` | `entire-report.txt:478–507` (`# Rubric 3` lines 498–506 = length-extension/M4); `task.toml:13` (`number_of_milestones = 4`); `docs/guidelines/rubrics.md:49–58` (one `# Rubric N` per milestone) | Add `# Rubric 3` for M3 (mint-third, discharge, bind, verify with discharges); move current `# Rubric 3` to `# Rubric 4`; ≥1 negative per block; remove `/app/examples/` reference (path does not exist). |

*No other High blockers found on re-audit.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | SPEC.md 32-byte key text mismatches M1–M3 16-byte hex vectors; agents added strict 32-byte validation (ChatGPT / entire-report) | **Agree** | `SPEC.md:109` ("32-byte key `tpKey`"); `named_m1.json:3` 32 hex chars; `warden.go:69–74`; agent failure analysis `entire-report.txt:72–76,122` |
| 2 | Portal rubric missing M3 block; `# Rubric 3` is M4; need `# Rubric 4` (ChatGPT) | **Agree** | `entire-report.txt:478–507`; M3 scope `steps/milestone_3/instruction.md`; M4 scope `steps/milestone_4/instruction.md` |
| 3 | Milestone layout, Dockerfile pinning, offline verifier, anti-cheat, oracle, Hard calibration solid (ChatGPT) | **Agree** | `environment/Dockerfile:1,15–18,27`; `environment/.dockerignore:11–12`; `steps/milestone_4/tests/test_m4.py` (hidden V0_KEY); `entire-report.txt:1–11` (oracle 100%, worst 20%) |
| 4 | `behavior_in_task_description` FAIL — instructions too terse vs tests (entire-report LLMaJ) | **Disagree** as blocker | M1 `instruction.md` names `/app/SPEC.md` as "the contract"; SPEC.md §4 documents CLI, stdin, output format; deferral is intentional for milestone tasks |
| 5 | `cidr_rejects_malformed_ip` phantom spec (`010.0.0.1`) (entire-report test quality) | **Partially agree** | `named_m1.json:21–25`; `SPEC.md:68` ("IPv4") without leading-zero rule; Low severity only — idiomatic Go rejects it |
| 6 | Non-canonical base image warning (entire-report) | **Disagree** as blocker | `Dockerfile:1` digest-pinned `golang:1.24-bookworm`; Go compile-at-runtime justifies non-ubuntu base |
| 7 | Automated validate: `number_of_milestones != [[steps]]` (validate output) | **Disagree** | `task.toml:12–13` comment contains `[[steps]]` string; 4 actual `[[steps]]` blocks at L33,43,53,63 |
| 8 | Automated validate: Dockerfile COPY solution/tests (validate output) | **Disagree** | `Dockerfile:26` comment "Never copy solution/ or tests/." matches `COPY\s+.*\bsolution\b` regex falsely; only `COPY app/ /app/` at L27 |
| 9 | Automated review blocker `#14` unpinned pip (review script) | **Disagree** | `Dockerfile:16–18` pins `pytest==8.3.4` and `pytest-json-ctrf==0.5.2` on continuation lines |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | 4 milestone instructions, ~1 sentence each | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Natural prompt tone | Terse engineering voice, not LLM spec dump | `steps/milestone_1/instruction.md` |
| 3 | CHECK | No excessive markdown | Plain prose, no ##/tables | milestone instructions |
| 4 | CHECK | No step-by-step HOW | States goals only; defers crypto detail to SPEC | milestone instructions |
| 5 | CHECK | No hints/strategies | WHAT to build, not attack walkthrough | milestone instructions |
| 6 | CHECK | No design-doc tables | None in instructions | — |
| 7 | CHECK | Well specified | Paths + SPEC.md as contract | `steps/milestone_1/instruction.md`; `environment/app/SPEC.md` |
| 8 | CHECK | Interesting | Real capability-token + length-extension security work | task scope |
| 9 | CHECK | Unique | No duplicate found in review corpus | manual assessment |
| 10 | CHECK | Absolute paths | `/app/warden`, `/app/SPEC.md`, `/app/forged.sigil` | milestone instructions |
| 11 | CHECK | Task name not in instruction | "sigil" used generically, not folder name | milestone instructions |
| 12 | CHECK | No canary string | None detected | milestone instructions |
| 13 | CHECK | No web fetch in env | Offline app only | `environment/` |
| 14 | CHECK | Pinned pip deps | `pytest==8.3.4`, `pytest-json-ctrf==0.5.2` | `environment/Dockerfile:16–18` |
| 15 | CHECK | Digest-pinned FROM | `@sha256:1a6d4452…` | `environment/Dockerfile:1` |
| 16 | CHECK | Context in environment/ | `COPY app/ /app/` only | `environment/Dockerfile:27` |
| 17 | CHECK | No ground truth in env | V0 key only in tests; captured token is input fixture | `environment/app/captured.sigil`; `test_m4.py` |
| 18 | CHECK | No dangerous Docker ops | No privileged/socket | `environment/Dockerfile` |
| 19 | CHECK | Compose mount safety | No compose file | — |
| 20 | CHECK | Verifier deps in image | pytest in image; test.sh no installs | `Dockerfile:15–18`; `steps/milestone_1/tests/test.sh` |
| 21 | CHECK | Oracle passes | 100% (3/3) per report | `entire-report.txt:11` |
| 22 | CHECK | Oracle offline | `go build` + stdlib only | `steps/milestone_*/solution/solve*.sh` |
| 23 | CHECK | Oracle not hardcoded | Builds `warden.go` / `forge.go` | `steps/milestone_1/solution/solve1.sh` |
| 24 | CHECK | reward.txt canonical | mkdir + pytest + 0/1 write | `steps/milestone_1/tests/test.sh` |
| 25 | CHECK | Same verifier for oracle/agent | No `/oracle` branching | test.sh files |
| 26 | CHECK | Binary rewards | 0 or 1 only | test.sh files |
| 27 | UNCHECK | Tests aligned with instructions | Key-length spec gap causes phantom 32-byte requirement | Blocker #1 |
| 28 | CHECK | Tests check correctness | HMAC byte-exact + crypto corpora | `steps/milestone_*/tests/test_m*.py` |
| 29 | CHECK | Behavior not implementation grep | Black-box subprocess to `/app/warden` | `test_m1.py:38–45` |
| 30 | CHECK | Not brittle string match | Byte-exact crypto outputs are required | test design |
| 31 | CHECK | Informative docstrings | All `test_*` documented | `test_m1.py` et al. |
| 32 | UNCHECK | ≥3 negative rubric criteria | 3 negatives exist but only 3/4 milestone blocks | `entire-report.txt:478–507` |
| 33 | CHECK | Valid rubric scores | Only ±1,2,3,5 used | portal rubric in report |
| 34 | UNCHECK | Rubric format | Missing `# Rubric 4`; `# Rubric 3` is wrong milestone | Blocker #2 |
| 35 | UNCHECK | Rubric precise | `# Rubric 1` cites `/app/examples/` — not in image | no `environment/app/examples/` |
| 36 | CHECK | Positive rubric phrasing | No "Agent does not…" positives | portal rubric |
| 37 | CHECK | Rubric no /tests/ refs | Clean | portal rubric |
| 38 | CHECK | Rubric no instruction.md refs | Clean | portal rubric |
| 39 | CHECK | Rubric no oracle/NOP refs | Clean | portal rubric |
| 40 | CHECK | Required files present | milestone layout complete | `task.toml`; `steps/` |
| 41 | CHECK | Clean parent directory | No stray jobs/README | `sigil-warden/` |
| 42 | CHECK | author fields | Present | `task.toml:6–7` |
| 43 | CHECK | Metadata complete | version, category, timeouts, etc. | `task.toml` |
| 44 | CHECK | Tags/languages/category fit | security; go/bash; relevant tags | `task.toml:8–18` |
| 45 | CHECK | Difficulty matches rates | hard vs 20% worst model | `entire-report.txt:6–7` |
| 46 | CHECK | steps/ milestone layout | 4 milestones under `steps/` | `task.toml`; directory tree |
| 47 | CHECK | solveN.sh per milestone | solve1–4.sh present | `steps/milestone_*/solution/` |
| 48 | CHECK | test_mN.py per milestone | test_m1–4.py present | `steps/milestone_*/tests/` |
| 49 | CHECK | Per-milestone scope | Each test file targets one milestone | test file headers |
| 50 | CHECK | Tests not in image | Only `COPY app/` | `environment/Dockerfile:27` |
| 51 | CHECK | Solution not in env | `.dockerignore` excludes solution/ | `environment/.dockerignore:11` |
| 52 | CHECK | Input not trivially mutable | M4 key test-only; signed corpora | `test_m4.py`; vector JSONL |
| 53 | CHECK | No unpinned git clone | None in Dockerfile | `environment/Dockerfile` |
| 54 | CHECK | Not too easy | Worst model 20% ≤80% | `entire-report.txt:6–7` |
| 55 | UNCHECK | Not unfair | Systematic spec-test key-length mismatch misled all agents | Blocker #1; `entire-report.txt:122` |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 33, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54 |
| **UNCHECK** | 27, 32, 34, 35, 55 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| v1 verify HMAC chain + caveats | `test_signature_integrity`, `test_corpus`, named M1 tests | covered | `test_m1.py`; `SPEC.md:51–58` |
| CLI `--key --now --path --method --ip` + `OK <scope>` | `run_verify()` harness | covered | `test_m1.py:38–45`; `SPEC.md:203–211` |
| Stdin token via `-` | `test_token_via_stdin` | covered | `SPEC.md:197`; `test_m1.py` |
| mint / attenuate byte-exact | `test_mint_matches_spec`, `test_attenuate_corpus` | covered | `test_m2.py`; `SPEC.md:213–214` |
| third-party mint/discharge/bind/verify | `test_mint_third_matches_spec`, `test_bind_matches_spec`, `test_end_to_end_pipeline` | covered | `test_m3.py`; `SPEC.md:107–157` |
| v0 length-extension forgery to `/app/forged.sigil` | `test_forged_is_accepted_for_admin` | covered | `steps/milestone_4/instruction.md`; `test_m4.py` |
| **CLI key input length** | all M1–M3 vector tests | **gap** | `SPEC.md:109,164` vs 16-byte keys in vectors; oracle accepts any hex |
| Leading-zero IP invalid for cidr | `cidr_rejects_malformed_ip` | phantom (Low) | `named_m1.json:21–25`; `SPEC.md:68` silent on leading zeros |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `environment/app/SPEC.md` | Blocker #1, #27, #55, spec alignment |
| `steps/milestone_1/tests/named_m1.json` | Blocker #1 key-length evidence |
| `steps/milestone_3/tests/named_m3.json` | Blocker #1 tpkey length |
| `steps/milestone_1/solution/warden.go` | Oracle key parsing (`mustHex`) |
| `environment/app/legacy/verify.go` | v0 32-byte key (M4 only, correct) |
| `environment/Dockerfile` | #14–#20, #50 |
| `task.toml` | #45–#49, milestone count |
| `entire-report.txt` | Agent stats, portal rubric, adjudication |
| `steps/milestone_*/instruction.md` | #1–#12, #7 |
| `steps/milestone_*/tests/test_m*.py` | #27–#31, alignment table |

---

## 7. Validation & agent performance

### Validation

```
ERROR: task.toml: number_of_milestones (4) != [[steps]] count (5)  ← FALSE POSITIVE (comment L12)
ERROR: dockerfile: Must not COPY solution/  ← FALSE POSITIVE (comment L26)
ERROR: dockerfile: Must not COPY tests/     ← FALSE POSITIVE (comment L26)
WARNING: pinned_dependencies: unpinned pip on continuation line  ← FALSE POSITIVE (== on L17–18)
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0.0% (0/5) | `entire-report.txt:7` |
| terminus-claude-opus-4-8 | 20.0% (1/5) | `entire-report.txt:6` |
| oracle | 100.0% (3/3) | `entire-report.txt:11` |

| Metric | Value |
|--------|-------|
| Worst-model rate | 20% |
| Observed tier | hard |
| Declared difficulty | hard |
| Tier match (#45) | yes |

---

## 8. Audit log

| Phase | Status | Notes |
|-------|--------|-------|
| 0 Scope & identity | ☑ | 4-milestone Go security task; report matches folder |
| 1 Instruction | ☑ | Terse; SPEC.md is normative contract |
| 2 Environment | ☑ | Digest-pinned Go image; tmux/asciinema; offline |
| 3 Oracle | ☑ | Builds real Go binaries; report 100% (not re-run) |
| 4 Verifiers | ☑ | Canonical test.sh; black-box crypto tests |
| 5 Metadata | ☑ | hard/security/go; 4 milestones |
| 6 Rubric | ☐ | Portal rubric incomplete — Blocker #2 |
| 7 LLMaJ & agent evidence | ☑ | Key-length pattern confirmed across 8/9 trials |
| 8 Novelty & fairness | ☐ | Unfair spec gap on key length — Blocker #1 |
| 9 Long context | N/A | Not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Structure, verifiers, digest-pinned Go Dockerfile, offline setup, anti-cheat (M4 hidden key), oracle pass rate, and Hard calibration all look solid. Fix first: SPEC.md §2.6/v0 wording makes agents enforce 32-byte `--key`/`--tpkey` while M1–M3 vectors use 16-byte hex and the reference accepts any hex length — clarify CLI key length rules (keep v0 gateway key at 32 bytes for M4 only). Second: add a proper `# Rubric 3` for third-party caveats and `# Rubric 4` for legacy forgery; current portal `# Rubric 3` is M4 content with no M3 rubric block.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Instruction Styling | yes | 1 |
| Test Alignment/Coverage Issues | yes | 1 |
| Rubric | yes | 2 |
| Exposing Hints/Answers | no | — |
| Oracle Solution Issues | no | — |
| Environment | no | — |
| Pinning Issues | no | — |
| Milestones | no | — |
| Task Difficulty | no | — |
| Metadata Issues | no | — |
