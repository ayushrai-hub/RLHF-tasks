# Task Subtypes (Subcategories)

A subset of tasks should align with **subtypes** that target key challenge areas. Tasks can use **multiple** subtypes when they span multiple challenge areas.

If your task aligns with none of these subcategories, leave `subcategories = []` in `task.toml`.

Subtypes are independent of `category` — see [Task Type Taxonomy](task-type-taxonomy.md).

---

## 1. Long Context (`long_context`)

Tasks that require models to test their context windows by reading **large documents**.

**Threshold:** Files must be at least **50k tokens** and **cannot** simply be parsed programmatically or through keyword search by the agent. The task must rely on the model's semantic understanding of the provided document.

### Supported formats & examples

**Text-heavy formats:**

- **PDF:** Academic papers (50–150 pages), regulatory filings (10-K), or ISO technical standards.
- **DOCX:** Legal contracts with deep appendices or internal architecture proposals.
- **Markdown/TXT:** Multi-day meeting transcripts or massive technical handbooks.

**Semi-structured content:**

- **HTML:** Entire documentation sites scraped into a single reference file.
- **JSON/YAML:** Massive API schemas or nested configuration files with inline documentation.
- **CSV:** Wide datasets with extensive metadata headers and notes.

**Conversational/narrative:**

- **Chat logs:** Slack/Discord exports or weeks of customer support transcripts.
- **Email:** Long back-and-forth threads where the agent must track referenced attachments.

**Checklist:** Use [Long Context Task Checklist](guidelines/long-context-checklist.md) before submitting or reviewing any `long_context` task.

---

## 2. Tool Specific (`tool_specific`)

Tasks that target tools with SDKs and APIs where models generally underperform.

**Examples:** Blender, FFmpeg, ImageMagick, Graphviz, MLflow, WandB, Prefect, Superset, GIMP, QGIS, etc.

**Goal:** Exercises for these tools are highly useful for identifying agent blind spots in specialized workflows.

Include the tool name in `tags`.

---

## 3. API Integration (`api_integration`)

Tasks that involve building, interacting with, or debugging APIs to solve a task. These are specifically tasks where **the API source code is included in the environment**.

**Implementation:** APIs must be mocked within the Docker environment without external dependencies.

**Interaction:** The agent interacts strictly via the terminal (no MCP). Source code for the API must be included in the environment.

**Frameworks:** Flask, Ruby on Rails, Rust API, Spring Boot, Django, Express.js, Fastify, Play, Gin, and more.

**Avoid oversaturating FastAPI** — it is used heavily throughout other datasets and risks oversaturation if not avoided.

---

## 4. DB Interaction (`db_interaction`)

Tasks that involve gathering context and/or problem solving through interacting with a database. Avoid tasks where the agent can read the underlying data without directly interacting with the DB.

**DB types:** SQL, NoSQL, vector databases, in-memory databases, and more.

**The flat-file limit:** DBs represented purely as CSVs should make up a **minority** of DB-based tasks to ensure agents are actually interacting with database engines.

Include DB software in `tags`.

---

## 5. UI Building (`ui_building`)

Tasks that create, edit, or update a user interface.

**Verification:** UI tasks must still use **Python pytest** validators. If browser automation is needed, use **Playwright's Python bindings from pytest** rather than a JavaScript or TypeScript Playwright suite.

Use UI skeleton: `stb init ... -t ui`

---

## task.toml example

```toml
[metadata]
category = "software-engineering"
subcategories = ["api_integration", "db_interaction"]
tags = ["flask", "postgresql", "rest-api", "debugging"]
```

Multiple subtypes when applicable:

```toml
subcategories = ["db_interaction", "tool_specific"]
```

Leave empty when none apply:

```toml
subcategories = []
```
