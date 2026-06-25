# Terminus Review Report: `seismic-fdtd-csharp`

**Generated:** 2026-06-24  
**Task path:** `/Users/ayushrai/Downloads/Airdawgs-review-Terminus2/seismic-fdtd-csharp`

---

## 1. Executive summary

| Field | Value |
|-------|-------|
| **Disposition** | Revise |
| **Confidence** | High |
| **Validation** | fail (2 errors, 46 warnings) |
| **Oracle** | pass (per `entire-report.txt`; not re-run locally — Harbor milestone layout) |
| **CHECK count** | 54 |
| **UNCHECK count** | 1 |

**Error categories (internal):** Metadata Issues

**Decision (concise):** One real blocker: `task.toml` has forbidden top-level `[agent]` and `[verifier]` sections on a milestone task (`docs/task-requirements.md` §Milestone Tasks; `./scripts/terminus validate` errors). Remove lines 24–28; per-milestone `[steps.agent]` / `[steps.verifier]` already exist. ChatGPT Accept and prior human findings about RTM fakeability, vz injection, BOM, and illumination/SNR gaps are **stale** — artifacts now cover them. Difficulty `hard` is correct (worst-model GPT-5.5 0%).

**Insights (concise):**

- External report item 5 (add top-level timeouts) is **wrong** — validator requires their **removal**.
- `test_m*.py` docstrings exist; validate false-positives on `-> None:` type hints (#31).
- M3 RTM anti-cheat: `test_rtm_image_follows_illumination_footprint` checks aperture taper, near-zero outside footprint, no energy above source, and wavelet sidelobe polarity in ≥10 central columns.
- BOM requirement is normative in `imaging_schema.md:3-6`; agent BOM failures are attention, not a spec gap.
- Claude 80% does not change tier — worst model 0% → Hard per `docs/guidelines/difficulty.md`.

---

## 2. Main blockers

| # | Severity | Error category | Checkbox | Finding | Proof | Required fix |
|---|----------|----------------|----------|---------|-------|--------------|
| 1 | High | Metadata Issues | #43 | Milestone `task.toml` must not have top-level `[agent]` / `[verifier]` | `task.toml:24-28`; `docs/task-requirements.md:107`; `validate` ERROR | Delete `[verifier]` and `[agent]` blocks at lines 24–28; keep only per-step `[steps.agent]` / `[steps.verifier]` |

*All other automated “blockers” from `./scripts/terminus review` were re-audited and downgraded — see adjudication §3.*

---

## 3. External findings adjudication

| # | Claim (source) | Verdict | Proof |
|---|----------------|---------|-------|
| 1 | M3 RTM is fakeable via synthetic bright band (`entire-report.txt:2`) | **Disagree** | `test_m3.py:80-115` — footprint taper (central >4× edges), outside-aperture near-zero (central >20× outside), no band above source, sidelobe polarity in ≥10/21 central columns |
| 2 | M2 vz injection never tested (`entire-report.txt:4`) | **Disagree** | `sim_homo_vz.json:4` `"kind": "vz"`; `test_m2.py:137-153` `test_vz_injection_direct_arrival` |
| 3 | CSV BOM not documented (`entire-report.txt:6`) | **Disagree** | `imaging_schema.md:3-6` — “plain UTF-8 text with no byte-order mark … `new UTF8Encoding(false)`” |
| 4 | M2 PML/attenuation thresholds too loose (`entire-report.txt:8`, test-quality review) | **Partially agree** | `test_m2.py:109,118,135` — bands are wide; observation only, not a fairness blocker — combined physics tests still require working FDTD |
| 5 | Elastic path under-exercised (`entire-report.txt:8`) | **Disagree** | `sim_homo_swave.json`; `test_m2.py:155-179` `test_elastic_shear_arrival` compares elastic vs acoustic late-window energy |
| 6 | QC/SNR and illumination only weakly checked (`entire-report.txt:10`) | **Disagree** | `test_m3.py:198-208` exact illumination counts; `test_m3.py:210-223` SNR recomputed from gather; `test_m3.py:225-262` exact sweep illumination map |
| 7 | Add top-level `[verifier]`/`[agent]` to task.toml (`entire-report.txt:10`) | **Disagree** | `validate_task.py:250-257` ERROR if present; `docs/task-requirements.md:107` |
| 8 | Fault-depth clamping undocumented (`entire-report.txt:10`) | **Disagree** | `model_schema.md:30-32` — negative lookup depth → topmost layer |
| 9 | ChatGPT Accept — no issues (`user`) | **Partially agree** | Substance sound after fixes; **one metadata blocker remains** (#43) |
| 10 | Prior fairness gaps “appear addressed” (`user`) | **Agree** | vz fixture, RTM structure, BOM schema, QC/SNR, illumination counts — all present in current artifacts |
| 11 | Hard calibration supported by GPT-5.5 0% (`user`, `entire-report.txt:13-19`) | **Agree** | `entire-report.txt:18-19` GPT 0/5; worst-model 0% → Hard tier |
| 12 | Instruction sufficiency FAIL for BOM (`entire-report.txt:77`) | **Disagree** | Schema documents BOM-free UTF-8; failures are agent default `Encoding.UTF8`, not missing spec |
| 13 | LLMaJ `behavior_in_tests` PASS (`entire-report.txt:156`) | **Agree** | Cross-checked M1–M3 test coverage against instructions + schema docs |
| 14 | Non-canonical Docker base (`entire-report.txt:193-211`) | **Agree (non-blocker)** | `Dockerfile:1-4` digest-pinned Debian + pinned SDK 8.0.414; justified comment |

---

## 4. Portal checkbox decisions (all 55)

| # | Decision | Label | Reason | Proof |
|---|----------|-------|--------|-------|
| 1 | CHECK | Instruction concise | Each milestone instruction ≤3 paragraphs (~197/175/235 words); combined heuristic N/A | `steps/milestone_*/instruction.md` |
| 2 | CHECK | Natural prompt tone | Engineer voice; no synthetic anti-patterns | `steps/milestone_*/instruction.md` |
| 3 | CHECK | No excessive markdown | No ##/###/tables in instructions | `steps/milestone_*/instruction.md` |
| 4 | CHECK | No step-by-step HOW | “then run simulate” states artifact dependency (WHAT), not implementation steps | `milestone_2/instruction.md:4` |
| 5 | CHECK | No hints/strategies | Normative schemas in `/app/docs/` define contracts, not solve walkthroughs | `environment/docs/*.md` |
| 6 | CHECK | No design-doc I/O tables | None in instructions | — |
| 7 | CHECK | Well specified | Measurable outputs, schema refs, absolute paths | `steps/milestone_*/instruction.md` |
| 8 | CHECK | Interesting | Real geophysics / FDTD / RTM engineering | — |
| 9 | CHECK | Unique | C# seismic FDTD milestone task; no duplicate in corpus | — |
| 10 | CHECK | Absolute paths only | `/app/...` throughout | `steps/milestone_*/instruction.md` |
| 11 | CHECK | Task name not in instruction | No “seismic-fdtd-csharp” string | — |
| 12 | CHECK | No canary string | None detected | — |
| 13 | CHECK | No runtime web fetch in env | Data/fixtures shipped locally | `environment/` |
| 14 | CHECK | Pinned pip deps | `pytest==8.4.1`, `numpy==2.2.6`, etc.; pip bootstrap unpinned only (standard) | `Dockerfile:45-49` |
| 15 | CHECK | FROM digest-pinned | `@sha256:4724b8cc...` | `Dockerfile:4` |
| 16 | CHECK | Build context in environment/ | All COPY from `environment/` | `Dockerfile:53-93` |
| 17 | CHECK | No ground truth in env | Schemas are contracts; no precomputed simulation outputs | `Dockerfile` COPY list |
| 18 | CHECK | No dangerous Docker ops | No privileged/SYS_ADMIN/docker.sock | `Dockerfile` |
| 19 | CHECK | Compose does not alter harbor mounts | No docker-compose.yaml | — |
| 20 | CHECK | Verifier deps in image | pytest/numpy/scipy in Dockerfile; test.sh offline | `Dockerfile:43-49`, `steps/*/tests/test.sh` |
| 21 | CHECK | Oracle passes | 100% (3/3) per report | `entire-report.txt:23` |
| 22 | CHECK | Oracle no runtime network | solve scripts write/compile C# locally | `steps/milestone_*/solution/solve*.sh` |
| 23 | CHECK | Oracle not hardcoded | Multi-file C# FDTD implementation via heredocs | `solve1.sh`, `solve2.sh`, `solve3.sh` |
| 24 | CHECK | reward.txt canonical block | mkdir, default 0, pytest, conditional 1/0 | `steps/milestone_*/tests/test.sh` |
| 25 | CHECK | Same verifier logic oracle/agent | No `/oracle` branching | `test_m*.py` |
| 26 | CHECK | Binary rewards | 0 or 1 only | `test.sh` |
| 27 | CHECK | Tests aligned with instructions | All instruction + schema behaviors covered | §5 table |
| 28 | CHECK | Tests check correctness | Physics: travel times, energy ratios, SNR, illumination | `test_m2.py`, `test_m3.py` |
| 29 | CHECK | Behavior not implementation grep | No source-code grep in verifiers | `test_m*.py` |
| 30 | CHECK | Not brittle where avoidable | Physics windows/tolerances; exact CSV header required by schema | `imaging_schema.md:51-55` |
| 31 | CHECK | Informative test docstrings | All `test_*` have docstrings; validator misses `-> None:` | `test_m1.py:39-40`, `test_m2.py:47-48`, `test_m3.py:57-58` |
| 32 | CHECK | Rubric ≥3 negatives | 4+ negatives per rubric block | `entire-report.txt:545-581` |
| 33 | CHECK | Rubric scores in allowed set | ±1,2,3,5 only | `entire-report.txt:545-581` |
| 34 | CHECK | Rubric format Agent …, ±N | Correct format | `entire-report.txt:545-581` |
| 35 | CHECK | Rubric criteria detailed | Specific agent behaviors | `entire-report.txt:545-581` |
| 36 | CHECK | Rubric positive language | Standard Terminus phrasing | `entire-report.txt:545-581` |
| 37 | CHECK | Rubric no /tests/ refs | None | `entire-report.txt:545-581` |
| 38 | CHECK | Rubric no instruction.md refs | Points to `/app/docs/` only | `entire-report.txt:545-581` |
| 39 | CHECK | Rubric no oracle/NOP mentions | None | `entire-report.txt:545-581` |
| 40 | CHECK | Required files present | Dockerfile, steps/, task.toml | task tree |
| 41 | CHECK | Clean parent directory | No stray jobs/README | — |
| 42 | CHECK | author_name/email | Present | `task.toml:4-5` |
| 43 | UNCHECK | Required metadata complete | Forbidden top-level `[agent]`/`[verifier]` on milestone task | `task.toml:24-28` |
| 44 | CHECK | Tags/languages/category match | csharp, scientific-computing, fdtd tags | `task.toml:7-11` |
| 45 | CHECK | Difficulty matches pass rates | `hard` vs worst-model 0% (GPT-5.5) | `entire-report.txt:18-19` |
| 46 | CHECK | steps/ milestone layout | 3 milestones under `steps/` | `task.toml:14`, tree |
| 47 | CHECK | solveN.sh per milestone | solve1/2/3.sh + wrappers | `steps/milestone_*/solution/` |
| 48 | CHECK | test_mN.py per milestone | test_m1/2/3.py | `steps/milestone_*/tests/` |
| 49 | CHECK | Milestone scope isolated | Each test file covers one milestone | `test_m*.py` class names |
| 50 | CHECK | Tests not in image | No COPY tests/solution | `Dockerfile` |
| 51 | CHECK | Solution not accessible | Not copied to image | `Dockerfile` |
| 52 | CHECK | Agent cannot trivially cheat | Physics-based checks; outputs under `/tmp` | `test_m*.py` |
| 53 | CHECK | No unpinned git clone | SDK via pinned dotnet-install.sh 8.0.414 | `Dockerfile:37-39` |
| 54 | CHECK | Not too easy | Worst-model 0% ≪ 80% threshold | `entire-report.txt:18-19` |
| 55 | CHECK | Not unfair | BOM/vz/RTM/QC documented; agent failures are implementation | `imaging_schema.md:3-6`, tests |

**Quick copy-paste**

| | Numbers |
|---|---------|
| **CHECK** | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55 |
| **UNCHECK** | 43 |

---

## 5. Spec ↔ test alignment

| Requirement (instruction / dossier) | Test(s) | Status | Proof |
|-------------------------------------|---------|--------|-------|
| M1: five float32 NPY grids `(nz,nx)` | `test_model_arrays_present_and_shape` | covered | `test_m1.py:39-48` |
| M1: layer depth lookup | `test_layer_assignment_by_depth` | covered | `test_m1.py:50-63` |
| M1: salt polygon override | `test_salt_polygon_overrides_layer` | covered | `test_m1.py` |
| M1: fault hanging-wall + additive throws | `test_fault_*`, `test_multiple_faults_stack_additively` | covered | `test_m1.py` |
| M1: fault-before-salt precedence | `test_fault_then_salt_precedence` | covered | `test_m1.py` |
| M1: three wavelet types + normalization | `test_source_*`, `test_all_sources_normalized` | covered | `test_m1.py` |
| M2: shot_gather/time/snapshots outputs | `test_simulate_subcommand_*`, `test_snapshots_*` | covered | `test_m2.py` |
| M2: direct P arrival timing | `test_direct_arrival_travel_time` | covered | `test_m2.py:76-92` |
| M2: PML absorption | `test_pml_reduces_interior_energy_*` | covered | `test_m2.py:94-118` |
| M2: SLS attenuation `exp(-pi*f*dt/Q)` | `test_attenuation_amplitude_decay` | covered | `test_m2.py:120-135` |
| M2: vz source injection | `test_vz_injection_direct_arrival` | covered | `test_m2.py:137-153`, `sim_homo_vz.json` |
| M2: elastic shear (vs>0) | `test_elastic_shear_arrival` | covered | `test_m2.py:155-179` |
| M2: two-layer reflection | `test_two_layer_reflection_arrival` | covered | `test_m2.py:194-209` |
| M3: RTM image.npy shape + reflector focus | `test_rtm_image_*` | covered | `test_m3.py:62-115` |
| M3: AVO CSV header + fit row + LS fit | `test_avo_*` | covered | `test_m3.py:117-179` |
| M3: QC snr/wavelength/resolution/illumination | `test_qc_*` | covered | `test_m3.py:181-223` |
| M3: sweep parameters + illumination map | `test_sweep_*` | covered | `test_m3.py:225-284` |
| M3: UTF-8 CSV without BOM | `test_avo_csv_header_and_fit_row` | covered | `imaging_schema.md:3-6`, `test_m3.py:121` |

---

## 6. Proof file index

| File | Used for |
|------|----------|
| `task.toml` | Blocker #43, #45 |
| `steps/milestone_*/instruction.md` | #1–#11, §5 |
| `environment/Dockerfile` | #13–#20, #50 |
| `environment/docs/imaging_schema.md` | BOM claim, §5 |
| `environment/docs/model_schema.md` | Fault clamp claim |
| `environment/fixtures/sim_homo_vz.json` | vz injection claim |
| `steps/milestone_*/tests/test_m*.py` | #27–#31, §5 |
| `steps/milestone_*/tests/test.sh` | #24, #20 |
| `steps/milestone_*/solution/solve*.sh` | #22, #23 |
| `entire-report.txt` | Agent stats, oracle, rubrics, adjudication |
| `docs/task-requirements.md` | Milestone metadata rule |

---

## 7. Validation & agent performance

### Validation

```
ERROR: task.toml — Milestone tasks must not have top-level [agent]
ERROR: task.toml — Milestone tasks must not have top-level [verifier]
WARNING: 46× informative_test_docstrings (false positive on -> None: annotations)
WARNING: 2× unpinned pip bootstrap
```

### Agent performance

| Model | Pass rate | Notes |
|-------|-----------|-------|
| terminus-gpt5-5 | 0.0% (0/5) | Worst model — sets tier |
| terminus-claude-opus-4-8 | 80.0% (4/5) | At easy boundary individually |
| oracle | 100.0% (3/3) | Per report |
| nop | 0.0% (0/1) | Per report |

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
| 0 Scope & identity | ☑ | 3-milestone C# seismic FDTD; report matches folder |
| 1 Instruction | ☑ | Per-milestone instructions OK; schemas normative |
| 2 Environment | ☑ | Digest-pinned; tmux+asciinema; deps baked; no tests/solution COPY |
| 3 Oracle | ☑ | Non-hardcoded C# builds; 100% per report |
| 4 Verifiers | ☑ | reward block; physics tests; docstrings present |
| 5 Metadata | ☐ | **Blocker:** top-level agent/verifier sections |
| 6 Rubric | ☑ | Verified from `entire-report.txt` portal rubrics |
| 7 Agent evidence | ☑ | Hard tier confirmed; BOM failures agent-side |
| 8 Fairness | ☑ | Prior gaps closed; RTM not trivially fakeable |
| 9 Long context | N/A | Not tagged `long_context` |

---

## 9. Reviewer note (copy-paste to portal)

Needs revision. Remove the top-level `[verifier]` and `[agent]` sections from `task.toml` (lines 24–28); milestone tasks must use only per-step `[steps.agent]` / `[steps.verifier]`, which are already present. Everything else re-audited clean: digest-pinned Dockerfile with offline verifiers, oracle 100%, hard difficulty confirmed (GPT-5.5 0%), and prior fairness gaps (vz injection, elastic shear, RTM structure, BOM-free CSV, QC/SNR, illumination counts) are addressed in current tests and schemas. Resubmit after the one-line metadata fix.

---

## 10. Error categories summary (internal)

| Category | Applies | Blocker # |
|----------|---------|-----------|
| Metadata Issues | yes | 1 |
| Instruction Styling | no | — |
| Test Alignment/Coverage Issues | no | — |
| Pinning Issues | no | — |
| Test Build Issues | no | — |
| Task Difficulty | no | — |
| Milestones | no | — |
| Rubric | no | — |
| Environment | no | — |
