# ADR-016: Versioned Paperclip Package as the Source of Agent Configuration

- **Status:** Proposed
- **Date:** 2026-11-04
- **Deciders:** Board Operator
- **Related:** ADR-012, OQ-007, OQ-023, OQ-031, OQ-040, [studio-bootstrap.md](../operations/studio-bootstrap.md)

## Context
ADR-012 imports roles from Git, but adapter config, permission allowlists, budgets and limits were then set by hand in the UI, and are not versioned. Facts checked on 2026-11-04 (Paperclip 2026.1023.0):
- Paperclip's package format has a `.paperclip.yaml` extension carrying adapter type and config, runtime settings, permissions, budgets, secret input names, projects and routines.
- Importing from the working repository also picks up gitignored worktree copies; a clean package folder does not.
- Import into an existing company refuses `--collision replace`, so re-import cannot update existing agents (OQ-040). ADR-012's statement that changes reach Paperclip by re-import with `--collision replace` does not hold for this version.
- `agents/qa` must declare `slug: qa-engineer` to match the live agent.

## Decision
- Git holds everything portable about an Agent Instance: role instructions (ADR-012), permission-profile allowlists and the reporting rule, budgets, WIP limit, secret input names, project workspace policies.
- A setup script builds a clean package folder outside the repository, including a generated `.paperclip.yaml` that combines the portable config with the provider allocation (ADR-015). The package MUST NOT contain secrets, absolute paths, UUIDs or UUID-scoped grants.
- A fresh instance is created with `company import --target new` from that package, then a post-import step fills machine-specific values and binds secrets.
- Until OQ-040 is resolved, changes to existing agents are applied by the Board from Git (UI or a confirmed API sync), never edited only in Paperclip.
- Each agent's folder name or frontmatter `slug` MUST equal its Paperclip URL key.

## Alternatives considered
| Alternative | Why not chosen |
|---|---|
| Keep configuring agents in the UI | Not reproducible; allowlists drift from security-architecture §4 |
| Commit a full `.paperclip.yaml` | It would hold the Board's provider choice and machine paths |
| Fresh company import for every change | Loses issue history and run records |

## Consequences
- Rebuilding the studio on a new machine becomes one import plus secrets.
- The setup scripts (`build-package`, `post-import`, later `sync-agents`) are new work (`PLANNED`).
- ADR-012's re-import consequence is superseded in part by this ADR once accepted.

## Reconsider when
Paperclip allows replace on existing-company imports, documents an agent sync API, or changes the package format.
