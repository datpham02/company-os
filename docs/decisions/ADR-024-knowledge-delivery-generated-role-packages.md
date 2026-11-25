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
- Board decisions of 2026-11-23: KD-BD-2 set the delivery direction (Git canonical, native Paperclip mechanisms first, deterministic generation, mandatory policy never only in optional skill discovery), and KD-BD-3 asked for this ADR. The Knowledge Delivery change set (items 1-8) asked for this implementation. The PR #111 review replaced the 32,000 B + 6,000 B budget for the game-artist pilot. Its 40,000 / 8,000 / 48,000 figures were sized from the 43,307 B role-plus-rules package. Restoring task-contract §2, §6 and §8, security §8 and game-rules §6 in full does not fit in 48,000 B, so the pilot cap was set to 47,000 / 8,000 / 53,000, the measured text rather than a cut. On 2026-11-25 the Board raised it to 48,000 / 8,000 / 54,000 (Issue #113, Option A), because regeneration at HEAD measured 47,871 B core and 53,765 B combined after rules.md R2 gained the Draft-PR delivery rule and task-contract §2 gained the capability preview subsection.

## Decision (proposed)
1. **Role Knowledge Manifest.** `config/paperclip/knowledge-manifest.json` declares, per role, the units of source text delivered to the agent. A unit is selected by exact heading, by the opening words of a block, or by exact line. It records knowledge status (`approved` / `proposed` / `experimental` / `superseded`), governance authority and delivery method. The delivery methods are: `always_loaded`, `command_reference` (both verified channels in the managed file), `skill_assigned` (not verified until a run opens it), `on_demand_verified` (a channel the agent can open without a paste), `on_request` (a human paste; not verified delivery) and `not_delivered`. Mandatory policy does not depend on `on_request`. Phrase coverage and the conflict scan are lexical lints, not semantic equivalence and not proof that every conflict is resolved.
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
7. **Deployment is opt-in per role.** The default `sync-instructions.py` run does not replace an installed generated package with the legacy role body; it skips that role and says why. A generated package is pushed only by the single-role mode (`--generated-package --role R --confirm R`), which deploys the committed artifact at HEAD (a working-tree file with an intact self-declared hash is refused), writes a backup snapshot outside the repository (company id, agent id, content hash), aborts if the revision moves before the write, and reads the file back. Restore refuses a snapshot whose hash, company or agent id does not match, including another agent with the same role slug. `check-agent-drift.py` separates package integrity, pinned provenance and freshness against HEAD content. Expected state is `legacy_baseline`, `pilot_prepared`, `pilot_active` or `rolled_back` (`config/paperclip/knowledge-delivery-state.json`). An active pilot with an empty `desiredSkills` is drift. `--check` at the pinned commit does not mean the knowledge is current.
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
- The game-artist pilot budget is 48,000 B core, 8,000 B command reference and 54,000 B combined (raised from 47,000 / 53,000 on 2026-11-25). It is not a budget for every role. Interim technical-art ownership, task contract §2, blocker protocol §6, reviews §8, security approval boundaries §8 and game rules §6 are `always_loaded`. Credentials stay `not_delivered` only where those requirements are already in a verified channel (lexical lint).
- `studio-art-identity-and-refinement` is the Knowledge Delivery pilot skill. It is not the deferred animation skill package (K5). U-B stays pending. U-F and K5 stay deferred. ADR-024 stays `PROPOSED`.
- Live behaviour (skill discovery, isolation flags, session reuse) stays `UNVERIFIED` until the pilot runs (OQ-050).
- Follow-up: packages for more roles, after the pilot evidence.

## Reconsider when
The pilot fails its checks; Paperclip gains per-agent read access to repository knowledge; the role file outgrows the budget; or the Agent Runtime takes over instruction delivery.
