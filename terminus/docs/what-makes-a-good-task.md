# What Makes a Good Task

## Core Principle

A good task is one an **expert human solves confidently**, but that **challenges or stumps current AI agents**.

Genuine engineering challenges requiring multi-step reasoning, domain expertise, and practical problem-solving — not trivia or trick questions.

## Key Requirements

### 1. Difficulty Target

Worst-model accuracy must be **≤ 80%** (GPT-5.5 + Claude Opus 4.8).

| Tier | Criteria |
|------|----------|
| Hard | ≤20% on best or worst model |
| Medium | 20–60% on worst model |
| Easy | 60–80% on worst model |

### 2. Multi-Step Complexity

Chain multiple commands, handle intermediate states, reason across steps.

**Good:** "Debug the failing test suite, fix the three bugs causing failures, and verify all tests pass."

**Bad:** "Run the test suite." (too simple)

### 3. Clear & Unambiguous

Fully specified — agent knows exactly what to do.

**Good:** "Implement `find_longest_palindrome(s: str) -> str` returning the longest palindromic substring; ties → first occurrence."

**Bad:** "Write code for palindromes."

### 4. Testable & Verifiable

Deterministic tests verify completion.

### 5. No Cheating Opportunities

Agents must not be able to:

- Read test files for answers
- Edit data files to pass tests
- Delete tests to avoid failures
- Hardcode expected outputs

## How to Make Tasks Harder

| Technique | Description |
|-----------|-------------|
| Debugging-style | Agent must find root cause |
| Niche knowledge | Public but rarely-trained domains |
| Bespoke rules | Custom rule among common ones |
| Multi-step | Each step adds failure probability |

## What to Avoid

| Avoid | Why |
|-------|-----|
| Trivia questions | Tests memorization |
| Ambiguous requirements | Agent can't know expected behavior |
| External dependencies | API keys, network |
| Simple one-liners | Instant solve |
| Brittle tests | String matching, hardcoded values |

## Quality Checklist

- [ ] Problem statement clear and complete
- [ ] Difficulty < 80% pass rate
- [ ] Multi-step reasoning required
- [ ] All constraints explicitly stated
- [ ] Test cases cover all requirements
- [ ] No cheating opportunities
- [ ] Human-written instruction.md (not LLM-generated)

See [Submission Checklist](submission-checklist.md) before uploading.
