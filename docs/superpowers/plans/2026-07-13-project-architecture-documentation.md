# Project Architecture Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the root README with an accurate project entry point and add a maintainer-focused architecture reference.

**Architecture:** Keep `README.md` concise and navigational, while `docs/architecture/` owns detailed descriptions of system context, technology choices, component boundaries, data flows, and development conventions. Derive every claim from repository manifests, runtime modules, deployment files, tests, and existing design records.

**Tech Stack:** Markdown documentation for a Python 3.10+ / FastAPI / vn.py backend, React 18 / TypeScript / Vite frontend, parquet and DuckDB market-data storage, and PostgreSQL / Redis live-trading infrastructure.

## Global Constraints

- This is a documentation-only change; do not modify application code, manifests, generated API artifacts, or deployment behavior.
- Document current repository behavior and label emerging or incomplete live-trading capabilities explicitly.
- Use exact dependency versions only when a repository manifest pins or declares them.
- Preserve historical records under `agent-docs/` unchanged.
- Every linked document, referenced path, and command must exist in the repository.

---

## File Structure

- Modify `README.md`: concise project entry point, quick start, repository map, commands, and links.
- Create `docs/architecture/README.md`: architecture index and system context.
- Create `docs/architecture/tech-stack.md`: runtime, library, storage, infrastructure, and tooling inventory.
- Create `docs/architecture/components.md`: subsystem ownership, dependencies, and boundaries.
- Create `docs/architecture/data-flows.md`: end-to-end operational flows.
- Create `docs/architecture/development.md`: configuration, local services, verification, generated files, and maintenance rules.

### Task 1: Architecture index and system context

**Files:**
- Create: `docs/architecture/README.md`

**Interfaces:**
- Consumes: subsystem names and boundaries present in the repository.
- Produces: stable relative links to the four focused architecture documents used by `README.md`.

- [ ] **Step 1: Confirm source paths**

Run: `rg --files appapi appui data_pipeline quant_runtime trade_runtime trade_supervisor deploy`

Expected: output includes source files beneath all seven paths.

- [ ] **Step 2: Write the architecture index**

Create a document with these exact top-level sections: `Purpose`, `System Context`, `Subsystem Map`, `Runtime Status`, and `Further Reading`. Describe the browser UI, HTTP API, data pipeline, quant runtime, trade runtime, supervisor, PostgreSQL, Redis, and CTP gateway relationships. State that live trading is an emerging foundation and requires environment-specific CTP dependencies and credentials.

- [ ] **Step 3: Verify its links**

Run: `rg -n "tech-stack\.md|components\.md|data-flows\.md|development\.md" docs/architecture/README.md`

Expected: all four filenames appear as relative Markdown links.

- [ ] **Step 4: Commit the architecture index**

```powershell
git add docs/architecture/README.md
git commit -m "docs: add architecture overview"
```

### Task 2: Technology stack and component boundaries

**Files:**
- Create: `docs/architecture/tech-stack.md`
- Create: `docs/architecture/components.md`

**Interfaces:**
- Consumes: `appui/package.json`, Python requirement files, API and runtime packages, and `deploy/compose.live-trading.yml`.
- Produces: technology and ownership references linked from the architecture index and root README.

- [ ] **Step 1: Re-read authoritative manifests**

Run: `Get-Content appui/package.json, appapi/requirements.txt, data_pipeline/requirements.txt, quant_runtime/requirements.txt, trade_runtime/requirements.txt, deploy/compose.live-trading.yml`

Expected: frontend packages, Python dependency floors, and PostgreSQL/Redis service versions are visible.

- [ ] **Step 2: Write `tech-stack.md`**

Use the sections `Languages and Runtimes`, `Frontend`, `API and Services`, `Quant and Data`, `Live-Trading Infrastructure`, and `Developer Tooling`. Distinguish declared minimum versions from exact package-manager or container versions. Include React, Redux Toolkit, Ant Design, Lightweight Charts, FastAPI, Uvicorn, pandas, DuckDB, PyArrow, vn.py, PostgreSQL, Redis, pytest, ESLint, Prettier, and Docker Compose only where supported by repository files.

- [ ] **Step 3: Write `components.md`**

Use one subsection per top-level subsystem: `appui`, `appapi`, `data_pipeline`, `quant_runtime`, `trade_runtime`, `trade_supervisor`, `deploy`, and `scripts`. For each, document responsibility, direct dependencies, and explicit non-responsibilities. Note that `appapi` orchestrates backtests but does not implement strategy simulation, while `quant_runtime` owns strategy execution.

- [ ] **Step 4: Check claims against manifests and paths**

Run: `rg -n "React|FastAPI|DuckDB|vn\.py|PostgreSQL|Redis|appui|appapi|data_pipeline|quant_runtime|trade_runtime|trade_supervisor" docs/architecture/tech-stack.md docs/architecture/components.md`

Expected: every listed technology and subsystem appears in the appropriate document.

- [ ] **Step 5: Commit stack and component documentation**

```powershell
git add docs/architecture/tech-stack.md docs/architecture/components.md
git commit -m "docs: document stack and component boundaries"
```

### Task 3: Data flows and development conventions

**Files:**
- Create: `docs/architecture/data-flows.md`
- Create: `docs/architecture/development.md`

**Interfaces:**
- Consumes: API routes and services, pipeline modules, runtime runners and workers, configuration modules, deployment files, scripts, and tests.
- Produces: operational and maintenance references linked from the architecture index and root README.

- [ ] **Step 1: Inspect flow entry points**

Run: `rg -n "APIRouter|def main|if __name__|Redis|parquet|run_backtest|command" appapi data_pipeline quant_runtime trade_runtime trade_supervisor scripts`

Expected: route, runner, storage, and command-handling entry points are listed.

- [ ] **Step 2: Write `data-flows.md`**

Use the sections `Market-Data Ingestion`, `K-Line Query`, `Backtesting`, `Authentication`, and `Live-Trading Commands`. Describe each flow as an ordered sequence with named packages and persisted stores. Separate implemented behavior from deployment-dependent live-trading integration.

- [ ] **Step 3: Write `development.md`**

Use the sections `Local Configuration`, `Running Services`, `Test Layout`, `Generated Artifacts`, and `Maintenance Rules`. Include commands that exist in package scripts or repository entry points. Explain that `appui/src/api/generated/` is generated, `data/input/` contains raw inputs, and canonical parquet outputs live under `data/output/1min` and `data/output/5min`.

- [ ] **Step 4: Check commands and paths**

Run: `Test-Path appui/src/api/generated, data/input, data/output/1min, data/output/5min, scripts/generate_openapi.py, scripts/verify_ctp_runtime.py`

Expected: six `True` results.

- [ ] **Step 5: Commit flow and development documentation**

```powershell
git add docs/architecture/data-flows.md docs/architecture/development.md
git commit -m "docs: document project flows and development"
```

### Task 4: Root README entry point

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: all five files under `docs/architecture/`.
- Produces: the repository landing page and primary navigation into the architecture reference.

- [ ] **Step 1: Rewrite the README**

Use the top-level sections `Overview`, `Capabilities`, `Architecture`, `Repository Map`, `Quick Start`, `Common Commands`, `Configuration`, `Documentation`, and `Project Status`. Retain accurate backend, frontend, quant-runtime, and proxy commands from the existing README. Add links to each architecture document and state the live-trading maturity limitation.

- [ ] **Step 2: Verify required README content**

Run: `rg -n "docs/architecture|python -m appapi\.main|pnpm dev|quant_runtime\.runner|live trading" README.md`

Expected: architecture links, backend command, frontend command, quant runner command, and live-trading status text all match.

- [ ] **Step 3: Commit the README**

```powershell
git add README.md
git commit -m "docs: refresh project README"
```

### Task 5: Documentation verification

**Files:**
- Verify: `README.md`
- Verify: `docs/architecture/*.md`

**Interfaces:**
- Consumes: the completed documentation set.
- Produces: evidence that scope, paths, links, and formatting are correct.

- [ ] **Step 1: Scan for unfinished content**

Run: `rg -n "TBD|TODO|PLACEHOLDER|implement later" README.md docs/architecture`

Expected: no matches.

- [ ] **Step 2: Verify referenced local paths**

Manually extract every backtick-delimited repository path and relative Markdown link from the six documentation files, then run `Test-Path` for each local target.

Expected: every target returns `True`; URLs and command fragments are excluded from the path check.

- [ ] **Step 3: Check Markdown whitespace and final diff**

Run: `git diff --check HEAD~4..HEAD`

Expected: no output and exit code 0.

- [ ] **Step 4: Confirm documentation-only scope**

Run: `git diff --name-only HEAD~4..HEAD`

Expected: only `README.md` and files under `docs/architecture/` are listed.

- [ ] **Step 5: Record any verification correction**

If verification required corrections, stage only the affected documentation and commit them:

```powershell
git add README.md docs/architecture
git commit -m "docs: correct architecture references"
```

If no correction was required, do not create an empty commit.
