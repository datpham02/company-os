# ADR-018: Rename the Framework Repository to `company-os`

- **Status:** Accepted
- **Date:** 2026-11-05
- **Deciders:** Board Operator
- **Related:** ADR-001, ADR-016, AI Company architecture brief v5

## Context
The framework is growing from a game studio into a company with several departments (Game, Web, later Marketing and Operations). ADR-001 names the single framework repository `datpham02/game-studio`. On 2026-11-04/05 the Board asked to rebuild the Paperclip company from the versioned package (ADR-016) and to rename the repository and its local folder.

## Decision
- The framework repository is `datpham02/company-os`, renamed on GitHub (history, issues and PRs kept; GitHub redirects the old URL).
- The local checkout folder is `company-os`.
- Everything else in ADR-001 stays: exactly one framework repository, no game code in it.
- The live Paperclip company is now **Soucean** (issue prefix `SOU`), imported from the package. The former company "Game Studio Soucean" (`GAM`) is paused and kept as an archive until the Board deletes it.
- Folder and documentation names that still say "Game Studio" (for example `~/game-studio-workspace`, `.config/game-studio`) are renamed later, together with the department split.

## Alternatives considered
| Alternative | Why not chosen |
|---|---|
| Create a new repository | Loses history, issues and PR links |
| Keep the name | Misleading once Web and other departments live here |

## Consequences
- Remotes and links must use the new name; old links redirect.
- Task branches in the new company are `SOU-<n>-<slug>`; allowlists were rebuilt with the `SOU` prefix.
- Claude Code keys its local memory by folder path, so the memory folder was copied to the new path.

## Reconsider when
The company name changes again or departments move into separate repositories.
