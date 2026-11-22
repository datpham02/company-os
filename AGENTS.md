# AGENTS.md — Instructions for AI Coding Agents

This file is the entry point for any AI coding agent (Claude Code, Codex, or another tool) working **on the Company OS framework repository itself**. [CLAUDE.md](CLAUDE.md) points here.

> If you are a *role agent* (for example `gameplay-programmer`) executing a task inside a **project repository**, your instructions come from your role file under [knowledge/README.md](knowledge/README.md) and from the project repository's own `AGENTS.md`, not from this file.

## 1. What this repository is

Company OS is the framework of an AI-operated company with departments (today Game and Web): its Company Core (organization, rules, shared roles, workflows, standards), each department's roles and knowledge, the project registry, the dependency registry, integrations, setup scripts and (later) a local Agent Runtime. Paperclip is the independent control plane that runs the company day to day.

Two trees ([ADR-019](docs/decisions/ADR-019-knowledge-tree-and-departments.md)):
- [knowledge/README.md](knowledge/README.md): what the company knows and how it operates. Company, departments, projects.
- [docs/README.md](docs/README.md): engineering documentation of Company OS itself.

The fastest orientation for an AI agent is [docs/guides/ai-agent-onboarding.md](docs/guides/ai-agent-onboarding.md).

## 2. Current implementation status

- The framework is mostly documentation (version in [VERSION](VERSION)). Implemented code: the Paperclip skill (`.claude/skills/paperclip/`, including the Board-credential helper `board_auth.py`), `scripts/setup/` (package build, post-import, role-text sync, read-only agent drift check, and the `PROPOSED` knowledge-delivery generators for role packages and the Capability Catalog, [ADR-024](docs/decisions/ADR-024-knowledge-delivery-generated-role-packages.md)), `scripts/maintenance/` (`move-files.py`; read-only `validate-registries.py`, `check-dependencies.py` and `merge-audit.py`; the authentication-migration tools `migrate-participants.py` and `auth-sandbox.py`), and the Stage 2 gap filler `runtime/tools/review-wake-watchdog.ts` (review wakes and stuck-issue alerts, rules in `stuck-rules.ts`).
- The Agent Runtime is **PLANNED**. Do not describe any other Runtime command as working.
- Paperclip 2026.1023.0 runs on the company machine in `local_trusted` mode. The live company is **Soucean** (`SOU`), imported from this repository on 2026-11-05 ([company-bootstrap.md](docs/operations/company-bootstrap.md)).

## 3. Rules you MUST follow

1. You MUST NOT add game source code to this repository. Game code lives in independent game repositories (see [ADR-005](docs/decisions/ADR-005-independent-game-repositories.md)).
2. You MUST NOT copy, vendor, or submodule external projects into this repository. Register them in [dependencies/registry.yaml](dependencies/registry.yaml) instead ([ADR-007](docs/decisions/ADR-007-external-dependency-registry.md)).
3. You MUST NOT modify Paperclip source code from this repository ([ADR-002](docs/decisions/ADR-002-paperclip-independent-orchestration.md)).
4. You MUST NOT invent Paperclip, Claude Code, Codex, OpenSpec, or MCP capabilities. Mark unverified claims `UNVERIFIED` and add them to [docs/roadmap/open-questions.md](docs/roadmap/open-questions.md).
5. You MUST NOT change an `Accepted` ADR silently. Propose a new ADR that supersedes it.
6. You MUST NOT label anything `IMPLEMENTED` unless the code exists in this repository and has been verified.
7. You MUST NOT commit secrets, local absolute paths of a specific machine, or Runtime data (logs, run state, worktrees) to this repository ([ADR-010](docs/decisions/ADR-010-runtime-data-outside-repository.md)).
8. You MUST NOT commit or push unless the human explicitly asks.
9. You SHOULD keep documents modular and update cross-references when you add or move a document.

## 4. Where to make changes

| Change | Location | Also update |
|---|---|---|
| Architectural decision | `docs/decisions/ADR-NNN-*.md` | [docs/decisions/README.md](docs/decisions/README.md) |
| Component contract | `docs/design/` | Related architecture doc |
| Company rule or policy | [knowledge/company/policies/rules.md](knowledge/company/policies/rules.md) | Affected workflows and role files |
| Company workflow | `knowledge/company/workflows/` | [its README](knowledge/company/workflows/README.md) |
| Role used by every department | `knowledge/company/agents/<agent-id>/AGENTS.md` | [ORGANIZATION.md](knowledge/company/ORGANIZATION.md), `config/paperclip/agents.json` |
| Department role, workflow or domain rule | `knowledge/departments/<dept>/` | The department's [charter](knowledge/departments/README.md), `config/paperclip/agents.json` for roles |
| Project | [knowledge/projects/registry.yaml](knowledge/projects/registry.yaml) | Its entrypoint `knowledge/projects/<id>/README.md` |
| External tool | [dependencies/registry.yaml](dependencies/registry.yaml) | — |
| Unverified assumption | [docs/roadmap/open-questions.md](docs/roadmap/open-questions.md) | — |

Placement rules: [knowledge/departments/README.md](knowledge/departments/README.md#placement-rules). Move files only with `scripts/maintenance/move-files.py`, which rewrites links.

## 5. Documentation conventions

Normative terms (MUST, MUST NOT, SHOULD, MAY) and status labels (`APPROVED`, `PROPOSED`, `PLANNED`, `UNVERIFIED`, `IMPLEMENTED`, `DEPRECATED`) are defined in [docs/conventions.md](docs/conventions.md). Terminology is defined in [docs/vision/terminology.md](docs/vision/terminology.md).

## 6. Provider-specific notes

- **Claude Code** loads [CLAUDE.md](CLAUDE.md), which redirects here. It also loads the project skill [`.claude/skills/paperclip`](.claude/skills/paperclip/SKILL.md), which lets the Board Operator run Paperclip from chat (status, release, approve, create and assign tasks) through the REST API.
- **Codex** loads `AGENTS.md` files from the repository root down to its working directory. Agent definition files under `knowledge/company/agents/<agent-id>/AGENTS.md` are role definitions, not instructions for working on this repository; Codex will only load one if started inside that directory.
