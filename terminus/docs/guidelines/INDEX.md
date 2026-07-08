# Documentation Index

Complete Terminus Edition 2 reference for the **RLHF-tasks** automation system.

| Resource | Location |
|----------|----------|
| Task library (21 tasks) | [`tasks/`](../tasks/) · [`tasks/README.md`](../tasks/README.md) |
| Main README | [`README.md`](../README.md) |
| Terminus hub | [`terminus/README.md`](../terminus/README.md) |
| Accuracy review prompt | [`prompt.md`](../prompt.md) |
| CLI | `./scripts/terminus <command> <task-dir>` |

---

## Workflow

| Doc | Purpose |
|-----|---------|
| [submission-checklist.md](../submission-checklist.md) | Pre-submit checklist |
| [creating-task.md](creating-task.md) | Scaffold → develop → submit |
| [ci-iteration.md](ci-iteration.md) | Fix CI/LLMaJ failures |
| [after-submission.md](../after-submission.md) | Post-submit review process |

## Task Design

| Doc | Purpose |
|-----|---------|
| [task-requirements.md](../task-requirements.md) | Structural requirements |
| [task-components.md](task-components.md) | File layout & components |
| [task-type-taxonomy.md](../task-type-taxonomy.md) | 9 categories |
| [task-subtypes.md](../task-subtypes.md) | Subcategories |
| [milestones.md](milestones.md) | Multi-step tasks |
| [prompt-styling.md](prompt-styling.md) | instruction.md style |
| [difficulty.md](difficulty.md) | Calibrating pass rates |
| [what-makes-a-good-task.md](../what-makes-a-good-task.md) | Quality principles |
| [bad-examples.md](bad-examples.md) | Anti-patterns |
| [common-errors.md](common-errors.md) | Instruction/test/env anti-patterns |
| [quality-guidelines.md](quality-guidelines.md) | TB2 quality bar (reward, latency, etc.) |
| [long-context-checklist.md](long-context-checklist.md) | `long_context` subcategory gate |
| [defending-submission.md](defending-submission.md) | Appeals & feedback response |
| [submission-diversity.md](../submission-diversity.md) | New submission rules |

## Implementation

| Doc | Purpose |
|-----|---------|
| [docker-environment.md](docker-environment.md) | Dockerfile setup & patterns |
| [dockerfile.md](dockerfile.md) | Canonical images & CI policy |
| [oracle-solution.md](oracle-solution.md) | solution/solve.sh |
| [writing-tests.md](writing-tests.md) | test.sh + pytest |
| [rubrics.md](rubrics.md) | Platform rubric workflow |
| [submission-export-format.md](submission-export-format.md) | `entire-report.txt` section map for reviewers |

## Validation

| Doc | Purpose |
|-----|---------|
| [oracle-agent.md](oracle-agent.md) | harbor run -a oracle |
| [agent-testing.md](agent-testing.md) | GPT-5.5 / Claude Opus 4.8 |
| [interactive-container.md](interactive-container.md) | harbor tasks start-env -i |
| [ci-checks.md](ci-checks.md) | CI check reference |
| [llmaj-checks.md](llmaj-checks.md) | LLM-as-Judge checks |
| [agent-review.md](agent-review.md) | Claude static review |
| [review-guidelines.md](review-guidelines.md) | Peer review process |
| [reviewer-checklist.md](../reviewer-checklist.md) | Quick review checklist |
| [reviewer-checklist-full.md](../reviewer-checklist-full.md) | Full severity-tagged checklist |
| [reviewer-checklist-ui.md](../reviewer-checklist-ui.md) | **55 portal checkboxes** |
| [faq.md](../faq.md) | Official FAQ (lifecycle, milestones, difficulty) |
| [../../prompt.md](../../prompt.md) | **Task accuracy review → `review-report.md`** |
| [../../templates/review-report.template.md](../../templates/review-report.template.md) | Review report template |

## CLI

```bash
./scripts/terminus validate <task-dir>
./scripts/terminus review <task-dir> [--report report.txt]
./scripts/terminus check-all <task-dir>
./scripts/terminus ci-check <task-dir>
./scripts/terminus rubric-validate <rubric.txt>   # optional rubric lint
```
