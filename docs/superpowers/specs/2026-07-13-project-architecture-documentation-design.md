# Project Architecture Documentation Design

## Purpose

Improve the repository documentation for maintainers by making the root README a concise entry point and adding a dedicated architecture reference under `docs/architecture/`.

The documentation must describe the repository as it exists. Emerging or incomplete live-trading capabilities must be labeled clearly rather than presented as production-ready features.

## Audience

The primary audience is maintainers who need to understand subsystem ownership, dependencies, runtime boundaries, and end-to-end data flows. New contributors remain a secondary audience and should be able to use the root README to find setup instructions and the deeper architecture material.

## Documentation Structure

### Root README

`README.md` will remain the main project entry point. It will contain:

- the project purpose and current capabilities;
- a high-level architecture summary;
- a repository map;
- prerequisites and quick-start instructions;
- common development and verification commands;
- links to the detailed architecture documents.

It will avoid duplicating detailed component and data-flow explanations.

### Architecture Reference

Create `docs/architecture/` with these documents:

- `README.md`: architecture index, system context, and subsystem relationship summary;
- `tech-stack.md`: languages, frameworks, libraries, storage engines, infrastructure, and developer tooling;
- `components.md`: responsibility, dependencies, and boundaries of each top-level runtime or package;
- `data-flows.md`: market-data ingestion, K-line queries, backtesting, authentication, and live-trading command flows;
- `development.md`: configuration model, local services, tests, generated artifacts, and maintenance conventions.

## Source of Truth

Documentation claims will be derived from repository files, including Python requirements, the frontend package manifest, API routes and services, runtime modules, deployment configuration, tests, and existing design documents. Version claims will be exact only where the repository pins or declares them; otherwise the documented constraint will match the manifest.

## Content Boundaries

The update covers documentation only. It will not change application code, dependency declarations, runtime configuration, generated API artifacts, or deployment behavior.

Existing historical plans and design records under `agent-docs/` remain unchanged. The new `docs/architecture/` folder will describe the current system rather than preserve decision history.

## Accuracy and Maintenance

- Every referenced file and directory must exist.
- Commands must match the current package scripts and Python entry points.
- Cross-document links must resolve from their containing files.
- Generated or environment-specific directories will not be presented as source modules.
- Known gaps, such as incomplete production hardening for live trading, will be stated explicitly.

## Verification

After editing, verification will include:

1. reviewing the final diff for documentation-only scope;
2. scanning Markdown links and referenced repository paths;
3. comparing technology claims against requirement and package manifests;
4. checking commands against available scripts and entry points;
5. confirming the Git worktree contains only the intended documentation changes.

No application test suite is required solely for Markdown edits, because runtime behavior is unchanged.
