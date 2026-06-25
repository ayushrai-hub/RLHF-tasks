# Task Subtypes (Subcategories)

Optional `subcategories = [...]` in `task.toml`. Multiple allowed. Leave empty if none apply.

## 1. Long Context (`long_context`)

Requires reading **large documents** (≥ **50k tokens**). Must need semantic understanding — not keyword search or programmatic parsing.

**Formats:** PDF, DOCX, MD/TXT, HTML docs, JSON/YAML schemas, CSV with metadata, chat logs, email threads.

**Checklist:** Use platform Long Context Task Checklist before submit/review.

## 2. Tool Specific (`tool_specific`)

SDKs/APIs where models underperform: Blender, FFmpeg, ImageMagick, Graphviz, MLflow, WandB, Prefect, Superset, GIMP, QGIS, etc.

Include tool name in `tags`.

## 3. API Integration (`api_integration`)

Build, interact with, or debug APIs. **API source in environment**; mocked in Docker; terminal-only (no MCP).

Frameworks: Flask, Rails, Rust API, Spring Boot, Django, Express, Fastify, Play, Gin, etc.

**Avoid oversaturating FastAPI** — used heavily in other datasets.

## 4. DB Interaction (`db_interaction`)

Problem-solving via database engines — not reading flat CSV as a substitute for DB work.

Types: SQL, NoSQL, vector DBs, in-memory DBs. CSV-only DBs should be minority.

Include DB software in `tags`.

## 5. UI Building (`ui_building`)

Create/edit UIs. Still verify with **Python pytest**; use Playwright Python bindings if browser automation needed — not JS/TS Playwright suites.

Use UI skeleton: `stb init ... -t ui`

## task.toml

```toml
subcategories = ["api_integration", "db_interaction"]
tags = ["flask", "postgresql", "rest-api", "debugging"]
```

Independent of `category` — see [task-type-taxonomy.md](../task-type-taxonomy.md).
