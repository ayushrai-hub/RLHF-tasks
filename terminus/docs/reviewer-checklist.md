# Reviewer Checklist (Quick Reference)

**Full severity-tagged checklist:** [reviewer-checklist-full.md](reviewer-checklist-full.md)  
**Review process:** [guidelines/review-guidelines.md](guidelines/review-guidelines.md)  
**Agent Review (advisory):** [guidelines/agent-review.md](guidelines/agent-review.md)

## Environment (High)

- [ ] No hidden step-by-step walkthroughs or solution hints in any env file
- [ ] No AI-framework scaffolding filenames (CLAUDE.md, skills.md, AGENTS.md, etc.)
- [ ] tmux and asciinema installed in Dockerfile
- [ ] No solution/ or tests/ copied into Docker image
- [ ] allow_internet = false; no runtime network installs in test.sh
- [ ] All FROM images digest-pinned (@sha256:)
- [ ] Final runtime base is canonical or has credible justification
- [ ] environment/ ≤ 100 MiB total, no file > 50 MiB

## Instructions (High)

- [ ] Concise, realistic engineering prompt (not LLM-style)
- [ ] No answers or hints in instruction.md or spec files
- [ ] Absolute paths used throughout
- [ ] spec.md not used to dodge instruction length limits

## Tests (High)

- [ ] Every prompt requirement has a corresponding test
- [ ] test.sh uses canonical reward block (no trailing exit required)
- [ ] No runtime package installs in test.sh

## Structure

- [ ] Correct layout for task type (regular vs milestone vs UI)
- [ ] Milestone: steps/milestone_N/ with per-milestone instruction, tests, solution
- [ ] number_of_milestones matches [[steps]] count in task.toml
- [ ] ZIP contains files inside folder, not nested extra folder

## Difficulty

- [ ] Oracle passes
- [ ] Worst-model pass rate < 80% (lowest rate among GPT-5.5 / Claude Opus 4.8) — **#54 only difficulty blocker**
- [ ] **Do not** fail/revise for `task.toml` `difficulty` vs platform classified mismatch — **#45 CHECK** when field present
- [ ] Task requires genuine engineering reasoning

## Rubric

- [ ] At least 3 negative rewards (evaluate **platform rubric** from submission report, not task zip)
- [ ] **Positive point cap:** non-milestone total ≤40; each milestone block ≤40 — **>40 is a main blocker (Revise)**
- [ ] Milestone tasks: `# Rubric 1`, `# Rubric 2` headers per milestone
- [ ] Non-milestone: flat `Agent …, ±N` lines
- [ ] Rubric aligns with current task version
