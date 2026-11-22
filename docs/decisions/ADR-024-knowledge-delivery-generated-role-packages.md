# ADR-024: Knowledge Delivery through Generated Role Packages, a Capability Catalog and Reviewed Studio Skills

- **Status:** Proposed
- **Date:** 2026-11-23
- **Deciders:** Board Operator
- **Supplements:** [ADR-019](ADR-019-knowledge-tree-and-departments.md) (knowledge tree). Changes no Accepted ADR.
- **Related:** ADR-002, ADR-007, ADR-009, ADR-010, ADR-012, ADR-016 (Proposed), ADR-017 (Proposed), OQ-040, OQ-050, [knowledge-delivery.md](../operations/knowledge-delivery.md)

## Context
- Company OS Git is the canonical source of company knowledge ([ADR-019](ADR-019-knowledge-tree-and-departments.md)). Paperclip agents receive only their managed `AGENTS.md`; links from a role file into Company OS cannot be opened from a Task Workspace. This was observed in the Stage 1 smoke tests (SOU-88, SOU-90, SOU-92; Board R&D evidence, outside this repository).
- `sync-instructions.py` pushes the raw role body. Company rules (`rules.md`), the task contract and department rules reach an agent only where the role file restates them.
- Every Claude agent inherits the Board operator's user-level skills, plugins and auto-memory. The R&D inventory of 2026-11-23 counted about 130 skills per run. Which of these channels can be switched off per agent is partly `UNVERIFIED` (OQ-050).
- Board decisions of 2026-11-23: KD-BD-2 set the delivery direction (Git canonical, native Paperclip mechanisms first, deterministic generation, mandatory policy never only in optional skill discovery), and KD-BD-3 asked for this ADR. The Knowledge Delivery change set (items 1-8) asked for this implementation, with a budget of 32,000 B core plus a separate 6,000 B command-reference block.

## Decision (proposed)
1. **Role Knowledge Manifest.** `config/paperclip/knowledge-manifest.json` declares, per role, the units of source text delivered to the agent. A unit is selected by exact heading, by the opening words of a block, or by exact line. It records knowledge status (`approved` / `proposed` / `experimental` / `superseded`), governance authority and delivery method. The delivery methods are: always-loaded, command-reference, on-demand, skill or not-delivered.
2. **Deterministic generation from a commit.** `scripts/setup/gen-role-packages.py` reads sources only through `git show <commit>:<path>`. Its output is byte-identical across runs. Every generated section opens with a `kd:unit` marker that records the source file and section, the source commit, the content hash, status, role, department, authority and delivery method. The file header records the source commit and the package hash. Generated files carry "do not edit by hand" and are committed under `config/paperclip/generated/`.
3. **Fail, never drop.** Generation stops on any of these:
   - a missing source, heading, link target or anchor;
   - a role-file block that no unit claims;
   - a relative link that survives rewriting;
   - conflicting mandatory policies (one rule id with two texts, or `MUST X` against `MUST NOT X` / `Never X`);
   - experimental or superseded content in a delivered unit;
   - a normative sentence or an exact allowed command form that would leave the always-loaded or command-reference channel without a manifest coverage entry that names its delivered equivalent;
   - a secret pattern in any output;
   - an over-budget package.
4. **Mandatory content stays in verified channels.** Mandatory rules and exact allowed command forms are delivered only always-loaded or in the command-reference block of the managed `AGENTS.md`. Skills and on-demand documents add procedure and reference; they never carry a rule that exists nowhere else.
5. **Capability Catalog.** `scripts/setup/gen-capability-catalog.py` generates a catalog with role views. Its columns are registered, installed, approved, permitted, instructed, runtime verified and production validated, and each cell has a cited source or says `unknown`. "Permitted" is only the exact allow rule built from `agents.json`. **A catalog entry is not a permission grant.** Cursor roles are shown as "not enforced (Cursor sandbox disabled)". R&D-only tools are listed only as "not available".
6. **Studio Skills** are generated from reviewed knowledge, stored with their department (`knowledge/departments/<dept>/skills/<name>/`), and assigned per role through Paperclip `desiredSkills`. A procedure in a Studio Skill names only commands the role's allow rules permit.
7. **Deployment is opt-in per role.** The default `sync-instructions.py` run is unchanged. A generated package is pushed only by the single-role mode (`--generated-package --role R --confirm R`), which writes a backup snapshot first. `check-agent-drift.py` tells a legacy role body from a generated package by its header and reports adapter, skill and memory state read-only.
8. **The first deployment is the game-artist pilot** (changes A, B, C in [knowledge-delivery.md](../operations/knowledge-delivery.md)). Each change needs its own Board approval and has its own rollback.

## Alternatives considered
| Alternative | Why not chosen |
|---|---|
| Keep syncing the raw role body | Company rules and the task contract stay unreadable at runtime (SOU-88, SOU-92) |
| Let agents read Company OS directly | Not available in a Task Workspace; widening reads conflicts with R4.2 and with per-scope access (ADR-019) |
| Hand-compact the role body in a derived copy (R&D prototype) | Two texts for one role; review drift; Board item 1 requires generation from the canonical commit |
| Deliver company rules only as skills | Skill discovery is optional and `UNVERIFIED` for mandatory policy (KD-BD-2) |
| A separate knowledge database or platform | Out of scope by Board decision; Git plus Paperclip's native mechanisms suffice |

## Consequences
- The game-artist package at `616f6d1` is 31,818 B core, 5,894 B command reference and 37,712 B combined (limits 32,000 / 6,000 / 38,000). To fit, the manifest moves three role-file sections out of the always-loaded core, each with coverage evidence:
  - "Credentials" is not delivered, because the secrets system-prompt rule and R4.1 deliver it;
  - "Ownership with Gameplay Programmer (interim)" goes on demand;
  - company sections that the role file restates go on demand.

  The Board should confirm these choices.
- The margin under the budget is small (182 B core). A longer role file stops generation until the manifest or the role file changes, by design.
- Live behaviour (skill discovery, isolation flags, session reuse) stays `UNVERIFIED` until the pilot runs (OQ-050).
- Follow-up: packages for more roles, after the pilot evidence.

## Reconsider when
The pilot fails its checks; Paperclip gains per-agent read access to repository knowledge; the role file outgrows the budget; or the Agent Runtime takes over instruction delivery.
