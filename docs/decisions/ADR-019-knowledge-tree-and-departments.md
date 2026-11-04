# ADR-019: Knowledge Tree, Departments and a Company-wide Director

- **Status:** Accepted
- **Date:** 2026-11-05
- **Deciders:** Board Operator
- **Supersedes:** in part ADR-012 (role files now live under `knowledge/`, not `agents/`) and ADR-014 §4 (`web-engineer` file location)
- **Related:** ADR-001, ADR-005, ADR-014, ADR-016, ADR-018, [company-os-migration-map.md](../architecture/company-os-migration-map.md)

## Context
The repository grew from a game studio into a company with a Game and a Web department, but kept the studio layout: one `agents/` folder for every role, company files written for games, and web-only rules inside company-wide documents. The AI Company brief v5 proposes a `knowledge/` tree by scope (§7.8) and a separate `docs/` tree for engineering documentation (§8). The Board reviewed the migration map and decided D1 to D5 on 2026-11-05.

## Decision
- **D3 Layout.** Normative knowledge lives in `knowledge/`:
  - `knowledge/company/` holds Company Core: COMPANY, ORGANIZATION, OPERATING_MODEL, `policies/`, `standards/`, shared `agents/`, company `workflows/` and `shared/` cross-department contracts.
  - `knowledge/departments/<dept>/` holds each department's charter, its own roles, workflows and `domain/` knowledge.
  - `knowledge/projects/` holds the project registry and one entrypoint per project.
  - Engineering documentation stays in `docs/`, which gains `vision/` and `roadmap/`.
- **D1 Shared roles.** Roles that serve every department (`director`, `producer`, `project-manager`, `ui-designer`, `qa`) live in `knowledge/company/agents/`. A role is split per department only when a department needs its own instance with different rules.
- **D2 Root agent.** `game-director` is renamed `director`: the company-wide director, head of every department and the Paperclip root. It keeps product direction for games (vision, pillars) and takes the same role for the website.
- **D5 Department leads.** None for now; `director` leads both departments. Revisit when a department has three or more roles of its own or `director` becomes a bottleneck.
- **D4 Local names.** The repository folder is `company-os` (done). The workspace folder and `start-studio.cmd` are renamed in a later step (M3).
- Placement rules are in [knowledge/departments/README.md](../../knowledge/departments/README.md#placement-rules). A department workflow extends a company workflow; it never replaces one.
- Paperclip never sees this layout: `scripts/setup/build-package.py` maps role files into the package.

## Alternatives considered
| Alternative | Why not chosen |
|---|---|
| Least churn: keep `company/`, `agents/`, `workflows/` and add only `departments/` | The Board preferred a full restructure that matches the brief |
| One copy of each shared role per department | Duplicated instructions and agents before any department needs different rules |
| Keep `game-director` as root | A web role would escalate to a game role |
| Add a new company-level root above `game-director` | An extra agent with little work at this size |

## Consequences
- About 35 files moved; links were rewritten by `scripts/maintenance/move-files.py` from `scripts/maintenance/m1-moves.json`.
- Every role file changed (paths, and the director rename), so the live Paperclip agents must receive the new texts (OQ-040), and the live `Game Director` agent is renamed `Director`.
- Real enforcement of per-scope read access is still absent in v1 (brief v5 §7.2).
- Generalizing the remaining game wording ("Game Repository", "studio") is a follow-up step (M2).

## Reconsider when
Read access is enforced per scope, a department gets its own lead, or a third department starts.
