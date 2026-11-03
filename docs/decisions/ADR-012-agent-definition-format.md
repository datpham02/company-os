# ADR-012: Agent Definitions Aligned with the Agent Companies Package Format

- **Status:** Proposed
- **Date:** 2026-11-03
- **Deciders:** Board Operator (pending)
- **Related:** ADR-002, [agent-system.md](../design/agent-system.md), OQ-007

## Context
Agent Roles must be defined in Git, provider-independent, and loadable into Paperclip. Paperclip documents a vendor-neutral "Agent Companies" package format (`agentcompanies/v1-draft`, `docs/companies/companies-spec.md`, verified at commit `7b8aa60`). In it, `COMPANY.md` defines a company and `agents/<slug>/AGENTS.md` defines an agent with YAML frontmatter (`name`, `title`, `reportsTo`, `skills`) and a Markdown body holding the agent's default instructions. Paperclip's CLI documents `company import` and `company export` for such packages.

## Decision (proposed)
- Each Agent Role is defined in `agents/<agent-id>/AGENTS.md`.
- Frontmatter uses the Agent Companies fields (`name`, `title`, `reportsTo`, `skills`, `description`) plus Game Studio fields under `metadata.gameStudio`, as specified in [agent-system.md §3](../design/agent-system.md#3-agent-definition-file-format).
- The Markdown body is the canonical role instruction and follows the section structure in [agent-system.md](../design/agent-system.md).
- Vendor-specific adapter config, absolute paths, and secrets MUST NOT appear in agent files (also a rule of the spec).
- Whether the repository can be imported directly with `paperclipai company import`, or needs a generated package (because `COMPANY.md` lives in `company/` rather than at the package root), is `UNVERIFIED` (OQ-007).

## Alternatives considered
| Alternative | Why not chosen |
|---|---|
| Custom YAML agent schema | Would need a converter for Paperclip anyway. |
| `agents/<id>/AGENT.md` (singular) | Not recognised by the Agent Companies format. |
| Define agents only inside Paperclip's UI | Not versioned; not reusable across instances. |

## Consequences
- Codex treats `AGENTS.md` as instructions for the directory it lives in. These files are only loaded if Codex is started inside `agents/<agent-id>/`, which the studio does not do.
- The format is a draft (`v1-draft`); upstream changes must be tracked (OQ-007).

## Reconsider when
- The Agent Companies format changes incompatibly, or
- Paperclip import proves unsuitable and a different loading mechanism is chosen.
