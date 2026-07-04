Difficulty Explanation (optional)
Describe in your own words why your task is challenging for humans and agents to solve.

The library has to be built from scratch in C with only libm — the incomplete gamma/beta functions, the chi-square/t/F CDFs, their inverses, and a CLI on top — across four dependent milestones. The quantiles require a robust root-find with the right brackets and edge handling, and the final CLI layers on a Holm–Bonferroni step-down correction whose monotonicity, capping, and step-down stopping rule are easy to get subtly wrong, plus a Welch confidence interval that depends on the non-integer-df t quantile. The math is well known but the integration, the bespoke multiple-testing rule, and the strict numerical tolerances across four stages give many independent places to fail.
Solution Explanation (optional)
Describe your high-level approach to this task and key insights in forming the solution.

Build it in layers. Implement the incomplete gamma and beta with a series/continued-fraction split, express every CDF as a thin wrapper, then invert the CDFs by bracketing and bisection (they are monotone, so this converges). The CLI is glue: parse the .spec suite and alpha, compute each test's statistic/df/p-value through the lower layers, get critical values and Welch intervals from the quantiles, apply Holm across the valid tests, and serialize minified JSON. The key insight is keeping the delicate numerics in one place so the CDFs, quantiles, and CLI stay simple.
Verification Explanation (optional)
Explain how your tests are verifying correctness.

Each milestone compiles a verifier-owned C probe against the agent's source and compares the compiled functions to an independent pure-Python reference (checked against scipy/statsmodels) on wide input grids with numerical tolerance, plus contract checks (identities, round trips F(ppf(p))=p, NaN on bad domains). The CLI milestone runs the built statctl on generated suites and checks the statistics, Holm-adjusted p-values, reject decisions, critical values, intervals, ordering, minified format, and exit codes against the reference. Every milestone re-checks the earlier ones through the same binary, so any regression fails.


Difficulty: ✅ HARD

Status: ✅ Solvable (all tests passed by at least one agent run)

Agent Performance:
  • terminus-claude-opus-4-8: 20.0% (1/5 runs)
  • terminus-gpt5-5: 100.0% (5/5 runs)

Reference Agents:
  • nop: 0.0% (0/1 runs)
  • oracle: 100.0% (3/3 runs)

Failure Breakdown:
  • nop: 1 other
  • terminus-claude-opus-4-8: 4 other

Unit Tests Results:
  • milestone_1 → TestMilestone1 → test_make_lib_produces_archive: 10 passed / 10 runs
  • milestone_1 → TestMilestone1 → test_gammap_matches_reference: 8 passed / 10 runs
  • milestone_1 → TestMilestone1 → test_gammaq_matches_reference: 8 passed / 10 runs
  • milestone_1 → TestMilestone1 → test_gamma_complement: 8 passed / 10 runs
  • milestone_1 → TestMilestone1 → test_gammap_known_identities: 8 passed / 10 runs
  • milestone_1 → TestMilestone1 → test_gammap_domain_returns_nan: 8 passed / 10 runs
  • milestone_1 → TestMilestone1 → test_gammaq_domain_returns_nan: 8 passed / 10 runs
  • milestone_1 → TestMilestone1 → test_chisq_cdf_matches_reference: 8 passed / 10 runs
  • milestone_1 → TestMilestone1 → test_chisq_sf_matches_reference: 8 passed / 10 runs
  • milestone_1 → TestMilestone1 → test_chisq_cdf_sf_complement: 8 passed / 10 runs
  • milestone_1 → TestMilestone1 → test_chisq_invalid_df_returns_nan: 8 passed / 10 runs
  • milestone_1 → TestMilestone1 → test_frozen_acceptance_incgamma: 8 passed / 10 runs
  • milestone_1 → TestMilestone1 → test_frozen_acceptance_chisq: 8 passed / 10 runs
  • milestone_2 → TestMilestone2 → test_betai_matches_reference: 10 passed / 10 runs
  • milestone_2 → TestMilestone2 → test_betai_symmetry: 10 passed / 10 runs
  • milestone_2 → TestMilestone2 → test_betai_known_identities: 10 passed / 10 runs
  • milestone_2 → TestMilestone2 → test_betai_domain_returns_nan: 10 passed / 10 runs
  • milestone_2 → TestMilestone2 → test_tdist_cdf_matches_reference: 10 passed / 10 runs
  • milestone_2 → TestMilestone2 → test_tdist_symmetry_and_complement: 10 passed / 10 runs
  • milestone_2 → TestMilestone2 → test_tdist_at_zero: 10 passed / 10 runs
  • milestone_2 → TestMilestone2 → test_tdist_invalid_df_returns_nan: 10 passed / 10 runs
  • milestone_2 → TestMilestone2 → test_fdist_cdf_matches_reference: 10 passed / 10 runs
  • milestone_2 → TestMilestone2 → test_fdist_invalid_df_returns_nan: 10 passed / 10 runs
  • milestone_2 → TestMilestone2 → test_milestone1_chisq_still_correct: 8 passed / 10 runs
  • milestone_2 → TestMilestone2 → test_frozen_acceptance_beta_and_dists: 10 passed / 10 runs
  • milestone_3 → TestMilestone3 → test_chisq_ppf_matches_reference: 10 passed / 10 runs
  • milestone_3 → TestMilestone3 → test_tdist_ppf_matches_reference: 10 passed / 10 runs
  • milestone_3 → TestMilestone3 → test_chisq_ppf_roundtrip: 10 passed / 10 runs
  • milestone_3 → TestMilestone3 → test_tdist_ppf_roundtrip: 10 passed / 10 runs
  • milestone_3 → TestMilestone3 → test_tdist_ppf_symmetry: 10 passed / 10 runs
  • milestone_3 → TestMilestone3 → test_ppf_monotonic: 10 passed / 10 runs
  • milestone_3 → TestMilestone3 → test_ppf_known_criticals: 10 passed / 10 runs
  • milestone_3 → TestMilestone3 → test_ppf_domain_returns_nan: 10 passed / 10 runs
  • milestone_3 → TestMilestone3 → test_milestone_cdfs_still_correct: 10 passed / 10 runs
  • milestone_3 → TestMilestone3 → test_frozen_acceptance_invdist: 10 passed / 10 runs
  • milestone_4 → TestMilestone4 → test_normal_cdf_matches_reference: 10 passed / 10 runs
  • milestone_4 → TestMilestone4 → test_normal_cdf_symmetry: 10 passed / 10 runs
  • milestone_4 → TestMilestone4 → test_normal_cdf_known: 10 passed / 10 runs
  • milestone_4 → TestMilestone4 → test_normal_cdf_domain_returns_nan: 10 passed / 10 runs
  • milestone_4 → TestMilestone4 → test_ks_sf_matches_reference: 10 passed / 10 runs
  • milestone_4 → TestMilestone4 → test_ks_sf_boundary_and_monotone: 10 passed / 10 runs
  • milestone_4 → TestMilestone4 → test_ks_sf_known: 10 passed / 10 runs
  • milestone_4 → TestMilestone4 → test_milestone_cdfs_still_correct: 10 passed / 10 runs
  • milestone_4 → TestMilestone4 → test_frozen_acceptance_ksdist: 10 passed / 10 runs
  • milestone_5 → TestMilestone5 → test_basic_suite_values: 9 passed / 10 runs
  • milestone_5 → TestMilestone5 → test_ks_normal_values: 9 passed / 10 runs
  • milestone_5 → TestMilestone5 → test_three_kinds_with_holm: 9 passed / 10 runs
  • milestone_5 → TestMilestone5 → test_holm_correction: 9 passed / 10 runs
  • milestone_5 → TestMilestone5 → test_alpha_directive_changes_decisions: 9 passed / 10 runs
  • milestone_5 → TestMilestone5 → test_report_is_minified_one_line: 9 passed / 10 runs
  • milestone_5 → TestMilestone5 → test_comments_and_blank_lines_ignored: 9 passed / 10 runs
  • milestone_5 → TestMilestone5 → test_ddof_changes_degrees_of_freedom: 9 passed / 10 runs
  • milestone_5 → TestMilestone5 → test_welch_df_is_non_integer: 9 passed / 10 runs
  • milestone_5 → TestMilestone5 → test_malformed_blocks_skipped: 8 passed / 10 runs
  • milestone_5 → TestMilestone5 → test_no_valid_tests_exit_nonzero: 10 passed / 10 runs
  • milestone_5 → TestMilestone5 → test_missing_spec_exit_nonzero: 10 passed / 10 runs
  • milestone_5 → TestMilestone5 → test_default_output_path: 9 passed / 10 runs

Analysis on Agent Failures:
  • Task Instruction Sufficiency: ✅ PASS, ## Job Summary: statkit C Library Implementation

### 1. Overall Results

**No trials achieved full marks (5/5 milestones).** Results across 4 trials:

| Trial | Reward | Milestones Passed |
|-------|--------|-------------------|
| tbench-task__gTsb7ov | 0.8 | 1–4 ✅, 5 ❌ (12/13 tests) |
| tbench-task__eCnPvxr | 0.8 | 1–4 ✅, 5 ❌ (infrastructure failure) |
| tbench-task__Pi8vMnx | 0.6 | 1–2 ❌, 3–5 ✅ |
| tbench-task__QLjSaYj | 0.6 | 1–2 ❌, 3–5 ✅ |

**Mean reward: 0.70.** No agent completed all 5 milestones.

---

### 2. Common Failure Patterns

**Two distinct failure clusters emerged:**

**Cluster A — Milestone 5 (CLI) failures** (`gTsb7ov`, `eCnPvxr`):
- Both passed milestones 1–4 cleanly before failing at the final CLI milestone.
- `gTsb7ov`: Near-miss — missed a single malformed-input validation: `sigma` was defaulted to `1.0` without checking `have_sigma`, so a `bad3` block missing `sigma` was incorrectly accepted. One-line bug.
- `eCnPvxr`: Infrastructure failure — the model's first (and only) API call on milestone 5 exceeded the 16,384 output-token limit (`OutputLengthExceededError`), triggering a retry loop until the 1200s timeout. **No code was written at all.** This is a model/harness issue, not an implementation failure.

**Cluster B — Milestone 1 (incgamma) failures** (`Pi8vMnx`, `QLjSaYj`):
- Both failed milestones 1 and 2, then recovered to pass 3–5.
- `QLjSaYj`: Agent **hallucinated** having previously succeeded on milestone 1 ("My previous run showed test_incgamma rc=0") and submitted unmodified stubs returning `-1.0`.
- `Pi8vMnx`: Stubs similarly returned `-1` sentinel values on milestone 1, suggesting the implementation was never properly written or built. Milestone 2 then introduced a regression check for milestone 1's chi-square CDF, compounding the failure.
- Both agents apparently rebuilt correctly from milestone 3 onward, suggesting the foundational math was not inherently beyond capability — the early failures were execution/ordering issues.

---

### 3. Hack Check

**Clean across all four trials.** No reward hacking detected:
- No agent accessed `solution/` directories.
- No agent wrote to `reward.txt` or `reward.json`.
- No agent modified test files.
- All failures are attributable to legitimate implementation bugs or infrastructure errors. The partial reward in `gTsb7ov` reflects a genuine near-miss; the 0.0 on milestone 5 in `eCnPvxr` reflects an API timeout before any code was written.

---

### 4. Systematic Instruction Issues

**None found.** All four `task_specification` checks passed. Key findings:
- FORMAT.md and ALGORITHMS.md were assessed as clear and sufficient in all trials.
- The malformed-block rules for `ks_normal` were explicitly documented (`sigma` listed as required); `gTsb7ov`'s failure was agent error.
- The regression expectation in milestone 2 ("incomplete gamma work from before should stay intact") was explicitly stated; Cluster B failures were agent execution failures, not spec gaps.
- The one systemic concern is the **OutputLengthExceededError** in `eCnPvxr` — this is an infrastructure/model-configuration issue (token output limit too low for a task requiring large C file generation) that could affect other runs. Consider raising the output token limit or prompting agents to write code incrementally.

---

### 5. Progress on Failed Trials

| Trial | Failed Milestone(s) | Completion Within Milestone |
|-------|--------------------|-----------------------------|
| gTsb7ov | M5 | 12/13 tests (92%) — one missing validation check |
| eCnPvxr | M5 | 0/13 tests (0%) — no code written due to token limit |
| Pi8vMnx | M1, M2 | M1: 0%, M2: ~92% (11/12 tests, blocked by M1 regression) |
| QLjSaYj | M1, M2 | M1: 0% (hallucination), M2: failed regression only |

Average effective progress on failed milestones: **~46%**, but this is skewed by infrastructure/hallucination zeroes. The two *implementation* failures (`gTsb7ov` M5, `Pi8vMnx` M2) were both near-misses at >90%.

---

### 6. Key Model/Agent Differences

Only one model is explicitly named: **claude-opus-4-8** (`eCnPvxr`, `QLjSaYj`). The other two trials don't name their models.

- **`eCnPvxr` (opus-4-8)**: Strong implementer (4/5 milestones passed) but hit a hard infrastructure wall on M5. The failure was external, not capability-related.
- **`QLjSaYj` (opus-4-8)**: Showed hallucination of prior success on M1 — a reliability/grounding issue. Recovered well on M3–5.
- **`gTsb7ov`**: Best overall implementation quality — only a single missing validation check separating it from a perfect score.
- **`Pi8vMnx`**: Recovered from two early failures to pass M3–5, suggesting the model could implement the math but had ordering/build issues early on.

**Actionable takeaway:** The most addressable improvement is the output-token limit causing `eCnPvxr`'s M5 failure — that was a winnable task lost to infrastructure. The second priority is addressing hallucinated success in `QLjSaYj` (e.g., requiring agents to verify test output before submitting).

## Quality Check Results
✅ pass - behavior_in_task_description: Each milestone instruction clearly describes the required behavior verified by its tests. M1 names sk_gammap/sk_gammaq/sk_chisq_cdf/sk_chisq_sf and their source files, references ALGORITHMS.md for math definitions, and cites the frozen C tests. M2 names sk_betai/sk_tdist_cdf/sk_tdist_sf/sk_fdist_cdf and notes non-integer DoF support. M3 names sk_chisq_ppf/sk_tdist_ppf in invdist.c with bisection, NaN for out-of-range. M4 names sk_normal_cdf/sk_ks_sf in ksdist.c with correct boundary/NaN behavior. M5 names all three test kinds, the CLI command (build/statctl <spec> [-o <out>]), default output path /app/output/report.json, Holm-Bonferroni correction, critical values, confidence intervals, malformed-block rules, and references FORMAT.md for the full schema. The FORMAT.md document (referenced from M5) provides the exact JSON schema, spec grammar, and all computation formulas.
✅ pass - behavior_in_tests: All behavior described in the instructions is covered by tests. M1 tests gammap/gammaq (wide grid, identities, NaN domain), chisq_cdf/chisq_sf (reference grid, complement, NaN), and frozen C acceptance tests. M2 adds betai, tdist_cdf/sf, fdist_cdf with symmetry, regression on M1 functions, and frozen tests. M3 tests chisq_ppf/tdist_ppf with round-trips, symmetry, monotonicity, NaN, and the frozen invdist test. M4 tests normal_cdf (symmetry, boundaries, NaN for sigma<=0) and ks_sf (boundary conditions, monotonicity, known values). M5 tests all three test kinds, Holm correction, alpha directive, minified JSON format, comment/blank handling, ddof, non-integer Welch df, malformed block skipping, exit codes, and default output path. Coverage is comprehensive.
✅ pass - informative_test_structure: All Python test files use pytest classes (e.g., TestMilestone1, TestMilestone5) with clearly named methods (test_gammap_matches_reference, test_frozen_acceptance_incgamma, test_ks_normal_values, etc.) and docstrings on each test that describe what is being checked (e.g., 'sk_gammap returns NaN for a<=0 or x<0', 'Report is a single minified JSON line with one trailing newline'). The frozen C test files (test_incgamma.c, test_chisq.c, etc.) use the SK_CHECK / SK_CLOSE / SK_DONE macros and are logically sectioned with comments. The structure is readable and maintainable.
✅ pass - anti_cheating_measures: The Dockerfile stashes golden copies of /app/tests and /app/data into /opt/golden/ and each test.sh restores them before grading (rm -rf /app/tests && cp -a /opt/golden/tests), preventing the agent from modifying the frozen C acceptance tests or fixture data. The Python verifiers compile the agent's source files from /app/src/*.c independently via a probe binary and compare numerically to an inline reference implementation—there are no ground-truth values baked into environment files that the agent could copy. The solution files are in steps/*/solution/ which are not copied into the Docker image (the Dockerfile only copies app/). Internet is disabled (allow_internet = false). The tests generate fresh spec strings dynamically (not from data/fixtures), so the agent cannot game them by reading fixture files.
✅ pass - structured_data_schema: FORMAT.md provides an explicit, normative JSON schema for the statctl report, including exact field names, types (num vs. bool), ordering, which fields appear for which test kinds (df and critical_value for chisq_gof, df/ci_low/ci_high for welch_t, neither for ks_normal), the minified one-line format with single trailing newline, and the version field. The spec grammar is also fully defined with all valid keys per test kind. The milestone 5 instruction explicitly references FORMAT.md as the authoritative source for the schema.
✅ pass - pinned_dependencies: Python packages are version-pinned in the Dockerfile: pytest==8.4.1 and pytest-json-ctrf==0.3.5. The base Docker image is digest-pinned (gcc:13-bookworm@sha256:930f2ebe...). Apt packages tmux=3.3a-3 and asciinema=2.2.0-1 are version-pinned. Other apt packages (python3, python3-pip, python3-venv, make, ca-certificates) are standard distro packages from the pinned base image and do not require explicit version pinning by convention.
✅ pass - typos: No significant typos found in filenames, paths, commands, or variable names. File paths mentioned in instructions (/app/src/incgamma.c, /app/src/chisq.c, /app/docs/ALGORITHMS.md, /app/tests/test_incgamma.c, build/statctl, /app/output/report.json, etc.) are consistent with the actual file tree. Function names (sk_gammap, sk_gammaq, sk_betai, sk_chisq_cdf, sk_chisq_sf, sk_tdist_cdf, sk_tdist_sf, sk_fdist_cdf, sk_chisq_ppf, sk_tdist_ppf, sk_normal_cdf, sk_ks_sf) match across headers, stubs, solutions, instructions, and tests. Test kind names (chisq_gof, welch_t, ks_normal) are consistent throughout spec files and code.
✅ pass - tests_or_solution_in_image: The Dockerfile only copies app/ into the image (COPY app/ /app/). The steps/ directory (which contains all solution/ and tests/ files) is not copied into the image. The test scripts are mounted at runtime under /tests (via the TEST_DIR variable). The golden copies stored in /opt/golden/ are sourced from /app/tests (the environment app's frozen acceptance suite), not from steps/*/tests/.
✅ pass - hardcoded_solution: All solutions derive answers through computation. solve1.sh copies actual C implementation files with working algorithms (power-series/continued-fraction for incomplete gamma, etc.) and builds+tests them. solve3.sh and solve4.sh write full algorithmic implementations via heredoc (bisection for quantiles, erfc for normal CDF, alternating series for KS). solve5.sh writes a full C parser and CLI driver that computes statistics at runtime. None of the solutions echo hardcoded numeric answers; all implement the required algorithms.
✅ pass - file_reference_mentioned: All output files agents must produce are explicitly named in the instructions. M1 specifies /app/src/incgamma.c and /app/src/chisq.c. M2 specifies /app/src/incbeta.c, /app/src/student.c, /app/src/fdist.c. M3 specifies /app/src/invdist.c. M4 specifies /app/src/ksdist.c. M5 specifies /app/cli/specparse.c and /app/cli/statctl.c, with the output defaulting to /app/output/report.json (explicitly stated). The build artifact build/statctl is implicit from 'make' but the command is described.


================================================================================
                         REVIEW REPORT: tbench-task
================================================================================

Status:        ✅ PASS
Task Location: /root/harbor_tasks/tbench-task

--------------------------------------------------------------------------------
SUMMARY
--------------------------------------------------------------------------------

This is a 5-milestone multi-step task requiring the agent to incrementally
implement a pure-C numerical statistics library ("statkit") — from
regularized incomplete gamma/beta functions through distribution CDFs,
quantile functions, the Kolmogorov distribution, and finally a CLI that
runs chi-square GOF, Welch t, and K-S tests with Holm-Bonferroni
correction. The environment ships a fully-scaffolded codebase with stub
implementations, headers, documentation, and a Makefile; the agent fills
in the numerical code. Each milestone's verifier compiles a self-contained
C probe against the agent's sources and compares outputs to an independent
Python reference at double-precision tolerance — an excellent anti-cheat
design since the tests are opaque to the agent.

================================================================================
                              WARNINGS ⚠️
================================================================================

--------------------------------------------------------------------------------
1. Non-Canonical Docker Base Image
--------------------------------------------------------------------------------

File:    tbench-task/environment/Dockerfile (line 3)
Problem: The task uses `gcc:13-bookworm` as its base image. The Terminus 2nd
         Edition canonical base image list is intended to constrain base-image
         fragmentation. If `gcc:13-bookworm` is not on the approved canonical
         list, it should be proposed as an addition (or the task should justify
         why the existing C/C++ canonical image is insufficient).

Current code:
┌─────────────────────────────────────────────────────────────────────────────┐
│  FROM public.ecr.aws/docker/library/gcc:13-bookworm@sha256:930f2ebe23927... │
└─────────────────────────────────────────────────────────────────────────────┘

Explanation: The image is digest-pinned (good) and provides the GCC
toolchain the task requires. If the canonical list already includes a
gcc/C-focused image, switch to it; otherwise, propose this image for
addition to the list. This is not blocking since the image is correctly
pinned and functional for the task's needs.

--------------------------------------------------------------------------------
2. Milestone 5 Instruction Could Be More Explicit on JSON Schema
--------------------------------------------------------------------------------

File:    tbench-task/steps/milestone_5/instruction.md (lines 1-5)
Problem: The milestone 5 instruction references `/app/docs/FORMAT.md` for the
         full report schema, but does not inline the exact JSON field names
         that the verifier checks (e.g., `adj_pvalue`, `ci_low`, `ci_high`,
         `critical_value`). An agent that misreads FORMAT.md could produce
         slightly different field names and fail.

Current approach: "The report schema [is] in `/app/docs/FORMAT.md`."

Suggested fix: No change strictly required — FORMAT.md is detailed and
present in the agent workspace. However, consider inlining the top-level
JSON keys in the instruction as a quick-reference to reduce ambiguity.

Explanation: FORMAT.md is thorough and unambiguous on its own, so this is
a usability concern rather than a correctness one. The agent has full
access to read the doc.

================================================================================
                            OVERALL ASSESSMENT
================================================================================

An exceptionally well-crafted, production-quality multi-step task that
exercises deep numerical computing skills in C with no third-party
dependencies. The anti-cheat design (golden copy restoration + opaque
verifier probes) is best-in-class.

Key Strengths:
  ✓ Excellent anti-cheat: frozen golden copies restored before each
    verifier run; tests compile their own probe binary and compare against
    an independent Python reference — agents cannot game by editing tests
  ✓ Progressive difficulty with regression checks: each milestone's
    verifier re-checks prior milestone outputs, catching regressions
  ✓ Comprehensive test coverage: 50+ assertions per milestone covering
    numerical accuracy, domain errors, known identities, round-trips,
    symmetry, monotonicity, and format correctness
  ✓ Clean offline design: all deps (pytest, tmux, asciinema) installed at
    build time; test.sh is network-free; TEST_DIR has a default

Key Weaknesses:
  ✗ Potentially non-canonical base image (needs verification against the
    approved list)

Evaluates: numerical methods in C, special function implementation,
           incremental library development, CLI/JSON output formatting

================================================================================
  RECOMMENDATION: ✅ READY TO USE

  This task is structurally sound, well-documented, and thoroughly tested.
  The only open item is confirming the gcc:13-bookworm base image against
  the canonical list — if it is already approved (or added), the task is
  fully production-ready with no changes.
================================================================================

================================================================================
          TEST QUALITY REVIEW: tbench-task (MILESTONE TASK — 5 steps)
================================================================================

Status:    ✅ ROBUST
Severity:  None
Milestones: 5 of 5 reviewed

================================================================================
                         OVERALL ASSESSMENT
================================================================================

This task has 5 milestone(s); 0 of 5 reviewed are VULNERABLE.
See per-milestone reviews below for details.

================================================================================
                         PER-MILESTONE REVIEWS
================================================================================

================================================================================
                      TEST QUALITY REVIEW: tbench-task milestone 1
================================================================================

Status:    ✅ ROBUST
Severity:  None

================================================================================
                         OVERALL ASSESSMENT
================================================================================

Recommendation: ACCEPT
The test suite thoroughly validates all four functions required by milestone 1
with extensive numerical correctness checks, identity verification, domain
error handling, and tamper-resistant frozen acceptance tests.

Strengths:  The verifier uses an independent Python reference implementation
to check 100+ data points per function across a wide parameter grid, verifies
known mathematical identities (P(1,x) = 1-e^-x, P(1/2,x) = erf(sqrt(x))),
and restores frozen C acceptance tests from /opt/golden to prevent tampering.

Weaknesses: None of significance — the test suite is comprehensive and
well-structured for this numerical implementation task.

================================================================================
                                 SUMMARY
================================================================================

Milestone 1 requires implementing four numerical functions: sk_gammap,
sk_gammaq, sk_chisq_cdf, and sk_chisq_sf. The test suite exercises each
function through a separate verifier-owned C probe binary compiled against
the agent's source, comparing results against an independent Python reference
at rtol=1e-9 across a 10x10 grid of parameter values. Additional tests
verify complement relationships (P+Q=1, CDF+SF=1), known closed-form
identities, boundary values, NaN returns for invalid domains, and the
frozen C acceptance suite. The test.sh script restores golden copies of
tests/ and data/ before grading, blocking any tampering strategy. No
shortcut solution exists — the agent must implement correct numerical
algorithms to pass.

================================================================================

================================================================================
                      TEST QUALITY REVIEW: tbench-task milestone 2
================================================================================

Status:    ✅ ROBUST
Severity:  None

================================================================================
                         OVERALL ASSESSMENT
================================================================================

Recommendation: ACCEPT
The test suite thoroughly validates all core requirements of milestone 2 with
numerical correctness assertions against an independent reference, algebraic
identity checks, domain validation, and the frozen C acceptance tests.

Strengths:  The verifier uses a multi-layered approach: (1) an independent
Python reference implementation verified against SciPy for betai, tdist_cdf,
tdist_sf, and fdist_cdf; (2) a custom C probe compiled against the agent's
source to test numerical outputs at high precision (rtol=1e-9, atol=1e-12);
(3) mathematical identity checks (symmetry, known values, endpoints);
(4) domain/NaN validation; (5) the frozen C acceptance suite is restored from
/opt/golden before grading, preventing agent tampering.

Weaknesses: None significant. The test coverage is comprehensive across all
required functions with wide parameter grids.

================================================================================
                                 SUMMARY
================================================================================

The milestone 2 test suite (`test_m2.py`) validates four functions:
`sk_betai`, `sk_tdist_cdf`, `sk_tdist_sf`, and `sk_fdist_cdf`. It compares
the agent's compiled C output against an inline Python reference across broad
parameter grids (8 a-values × 7 b-values × 7 x-values for betai; 8
nu-values × 8 t-values for tdist; 5 degree-pairs × 5 f-values for fdist).
The reference implementation faithfully mirrors the ALGORITHMS.md spec
line-by-line. The frozen C acceptance tests are also run after being restored
from a golden copy. No shortcut solution exists — the agent cannot read test
files, the parameter grids are too large for hardcoding, and the numerical
precision requirements demand a genuine implementation of the continued
fraction algorithm for the incomplete beta function.

================================================================================

================================================================================
                      TEST QUALITY REVIEW: tbench-task milestone 3
================================================================================

Status:    ✅ ROBUST
Severity:  None

================================================================================
                         OVERALL ASSESSMENT
================================================================================

Recommendation: ACCEPT
The test suite thoroughly verifies both quantile functions across wide
parameter grids with correctness assertions, roundtrip checks, known
critical values, domain error handling, and mathematical property tests.

Strengths:  The verifier uses an independent reference implementation and a
custom C probe to exercise the agent's compiled code directly, testing 54
chi-square and 63 t-distribution parameter combinations plus domain errors,
symmetry, and monotonicity — no shortcut can satisfy this coverage.

Weaknesses: None of significance. The tolerance (rtol=1e-5) is slightly
more generous than the spec's "roughly 1e-6" but this is conservative
grading, not a vulnerability.

================================================================================
                                 SUMMARY
================================================================================

Milestone 3 requires implementing sk_chisq_ppf and sk_tdist_ppf as
numerical inverses of the chi-square and Student-t CDFs. The test suite
verifies correctness through four complementary strategies: (1) comparison
against an independent Python bisection reference across a 6×9 and 7×9
parameter grid, (2) CDF(PPF(p))=p roundtrip consistency, (3) known
textbook critical values, and (4) NaN returns for out-of-domain inputs.
The frozen C acceptance test is restored from a golden copy before grading,
preventing the agent from weakening it. Non-integer degrees of freedom
(3.5, 10.86) are explicitly tested. No shortcut implementation can pass
this suite without genuine numerical root-finding.

================================================================================

================================================================================
                      TEST QUALITY REVIEW: tbench-task milestone 4
================================================================================

Status:    ✅ ROBUST
Severity:  None

================================================================================
                         OVERALL ASSESSMENT
================================================================================

Recommendation: ACCEPT
The test suite thoroughly validates both core functions with multiple
complementary verification strategies and tight numerical tolerances.

Strengths:  Tests combine hardcoded known values, reference implementation
comparison across many points, symmetry/monotonicity property checks, domain
error handling, regression coverage for prior milestones, and a frozen C
acceptance suite that is restored from a golden copy to prevent tampering.

Weaknesses: None of significance — coverage is comprehensive.

================================================================================
                                 SUMMARY
================================================================================

The milestone 4 test suite validates sk_normal_cdf and sk_ks_sf through
nine distinct tests covering correctness, boundary behavior, domain errors,
mathematical properties, regression of earlier CDFs, and the frozen C
acceptance suite. The Python reference implementations faithfully mirror
the formulas in ALGORITHMS.md (erfc-based normal CDF and alternating-series
Kolmogorov survival function). Tolerances are tight (1e-10 for normal CDF,
1e-7 to 1e-9 for ks_sf), test points span the useful domain, and the
verifier restores frozen test files from /opt/golden/ to block tampering.
No shortcut implementation can pass without correctly computing both
functions.

================================================================================

================================================================================
                      TEST QUALITY REVIEW: tbench-task milestone 5
================================================================================

Status:    ✅ ROBUST
Severity:  None

================================================================================
                         OVERALL ASSESSMENT
================================================================================

Recommendation: ACCEPT
The test suite thoroughly verifies all core constraints of milestone 5 with
numerical correctness assertions against an independent reference
implementation, and no shortcut path exists for the agent.

Strengths:  The tests dynamically generate spec files (not using the fixture
files the agent can see), compute expected values from an inline independent
reference implementation verified against SciPy, and compare all numerical
outputs with tight tolerances. Coverage spans all three test kinds, Holm
correction, malformed-block skipping, exit codes, formatting, alpha
directives, ddof, confidence intervals, critical values, and the default
output path.

Weaknesses: Minor — the reference implementation in the test file is complex
enough that subtle oracle drift is theoretically possible, but each function
mirrors the documented formulas in FORMAT.md faithfully.

================================================================================
                                 SUMMARY
================================================================================

The milestone 5 test suite contains 13 test cases exercising every
requirement stated in the instruction: chi-square GOF (with ddof), Welch
two-sample t-test (with non-integer df and CI), KS normality test,
Holm-Bonferroni correction across mixed suites, the alpha directive,
malformed-block handling, report format (minified single line), comment/
blank-line tolerance, exit codes, and the default output path. Tests use
dynamically constructed spec inputs not available to the agent, compute
reference values inline, and assert numerical closeness with rtol=1e-6.
The verifier restores golden copies of /app/tests and /app/data before
grading, preventing tampering. No shortcut solution is viable — the agent
must implement a working parser and statistical driver from stub C files.

================================================================================

================================================================================

# Rubric 1
Agent inspects the incomplete-gamma source before editing it, showing its contents in the trace, +1
Agent implements the lower and upper regularized incomplete gamma functions in /app/src/incgamma.c so they stay accurate across both small and large x without a single-regime breakdown, +5
Agent implements the chi-square CDF and survival function in /app/src/chisq.c as thin wrappers over the regularized incomplete gamma functions, +3
Agent returns NaN from the gamma and chi-square functions for out-of-domain arguments such as a<=0, x<0, or non-positive degrees of freedom, +2
Agent builds the library with make and surfaces a clean compile in the trace, +2
Agent exercises its compiled gamma and chi-square functions on sample inputs and surfaces correct numeric output in the trace, +3
Agent weakens, deletes, or stubs out the frozen acceptance checks instead of implementing the library to satisfy them, -5
Agent changes the frozen public function signatures it was told to leave untouched, -3
Agent hardcodes specific numeric outputs to satisfy the checks instead of writing a general implementation, -3
Agent repeats the same failing build or command three or more times without changing the approach, -1

# Rubric 2
Agent inspects the incomplete-beta source before editing it, showing its contents in the trace, +1
Agent implements the regularized incomplete beta function in /app/src/incbeta.c so it stays numerically accurate across the full 0 to 1 range, including x near 1, +5
Agent implements the Student-t CDF and survival function in /app/src/student.c and the F CDF in /app/src/fdist.c in terms of the incomplete beta, +3
Agent keeps the t CDF correct for non-integer degrees of freedom and returns NaN for non-positive degrees of freedom, +2
Agent verifies a beta identity or symmetry such as I_x(a,b)+I_(1-x)(b,a)=1 on its own implementation in the trace, +2
Agent builds with make and exercises its compiled beta and distribution functions, surfacing correct numeric output, +3
Agent keeps the earlier incomplete-gamma and chi-square functions working after adding the beta layer, +2
Agent weakens, deletes, or stubs out the frozen acceptance checks instead of implementing the library to satisfy them, -5
Agent hardcodes beta, t, or F outputs instead of writing a general implementation, -3
Agent breaks the previously working incomplete-gamma or chi-square functions while adding the beta code, -2

# Rubric 3
Agent inspects the quantile source before editing it, showing its contents in the trace, +1
Agent implements sk_chisq_ppf and sk_tdist_ppf in /app/src/invdist.c as the inverses of the chi-square and t CDFs, accurate across the full probability range, +5
Agent confirms the inverse round trip (the CDF of the quantile returns the input probability) on its own implementation in the trace, +3
Agent supports non-integer degrees of freedom and returns NaN for p outside the open interval (0,1) or non-positive degrees of freedom, +2
Agent builds with make and exercises its compiled quantile functions, surfacing correct numeric output, +3
Agent keeps the earlier CDF functions working after adding the quantiles, +2
Agent weakens, deletes, or stubs out the frozen acceptance checks instead of implementing the quantiles to satisfy them, -5
Agent hardcodes quantile outputs for the tested points instead of writing a general inverse, -3
Agent breaks a previously working CDF while adding the quantile code, -2

# Rubric 4
Agent inspects the Kolmogorov source before editing it, showing its contents in the trace, +1
Agent implements sk_normal_cdf in /app/src/ksdist.c via the error function and returns NaN for a non-positive standard deviation, +3
Agent implements sk_ks_sf in /app/src/ksdist.c as the Kolmogorov survival series, returning 1 at and below 0 and clamping the result to the zero-to-one range, +5
Agent confirms sk_ks_sf decreases monotonically and matches known Kolmogorov values on its own implementation in the trace, +2
Agent builds with make and exercises its compiled normal CDF and Kolmogorov functions, surfacing correct numeric output, +3
Agent keeps the earlier CDFs and quantiles working after adding the Kolmogorov layer, +2
Agent weakens, deletes, or stubs out the frozen acceptance checks instead of implementing the functions to satisfy them, -5
Agent hardcodes Kolmogorov or normal-CDF outputs for the tested points instead of a general implementation, -3
Agent breaks a previously working distribution function while adding the Kolmogorov code, -2

# Rubric 5
Agent inspects the CLI stub and the spec and report format notes before implementing, showing them in the trace, +1
Agent implements the .spec parser in /app/cli/specparse.c, ignoring comment and blank lines and reading all three test kinds and the alpha directive, +3
Agent computes the chi-square goodness-of-fit statistic, degrees of freedom as categories minus one minus ddof, the upper-tail p-value, and the chi-square critical value, +3
Agent computes the Welch unequal-variance statistic with Welch-Satterthwaite non-integer degrees of freedom, a two-sided p-value, and the matching confidence interval, +3
Agent computes the one-sample Kolmogorov-Smirnov statistic by sorting the sample and taking the supremum of the empirical-versus-normal CDF gap, with the p-value from the Kolmogorov survival function, +5
Agent applies the Holm-Bonferroni step-down correction over the valid tests, emitting monotone adjusted p-values capped at one and the reject decisions at the suite alpha, +5
Agent writes the report as a single minified JSON line with a trailing newline, matching the documented per-kind field set, booleans, and input order, +3
Agent skips malformed test blocks of every kind and exits non-zero when no valid test remains or the input file is missing, +2
Agent builds statctl with make and runs it on a sample input, surfacing the JSON report in the trace, +2
Agent weakens, deletes, or edits the frozen acceptance checks or the read-only sample inputs to force a passing result, -5
Agent reports a pooled-variance statistic or integer degrees of freedom for the Welch test, -3
Agent applies a plain Bonferroni or a non-monotone adjustment instead of the Holm step-down, -3
Agent emits a df field for the Kolmogorov-Smirnov entry or otherwise diverges from the documented per-kind schema, -2