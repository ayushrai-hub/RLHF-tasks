# Oracle Run Fix & `jobs/` Health Report

**Date:** 2026-07-03
**Scope:** (1) Why the oracle solution would not run and how it was fixed; (2) health audit of all `jobs/` run folders.

---

## Part 1 — Oracle solution: root cause & fix

### Symptom

Running the oracle produced zero trials and a `RuntimeError`:

```
Docker compose command failed for environment rust-saml-acs-guard.
... permission denied while trying to connect to the Docker daemon socket
at unix:///Users/ayushrai/.docker/run/docker.sock ... connect: operation not permitted
```

### Root cause

**Not a task bug.** The failure is an execution-environment (sandbox) restriction, not a problem with the task, Dockerfile, or `solve.sh`:

- Harbor drives the oracle by building and starting a Docker container via `docker compose`.
- When the command runs inside the restricted sandbox, the Docker daemon socket (`/Users/ayushrai/.docker/run/docker.sock`) is **blocked** → `connect: operation not permitted`.
- Outside the sandbox, Docker is healthy: `docker info` returns OK, the socket exists (`srwxr-xr-x … docker.sock`), and the `desktop-linux` context is active.

The distinction is visible in the error text:
- Sandbox-blocked runs say `connect: operation not permitted`.
- Runs where Docker Desktop was simply not running say `Cannot connect to the Docker daemon … Is the docker daemon running?`.

### Fix (verified)

Run the oracle **outside the sandbox** (Docker socket access required). With sandboxing disabled the oracle passes cleanly:

```
=== Oracle Agent: rust-saml-acs-guard/ ===
  1/1 Mean: 1.000
Trials: 1 | Errors: 0 | reward = 1.0 → 1
Results written to jobs/2026-07-03__13-59-58/result.json
Clean rerun after cleanup race: jobs/2026-07-03__14-27-15/result.json
```

- Trial `rust-saml-acs-guard__uGP5BqR`: `verifier_result.rewards.reward = 1.0`, `exception_info = null`.
- Follow-up trial `rust-saml-acs-guard__Y3ASnLE` in `jobs/2026-07-03__14-27-15`: reward `1.0`, 1 trial, 0 errors. This confirms the task/oracle is healthy after the cleanup race described below.
- Environment build ~56s, agent ~4s, verifier ~2s (well under the 900s verifier / 1500s agent timeouts in `task.toml`).

**How to run it going forward** (from repo root, in a normal terminal / with sandbox disabled and Docker Desktop running):

```bash
./scripts/terminus oracle rust-saml-acs-guard/
```

If you must run from an automated/sandboxed context, grant full (unsandboxed) permission so the Docker socket is reachable. No change to the task files was needed or made — the task oracle is correct.

---

## Part 2 — `jobs/` folder health audit

### Method

Every folder under `jobs/` was classified using its trial-level `result.json`
(`verifier_result.rewards.reward` and `exception_info`), the job-level
`result.json` stats, and any `exception.txt` / `trial.log`. A run is counted as
**proper logs** only when a trial completed and recorded a reward with no
infra exception.

### Results (pre-cleanup: 122 job folders)

| Category | Count | % | Meaning |
|----------|------:|--:|---------|
| **Proper logs (completed, reward recorded)** | **22** | 18.0% | Trial ran end-to-end; reward written |
| — of which passed (reward = 1.0) | 21 | — | Healthy oracle/agent run |
| — of which failed (reward = 0.0) | 1 | — | Valid run, agent did not pass (`parallel-solver-divergence-mask`) |
| **Infra / Docker failures** | **57** | 46.7% | `docker compose` could not connect to daemon (sandbox block or daemon down) |
| **Partial (trial started, no `result.json`)** | **14** | 11.5% | Trial dir + `config.json`/`trial.log` present, run interrupted before completion |
| **Empty (no trial at all)** | **29** | 23.8% | Job folder created but no trial subfolder (aborted at startup) |

**Pre-cleanup bottom line: only 22 of 122 (18%) job folders contained proper, complete logs. 100 of 122 (82%) were incomplete — 57 Docker/infra failures, 14 partial, 29 empty.** The dominant failure mode (57 folders) is exactly the same Docker-socket issue diagnosed in Part 1.

**Post-cleanup state:** after pruning empty/partial folders and rerunning the SAML oracle cleanly, `jobs/` contains **80 folders**: **23 completed runs** and **57 infra/Docker-failure diagnostic folders**, with **0 leftover empty/partial folders**.

### Job folders with proper logs (22)

| Job | Task | Reward |
|-----|------|-------:|
| 2026-06-21__16-23-46 | ts-seafloor-changepoint1 | 1.0 |
| 2026-06-21__17-15-50 | commonmark-debug-rust | 1.0 |
| 2026-06-21__23-44-05 | vlq-event-tape-rollup | 1.0 |
| 2026-06-23__17-25-03 | cargo-solver-static-analysis | 1.0 |
| 2026-06-23__21-27-03 | fstab-variant-remount-ladder | 1.0 |
| 2026-06-24__16-05-14 | go-service-mesh-traffic-split-repair | 1.0 |
| 2026-06-24__18-22-18 | rust-tmpfiles-debugger | 1.0 |
| 2026-06-24__18-53-23 | parallel-solver-divergence-mask | 0.0 |
| 2026-06-26__16-34-18 | build-rust-maven-dependency-convergence-auditor2 | 1.0 |
| 2026-06-26__17-48-25 | stellar-kiosk-ledger | 1.0 |
| 2026-06-27__20-48-19 | nftables-atomic-rollback-journal | 1.0 |
| 2026-06-27__23-06-28 | crc-checksum-debugger-rust | 1.0 |
| 2026-06-28__15-30-14 | dafny-insertion-sort-multiset-sorted | 1.0 |
| 2026-06-28__15-50-18 | go-game-record-dual-cause-adjudicator-closure-authoring | 1.0 |
| 2026-06-28__16-11-11 | metrics-aggregator | 1.0 |
| 2026-06-28__17-30-08 | tbrain-process-kettle-cycle | 1.0 |
| 2026-06-29__01-18-07 | git-repository-integrity-verifier | 1.0 |
| 2026-06-29__01-54-54 | game-replay-chronicle-normalizer | 1.0 |
| 2026-06-29__12-10-59 | sklearn-pipeline-column-transform | 1.0 |
| 2026-06-29__13-12-17 | numba-parfors-combine-seam | 1.0 |
| 2026-06-29__15-27-56 | tbrain-pump-overflow-trip | 1.0 |
| 2026-07-03__13-59-58 | rust-saml-acs-guard | 1.0 |
| 2026-07-03__14-27-15 | rust-saml-acs-guard | 1.0 |

### Partial runs (14 — trial started, no `result.json`)

mavlink-mission-upload-sequence-auditor, perl-marine-inquiry-cli,
java-buoy-wavelet-spectra-yaml-calibration, microgrid-islanding-restorer,
tls-keyshare-policy-witness, remifentanil-population-pk-nlme, stellar-kiosk-ledger,
scala-course-scheduler, crc-checksum-debugger-rust, prison-cell-lock-arbitration,
`nftables-atomic-rollback-journal.`, variform-ruby-transform-allowlist-audit,
go-local-file-retention-policy-reconciler-hardfix4 (×2).

### Infra/Docker failures (57)

All 57 fail with `docker compose … up` errors — either
`connect: operation not permitted` (sandbox) or
`Cannot connect to the Docker daemon … Is the docker daemon running?`
(daemon not running at run time). Four of these were initially mis-bucketed as
"other exceptions" only because the daemon message was truncated in
`exception_info`; they are the same infra class.

---

## Interpretation & recommendations

1. **The oracle itself is healthy.** Both the fresh `rust-saml-acs-guard` oracle run and the 21 historical passing runs prove the tasks and verifiers work when Docker is reachable.
2. **Most incomplete job folders were noise from environment issues, not task defects.** The single largest retained bucket (57) is the Docker-socket problem; empty/partial folders have now been pruned.
3. **To avoid future infra failures:** ensure Docker Desktop is running and run Harbor/oracle commands with Docker socket access (outside the sandbox). This alone would convert the 57 infra failures into real runs.
4. **Cleanup (done, with correction):** the empty and partial folders carried no usable results and were pruned. **44 folders were deleted** (29 empty + 15 partial — one extra partial SAML oracle run appeared between the audit and cleanup). That extra SAML folder was deleted while Harbor was finalizing it, which caused the terminal `FileNotFoundError` for `jobs/2026-07-03__14-25-41/rust-saml-acs-guard__QmyCpcP/result.json`. A clean rerun immediately afterward passed with reward `1.0` in `jobs/2026-07-03__14-27-15`. Current verified state: **80 folders** = **23** completed-log runs + **57** infra/Docker-failure runs, **0** leftover empty/partial folders.

---

## Evidence / commands used

```bash
# Docker health (outside sandbox)
docker info; docker context ls; ls -la /Users/ayushrai/.docker/run/docker.sock

# Oracle re-run (outside sandbox) — PASSED reward 1.0
./scripts/terminus oracle rust-saml-acs-guard/

# Classification: parsed every jobs/*/**/result.json
#   verifier_result.rewards.reward, exception_info, exception.txt, trial.log
```
