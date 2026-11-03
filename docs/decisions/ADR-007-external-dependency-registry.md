# ADR-007: External Dependency Registry

- **Status:** Accepted
- **Date:** 2026-11-03
- **Deciders:** Board Operator
- **Related:** ADR-001, [dependency-system.md](../design/dependency-system.md)

## Context
The studio relies on external tools: Paperclip, AI CLIs, OpenSpec, skill packs, MCP servers. Copying their source into the framework would create license, update, and drift problems.

## Decision
- External tools MUST be registered in [dependencies/registry.yaml](../../dependencies/registry.yaml).
- Game Studio MUST NOT vendor, copy, or submodule the source code of external projects into this repository.
- Each entry MUST record: identifier, name, source (repository or official docs), category, version constraint, installation reference, required/optional status, integration status, compatibility notes, and license when known.
- Listing a dependency in the registry does not approve its installation. Installation requires the approval gate in [add-external-dependency.md](../../workflows/add-external-dependency.md).

## Alternatives considered
| Alternative | Why not chosen |
|---|---|
| Vendor copies | License and update burden; violates "do not copy". |
| Git submodules | Couples framework history to external repos; still a copy in practice. |
| No registry (ad-hoc installs) | No traceability; agents cannot know what is available. |

## Consequences
- Installation happens on the machine (or in game repositories), following each tool's official instructions.
- Version drift must be checked against the registry ([dependency-system.md §6](../design/dependency-system.md)).

## Reconsider when
- A dependency must be patched and upstream will not accept the patch (then fork it as a separate repository and register the fork).
