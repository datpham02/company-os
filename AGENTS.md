# AGENTS.md — Instructions for AI Coding Agents

This file is the entry point for any AI coding agent (Claude Code, Codex, or another tool) working **on the Game Studio framework repository itself**. [CLAUDE.md](CLAUDE.md) points here.

> If you are a Game Studio *role agent* (for example `gameplay-programmer`) executing a task inside a **game repository**, your instructions come from your agent definition in [agents/](agents/) and from the game repository's own `AGENTS.md`, not from this file.

## 1. What this repository is

Game Studio is a reusable framework that defines an AI game-development studio: its organization, agent roles, rules, workflows, project registry, external dependency registry, integrations, and (later) a local Agent Runtime. Paperclip is the independent orchestration platform that runs the studio day to day.

Start here: [docs/README.md](docs/README.md). The fastest orientation for an AI agent is [docs/guides/ai-agent-onboarding.md](docs/guides/ai-agent-onboarding.md).

## 2. Current implementation status

- Status of the framework: **documentation-only** (version in [VERSION](VERSION)).
- The Agent Runtime is **PLANNED**. The only Runtime code is the Stage 2 gap filler `runtime/tools/review-wake-watchdog.ts`. Do not describe any other Runtime command as working.
- Paperclip is **not installed** in this environment as of the last audit (see [docs/architecture/open-questions.md](docs/architecture/open-questions.md)).

## 3. Rules you MUST follow

1. You MUST NOT add game source code to this repository. Game code lives in independent game repositories (see [ADR-005](docs/decisions/ADR-005-independent-game-repositories.md)).
2. You MUST NOT copy, vendor, or submodule external projects into this repository. Register them in [dependencies/registry.yaml](dependencies/registry.yaml) instead ([ADR-007](docs/decisions/ADR-007-external-dependency-registry.md)).
3. You MUST NOT modify Paperclip source code from this repository ([ADR-002](docs/decisions/ADR-002-paperclip-independent-orchestration.md)).
4. You MUST NOT invent Paperclip, Claude Code, Codex, OpenSpec, or MCP capabilities. Mark unverified claims `UNVERIFIED` and add them to [docs/architecture/open-questions.md](docs/architecture/open-questions.md).
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
| Operational process | `workflows/` | [workflows/README.md](workflows/README.md) |
| Agent role | `agents/<agent-id>/AGENTS.md` | [company/ORGANIZATION.md](company/ORGANIZATION.md) |
| Studio rule | [company/RULES.md](company/RULES.md) | Affected workflows |
| External tool | [dependencies/registry.yaml](dependencies/registry.yaml) | — |
| Game project | [projects/project-registry.yaml](projects/project-registry.yaml) | — |
| Unverified assumption | [docs/architecture/open-questions.md](docs/architecture/open-questions.md) | — |

## 5. Documentation conventions

Normative terms (MUST, MUST NOT, SHOULD, MAY) and status labels (`APPROVED`, `PROPOSED`, `PLANNED`, `UNVERIFIED`, `IMPLEMENTED`, `DEPRECATED`) are defined in [docs/conventions.md](docs/conventions.md). Terminology is defined in [docs/glossary.md](docs/glossary.md).

## 6. Provider-specific notes

- **Claude Code** loads [CLAUDE.md](CLAUDE.md), which redirects here. It also loads the project skill [`.claude/skills/paperclip`](.claude/skills/paperclip/SKILL.md), which lets the Board Operator run Paperclip from chat (status, release, approve, create and assign tasks) through the REST API.
- **Codex** loads `AGENTS.md` files from the repository root down to its working directory. Agent definition files under `agents/<agent-id>/AGENTS.md` are role definitions, not instructions for working on this repository; Codex will only load one if started inside that directory.
