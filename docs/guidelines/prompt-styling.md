# Instruction Prompt Styling

`instruction.md` is the primary agent interface. Write like a real engineer prompting a terminal agent — not like an LLM.

## Six Principles

1. **Concise** — 1 sentence to 3 paragraphs; no long multi-requirement prompts
2. **Well specified** — clear goal; hard via engineering depth, not edge-case laundry lists
3. **Interesting** — useful to real developers
4. **No answers/hints** — requirements yes, step-by-step how-to no
5. **Unique** — not duplicate of existing Terminal Bench tasks
6. **Absolute paths** — `/app/file.txt`, never relative paths

## Human vs Synthetic

| | ❌ Synthetic | ✅ Human |
|---|-------------|---------|
| Tone | "You are an expert programmer..." | "We need to migrate the SQLite schema..." |
| Length | 500+ words | 150–200 words actionable |
| Guidance | "First, use ls to see files..." | "Source data is in /data. Output to /output/" |

**Avoid:** emojis, heavy markdown, GPT-style verbosity, canary strings.

## Anti-Patterns

### 1. Step-by-step walkthrough with solution values
Telling the agent exact flags, buffer sizes, or config values = giving the answer.

### 2. Hints / detection guidance sections
"Look for currency anomalies, transposed dates..." = leaked solution strategy.

### 3. Excessive markdown / API spec dumps
Structured endpoint docs read like synthetic prompts, not human requests.

### 4. Overly prescriptive file/function signatures
Exact exports, libraries, and build commands remove agent reasoning.

### 5. Bold markers on solution details
`**Policy limit**: $500` highlights answer fragments.

## Spec Files Loophole (Blocked)

Environment docs (`spec.md`, READMEs) must:

- Define **what** (schemas, contracts) — not **how** to solve
- Not split instructions out of `instruction.md` to dodge length limits
- Read like real engineering docs (RFCs, API contracts) — not LLM prompt extensions

## Milestone Instructions

- Milestone 1: include overall task context
- Later milestones: new requirements only, building on prior work

See [bad-examples.md](bad-examples.md).
