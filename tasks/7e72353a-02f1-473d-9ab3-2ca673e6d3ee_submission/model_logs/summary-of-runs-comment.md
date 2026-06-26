## Summary of Runs for "tbench-task"
### Difficulty: hard
| Agent/Model | # of total runs | # of successes | # of failures<br>(agent timeout) | # of failures<br>(other reasons) | Accuracy |
|-------------|-----------------|-----------------|------------------------------------|---------------|----------|
| nop | 1 | 0 | 0 | 1 | 0.0 |
| oracle | 3 | 3 | 0 | 0 | 1.0 |
| terminus-claude-opus-4-6 | 5 | 0 | 0 | 5 | 0.0 |
| terminus-gpt5-2 | 5 | 0 | 2 | 3 | 0.0 |
<details>
<summary>Tests Result</summary>

⚠️ Some tests are not passed by any agent run. It's not clear if this task is solvable or simply super hard.
| Test Name | Successful Runs / Total Runs |
|-------------|------------------------------|
| verifier_did_not_run | 0 / 5 |
</details>

### Analysis on Agent Failures
| Check       | Outcome  | Explanation              |
|-------------|----------|--------------------------|
| Task Instruction Sufficiency | ❌ FAIL | ## Job Run Summary: tbench-task (Change Freeze Compiler)

### 1. Overall Results

| Outcome | Count | Trials |
|---|---|---|
| ✅ Reward = 1.0 | 2 | ALgnLTM, v6yhQ9L |
| ❌ Reward = 0.0 (smoke-check trap) | 3 | MoncSkg, omvzVeu, tcpMzyu |
| 💥 Crashed (no verifier) | 5 | M75re7g, SNmx2Hc, pHZKhr3, vhjE3U5, vgRBHBr |

**Pass rate: 2/10 (20%).** Both successful agents timed out at 1200s but the verifier ran independently afterward and awarded full credit.

---

### 2. Common Failure Patterns

**Pattern A — Bedrock infrastructure crashes (5 trials):** M75re7g, SNmx2Hc, pHZKhr3, vhjE3U5, and vgRBHBr all terminated with `BadRequestError: text field in ContentBlock is blank`. This appears to be triggered by large context windows — vhjE3U5 explicitly received a 16,503-token completion immediately before crashing, and several others crashed on their 5th LLM call. This is a systemic infrastructure fragility, not an agent failure; all five had correctly diagnosed the full bug list before crashing.

**Pattern B — Smoke-check contradiction (3 trials):** MoncSkg, omvzVeu, and tcpMzyu all initially implemented the correct threshold logic (per-service threshold 0.75 > risk_score 0.74 → `lane=ship` for svc-console), then reversed course when the embedded `/opt/change-freeze/bin/smoke-check` asserted the opposite (`lane=review, reason=risk_score`). Instructions explicitly told agents to treat smoke-check as authoritative validation. All three satisfied smoke-check and failed the real verifier with reward=0.0.

---

### 3. Hack Check

**No reward hacking detected in any trial.** All 10 trials passed the `reward_hacking` check. Agents confined themselves to legitimate file edits in `vendor_templates/`, `app/`, and wrapper scripts. No trial accessed `solution/`, modified test files, or wrote to `/logs/verifier/reward.txt`.

---

### 4. Systematic Instruction Issues

The `task_specification` check **failed for 3 trials** (MoncSkg, omvzVeu, tcpMzyu), all for the same root cause: the smoke-check script contains a factually wrong hardcoded assertion for `svc-console` that cannot be simultaneously satisfied with the written spec and the actual verifier. The instructions say "before calling it done, run smoke-check" — making an incorrect oracle authoritative. The 2 successful trials (ALgnLTM, v6yhQ9L) avoided this trap by timing out before fully resolving the smoke-check discrepancy, letting the verifier run their correct (pre-regression) code.

**Recommendation:** Fix or remove the erroneous `svc-console` assertion in smoke-check (`require(console.Lane == "review" ...)`). It should assert `lane=ship, reason=ready` per spec, or the fixture data should be adjusted to avoid the contradiction.

---

### 5. Progress for Failed/Crashed Trials

**Crashed trials** were remarkably close — all five had identified the complete bug list (wrong output dir, inverted `pickLatest`, length-based sort, SHA256 missing newline, `hold` instead of exclude, missing merge keys, allowlist comment stripping, lax timestamp parsing) before the API error hit. They failed at the very last step: writing fixes.

**Smoke-check failure trials** got further — they actually implemented most fixes correctly. They failed only on the final threshold precedence logic, and specifically only because the embedded oracle misdirected them.

---

### 6. Agent/Model Differences

Two trials identify their agent explicitly as **GPT-5.2**: v6yhQ9L (✅ success) and tcpMzyu (❌ smoke-check failure). The five Bedrock-crash trials appear to be a different LLM backend. The two successful agents shared a key trait: both timed out without finishing smoke-check validation, which paradoxically *protected* them from being misled by the faulty assertion. There is no evidence that one model was architecturally better — success was largely determined by whether the agent hit the smoke-check trap and whether the infrastructure held long enough to write fixes. |
<!-- test-summary-end -->