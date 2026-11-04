# Company OS Migration Map

- **Status:** M1 done on 2026-11-05 ([ADR-019](../decisions/ADR-019-knowledge-tree-and-departments.md)); M2 to M4 open. Decisions D1, D2, D3 and D5 are made; D4 is partly done (§4). The tables below keep the old paths on purpose: they record what moved where.
- **Date:** 2026-11-05
- **Input:** AI Company architecture brief v5 (§4.2, §7.8 knowledge layout, §8 documentation layout, §15, §17, §19 steps 1 to 3); ADR-014; ADR-018.
- **Scope:** every tracked file in this repository. Project repositories (`lamplight-vigil`, `soucean-game`) are out of scope; their documents stay in them ([project-system.md §4](../design/project-system.md#4-project-specific-context)).

## 1. Why

The repository started as a game studio. Since ADR-014 it also holds the Web department's role, rules and project (Soucean Game). The two are mixed:

- `agents/` holds game roles, the web role and roles that serve both departments.
- `company/` and the core docs mix company-wide rules with game wording ("Game Studio", "Game Repository", "original games").
- Web-only material (production environments, the web-design tools) sits inside company-wide files.

The Board chose a full restructure into the brief's two trees (D3):

- **`knowledge/`** (brief §7.8) holds what the company knows and how it operates: company scope, department scope, project scope.
- **`docs/`** (brief §8) holds the engineering documentation of Company OS itself: architecture, design, decisions, integrations, operations, roadmap.

## 2. Current state

| Area | Files | What is mixed |
|---|---|---|
| Company definition | `company/` (4) | Game mission and game hierarchy inside company files |
| Roles | `agents/` (8) | 3 game roles, 1 web role, 4 used by both departments |
| Workflows | `workflows/` (14) | Mostly company-wide; project initialization is written for games only |
| Architecture and design | `docs/architecture/` (8), `docs/design/` (9) | Generic content in game wording; web rules inside `security-architecture.md` §10; normative task rules sit among system design docs |
| Decisions | `docs/decisions/` (20) | Historical records; ADR-014 founded the Web department |
| Registries | `projects/`, `dependencies/` | Projects carry a type but no department; dependencies have no department |
| Tooling | `.claude/`, `config/`, `scripts/`, `runtime/` | Company-wide; the package builder reads roles only from `agents/` and the company from `company/` |

A finding outside the move itself: `AGENTS.md` §2 still says "Paperclip is not installed". That is false since 2026-11-03.

## 3. Target layout

```text
company-os/
├── AGENTS.md, CLAUDE.md, README.md, CHANGELOG.md, CONTRIBUTING.md, VERSION
├── knowledge/
│   ├── README.md                     scopes, who may read what, loading order (brief §7.3–§7.5)
│   ├── company/
│   │   ├── README.md                 index
│   │   ├── COMPANY.md                company definition (Paperclip company description)
│   │   ├── ORGANIZATION.md           company org chart; links each department's roster
│   │   ├── OPERATING_MODEL.md
│   │   ├── policies/                 rules.md, provider-allocation.md
│   │   ├── standards/                task-contract.md
│   │   ├── agents/<id>/AGENTS.md     director, producer, project-manager, ui-designer, qa
│   │   ├── workflows/                company-wide workflows (14 files, README included)
│   │   └── shared/                   cross-department contracts: game-platform-contract.md
│   ├── departments/
│   │   ├── README.md                 what a department owns; how to add one
│   │   ├── game/
│   │   │   ├── README.md             charter
│   │   │   ├── agents/               game-designer, gameplay-programmer
│   │   │   ├── workflows/            new-game-concept.md
│   │   │   └── domain/               game-rules.md (original games, hotspot defaults, review gates)
│   │   └── web/
│   │       ├── README.md             charter (from ADR-014)
│   │       ├── agents/               web-engineer
│   │       └── domain/               production-environments.md
│   └── projects/
│       ├── README.md                 how projects are registered
│       ├── registry.yaml             from projects/project-registry.yaml
│       ├── project-config.schema.yaml
│       ├── lamplight-vigil/README.md entrypoint only: repository, department, links into the repo
│       └── soucean-game/README.md
├── dependencies/                     registry.yaml (+ departments field); assignments/ later (brief §5)
├── config/, scripts/, runtime/, .claude/
└── docs/
    ├── README.md, conventions.md
    ├── vision/                       company-vision.md, principles.md, terminology.md
    ├── architecture/                 overview, system-components, repository-architecture, runtime-architecture,
    │                                 data-flow, security-architecture, stage1-gap-analysis, company-core,
    │                                 departments, knowledge-and-context-access, cross-department-collaboration
    ├── design/                       agent-system, company-design, workflow-system, project-system,
    │                                 dependency-system, integration-system
    ├── decisions/                    ADRs (unchanged)
    ├── integrations/                 unchanged
    ├── operations/                   unchanged, studio-bootstrap → company-bootstrap
    ├── guides/                       ai-agent-onboarding
    └── roadmap/                      phases.md, open-questions.md
```

Rules for placing a file:

1. **Normative knowledge an agent or the Board follows** (rules, roles, workflows, standards, charters) goes in `knowledge/`. **Engineering documentation of the system** goes in `docs/`.
2. Would a second department follow it unchanged? Then `knowledge/company/`. Only one department? Then `knowledge/departments/<dept>/`.
3. A contract between departments goes in `knowledge/company/shared/` with one named owner; both charters link it.
4. Decision records stay in `docs/decisions/` and are never edited.
5. Project documents stay in the project's own repository. `knowledge/projects/<id>/` holds only the entrypoint and registry data.
6. Departments without a role yet (Marketing, Operations) get no folder until their first role exists (brief §2.10).

**Layout and access.** The tree is shaped so that read access can later be granted per folder (company scope, one department, one project). In v1 nothing enforces it: agents run as the Board's Windows user, and Paperclip agents do not read this repository at run time (brief v5 §7.2). `knowledge-and-context-access.md` will state this.

**Paperclip.** `scripts/setup/build-package.py` builds the package from `knowledge/company/COMPANY.md`, `knowledge/company/agents/*` and `knowledge/departments/*/agents/*`. Paperclip never sees the repository layout.

## 4. Decisions for the Board

| # | Question | Options | Status |
|---|---|---|---|
| D1 | Where do the roles that serve every department live (`director`, `producer`, `project-manager`, `ui-designer`, `qa`)? | (a) `knowledge/company/agents/`; (b) one copy per department (`game-qa`, `web-qa`, …) | **Decided 2026-11-05: (a).** Split only when one department needs its own instance with different rules |
| D2 | Who is the Paperclip root agent? | (a) keep `game-director`; (b) add a new company-level role above it; (c) rename `game-director` to `director`, a company-wide director for every department | **Decided 2026-11-05: (c).** `director` is the root and the head of every department; it keeps product direction for games (pillars, vision) and takes the same role for the website. No new agent |
| D3 | Layout | (a) least churn (only department material moves); (b) the brief's `knowledge/` tree | **Decided 2026-11-05: (b)**, with `docs/` kept for engineering documentation as brief §8 describes |
| D4 | Local names that still say "game studio": `~/game-studio-workspace`, `~/.config/game-studio`, `~/.local/state/game-studio`, `start-studio.cmd` | (a) rename in step M3; (b) keep | **Partly done 2026-11-05:** the Board renamed the repository folder to `company-os`. `~/game-studio-workspace` and `start-studio.cmd` keep their names until M3; `~/.config/game-studio` and `~/.local/state/game-studio` were never created |
| D5 | Does a department get its own lead under `director`? | (a) not yet; (b) add `game-lead` / `web-lead` | Follows from D2: **(a)**. Revisit when a department has three or more roles or `director` becomes a bottleneck |

## 5. File-by-file map

Classes (brief §19): `KEEP` · `UPDATE` (wording or content revised) · `MOVE` · `SPLIT` (shared part and department part go to different places) · `REPLACE` · `ARCHIVE` · `ADD`. A `MOVE` may also be `UPDATE`.

"Generalize terms" means: "Game Studio" → the company or Company OS; "Game Project" → Project; "Game Repository" → Project Repository; "studio machine" → company machine. `docs/vision/terminology.md` defines them first.

### 5.1 Repository root and tooling

| File | Class | Target | Reason |
|---|---|---|---|
| `AGENTS.md` | UPDATE | — | Company OS framing; the two trees; fix the stale "Paperclip is not installed" |
| `CLAUDE.md` | KEEP | — | Only redirects to `AGENTS.md` |
| `README.md` | UPDATE | — | Company with departments; where to start |
| `CHANGELOG.md` | KEEP | — | New entries per step |
| `CONTRIBUTING.md` | UPDATE | — | Placement rules (§3) |
| `VERSION` | UPDATE | — | 0.2.0 when M1 lands |
| `.gitignore` | KEEP | — | — |
| `.claude/skills/paperclip/SKILL.md` | UPDATE | — | New paths to the gap analysis and triage workflow; no "studio" wording |
| `.claude/skills/paperclip/scripts/pc.py` | KEEP | — | — |
| `config/paperclip/agents.json` | UPDATE | — | `game-director` → `director`; add `department` per agent |
| `config/providers.example.yaml` | KEEP | — | — |
| `scripts/setup/build-package.py` | UPDATE | — | Read `knowledge/company/COMPANY.md`, `knowledge/company/agents/*`, `knowledge/departments/*/agents/*`; fail on duplicate slugs; projects stay in `config/paperclip/agents.json` (stdlib cannot read YAML) |
| `scripts/setup/post-import.py` | UPDATE (M3) | — | Workspace path after D4 |
| `runtime/README.md`, `runtime/tools/review-wake-watchdog.ts` | KEEP | — | — |
| `runtime/tools/start-studio.cmd` | MOVE (M3) | `runtime/tools/start-company.cmd` | D4 |
| new: link-rewrite script | ADD | `scripts/maintenance/move-files.py` | Moves files with `git mv` and rewrites every relative link from a mapping table; used for M1 |

### 5.2 `company/` → `knowledge/company/`

| File | Class | Target | Reason |
|---|---|---|---|
| `company/COMPANY.md` | SPLIT | `knowledge/company/COMPANY.md`; game mission and values → `knowledge/departments/game/README.md` | Today's mission is a game studio's; Core gets the company mission |
| `company/ORGANIZATION.md` | SPLIT | `knowledge/company/ORGANIZATION.md`; per-department rosters → each charter | One company chart with `director` at the root |
| `company/RULES.md` | MOVE + UPDATE | `knowledge/company/policies/rules.md` | R1.4 "game code" → "project code"; R7.1 "original games" → `knowledge/departments/game/domain/game-rules.md`, also repeated in the game role files |
| `company/OPERATING_MODEL.md` | MOVE + UPDATE | `knowledge/company/OPERATING_MODEL.md` | "Direction review against game pillars" → per-department cadence under `director` |
| new | ADD | `knowledge/README.md`, `knowledge/company/README.md` | Indexes: purpose, owner, audience, what to load when (brief §7.8) |

### 5.3 `agents/` → `knowledge/company/agents/` and `knowledge/departments/*/agents/`

| File | Class | Target | Reason |
|---|---|---|---|
| `agents/game-director/AGENTS.md` | MOVE + UPDATE | `knowledge/company/agents/director/AGENTS.md` | D2: company-wide director and Paperclip root; widened from games to every product, game authority (pillars) labelled for game projects |
| `agents/producer/AGENTS.md` | MOVE + UPDATE | `knowledge/company/agents/producer/` | D1; `reportsTo: director`; generalize terms |
| `agents/project-manager/AGENTS.md` | MOVE + UPDATE | `knowledge/company/agents/project-manager/` | D1; generalize terms |
| `agents/ui-designer/AGENTS.md` | MOVE + UPDATE | `knowledge/company/agents/ui-designer/` | D1; works for both departments |
| `agents/qa/AGENTS.md` | MOVE + UPDATE | `knowledge/company/agents/qa/` | D1; keep `slug: qa-engineer` |
| `agents/game-designer/AGENTS.md` | MOVE + UPDATE | `knowledge/departments/game/agents/game-designer/` | Game-only; `reportsTo: director` |
| `agents/gameplay-programmer/AGENTS.md` | MOVE | `knowledge/departments/game/agents/gameplay-programmer/` | Game-only |
| `agents/web-engineer/AGENTS.md` | MOVE | `knowledge/departments/web/agents/web-engineer/` | Web-only (ADR-014) |

Every role file changes in M1, at least its relative links, so the new texts must be applied to the 8 live agents afterwards (OQ-040). The live `game-director` agent is renamed `Director`. Its URL key follows the name, and its reports keep their link because Paperclip stores manager IDs.

### 5.4 `workflows/` → `knowledge/company/workflows/`

| File | Class | Target | Reason |
|---|---|---|---|
| `README.md`, `task-delegation.md`, `development-cycle.md`, `parallel-tasks.md`, `task-failure-handling.md`, `daily-triage.md`, `approval-request.md`, `code-review-and-merge.md`, `agent-onboarding.md`, `add-external-dependency.md`, `add-execution-provider.md`, `register-existing-repository.md` | MOVE + UPDATE | `knowledge/company/workflows/` | Company-wide; generalize terms |
| `release-approval.md` | MOVE + UPDATE | `knowledge/company/workflows/release-approval.md` | "Release a game version" → "Release a project version" |
| `project-initialization.md` | SPLIT | Core: `knowledge/company/workflows/project-initialization.md` ("Create a new project": Board creates the repository, registry entry, Paperclip project, seeding Task). Game: `knowledge/departments/game/workflows/new-game-concept.md` (concept, vision and pillars). Web: platform steps from ADR-014 §3 → web charter | Today it is written only for games |

### 5.5 Department knowledge (new)

| File | Class | Content |
|---|---|---|
| `knowledge/departments/README.md` | ADD | What a department owns (brief §4.2), how to add one, placement rules |
| `knowledge/departments/game/README.md` | ADD | Charter: mission and values from `COMPANY.md`, roles, review gates, links to ADR-001 and ADR-005 |
| `knowledge/departments/game/domain/game-rules.md` | ADD | Original games only (R7.1), default hotspot files for Phaser projects, game design authority |
| `knowledge/departments/game/workflows/new-game-concept.md` | ADD | Game part of `project-initialization.md` |
| `knowledge/departments/web/README.md` | ADD | Charter from ADR-014: platform projects, environments, Board-only actions, design-tool policy |
| `knowledge/departments/web/domain/production-environments.md` | ADD | Web details from `security-architecture.md` §10 (Supabase keys, ads, player data on the website) |

### 5.6 Projects

| File | Class | Target | Reason |
|---|---|---|---|
| `projects/project-registry.yaml` | MOVE + UPDATE | `knowledge/projects/registry.yaml` | Add `department` (`game` for Lamplight Vigil, `web` for Soucean Game) and contributing departments |
| `projects/project-config.schema.yaml` | MOVE + UPDATE | `knowledge/projects/project-config.schema.yaml` | `department` field, required; `$id` path |
| new | ADD | `knowledge/projects/README.md`, `knowledge/projects/lamplight-vigil/README.md`, `knowledge/projects/soucean-game/README.md` | Entrypoints only: repository, owning department, links to the repository's `AGENTS.md` and docs |

### 5.7 Dependencies

| File | Class | Target | Reason |
|---|---|---|---|
| `dependencies/registry.yaml` | UPDATE | — | Add `departments`: `game-development` entries → `[game]`, `web-design` entries → `[web]`, tooling → `[all]` |
| `dependencies/README.md` | UPDATE | — | Explain the field; assignments come in M4 (brief §5) |

### 5.8 `docs/` (engineering documentation)

| File | Class | Target | Reason |
|---|---|---|---|
| `docs/README.md` | UPDATE | — | Index both trees |
| `docs/conventions.md` | UPDATE | — | Status labels and hierarchy also cover `knowledge/` |
| `docs/glossary.md` | MOVE + UPDATE | `docs/vision/terminology.md` | Brief §8; defines Company, Company Core, Department, Project Repository; old game terms listed as former names |
| new | ADD | `docs/vision/company-vision.md`, `docs/vision/principles.md` | Vision from README and COMPANY; principles from `docs/README.md` §2 and brief §2 |
| `docs/architecture/overview.md`, `system-components.md`, `runtime-architecture.md`, `data-flow.md` | UPDATE | — | Company Core + departments + shared Runtime; generalize terms |
| `docs/architecture/repository-architecture.md` | UPDATE | — | New layout (§3); project repository layout; local paths after D4 |
| `docs/architecture/security-architecture.md` | SPLIT | §10 rule stays, generalized to "projects with production environments"; its web details → `knowledge/departments/web/domain/production-environments.md` | The principle is company-wide; the specifics are Web's |
| `docs/architecture/stage1-gap-analysis.md` | KEEP | — | — |
| `docs/architecture/open-questions.md` | MOVE + UPDATE | `docs/roadmap/open-questions.md` | Brief §8; tag website questions OQ-036 to OQ-039 `web` |
| `docs/architecture/company-os-migration-map.md` | ARCHIVE after M1 | — | This file |
| new | ADD | `docs/architecture/company-core.md`, `departments.md`, `knowledge-and-context-access.md`, `cross-department-collaboration.md` | Brief §4, §7 (including what v1 does not enforce), §12 |
| `docs/design/company-design.md` | SPLIT | Company hierarchy, decision authority, escalation stay; game authority (pillars) → game charter | Today it describes a game studio |
| `docs/design/agent-system.md` | UPDATE | — | Role locations, `department` field, roles grouped by scope |
| `docs/design/workflow-system.md`, `project-system.md`, `dependency-system.md`, `integration-system.md` | UPDATE | — | Department workflows extend Core ones; owning department per project; dependency departments |
| `docs/design/task-contract.md` | MOVE | `knowledge/company/standards/task-contract.md` | Normative rule agents and the Board follow |
| `docs/design/provider-allocation.md` | MOVE | `knowledge/company/policies/provider-allocation.md` | Board staffing policy |
| `docs/design/game-platform-contract.md` | MOVE | `knowledge/company/shared/game-platform-contract.md` | Contract between Game and Web; design owner `director` (GAM-16 in the archived company, to be re-created in Soucean) |
| `docs/decisions/*` (20 files) | KEEP | — | Never edited. ADR-001's repository name is superseded by ADR-018 |
| new | ADD | `docs/decisions/ADR-019-knowledge-tree-and-departments.md` | Records D1 to D5 and §3 |
| `docs/integrations/*.md` (5) | UPDATE | — | Wording only |
| `docs/operations/*.md` (8) | UPDATE (M3) | — | Local paths after D4; wording |
| `docs/operations/studio-bootstrap.md` | MOVE + UPDATE | `docs/operations/company-bootstrap.md` | Name; new source paths |
| `docs/guides/ai-agent-onboarding.md` | UPDATE | — | Read `knowledge/README.md` first, then the relevant scope |
| `docs/guides/implementation-roadmap.md` | MOVE + UPDATE | `docs/roadmap/phases.md` | Brief §8; add the brief's phases |

Totals: about 35 files move, about 18 are added, 5 are split, the rest are updated or kept.

## 6. Execution plan

Each step is its own PR. Before each PR: the link checker reports 0 problems, the package builds, and an import dry run against Soucean matches 8 of 8 agents.

| Step | Contents | Paperclip impact |
|---|---|---|
| **M1 Restructure** | ADR-019; `scripts/maintenance/move-files.py` with the mapping table from §5; all moves; the 5 splits; the director rename; indexes and charters; builder reads the new paths; fix `AGENTS.md` status | Rename the live `game-director` agent to `Director`; apply the new texts of all 8 roles (OQ-040) |
| **M2 Wording** | Terminology first, then generalize terms across `knowledge/` and `docs/` | Role texts change again: apply to the 8 agents. M1 and M2 can be one PR if the Board prefers a single re-apply |
| **M3 Local names** (D4) | Rename the workspace and config/state folders; `start-company.cmd`; script defaults; post-import updates project and agent `cwd` | Paths updated by `post-import.py`; restart Paperclip from the new folder with all agents paused |
| **M4 Access and collaboration** | `knowledge-and-context-access.md`, `cross-department-collaboration.md` filled; dependency assignments | None |

## 7. Risks

| Risk | Mitigation |
|---|---|
| Hundreds of relative links break (about 130 references to `agents/`, 100 to `workflows/`, 90 to `company/`) | Moves only through `move-files.py`, which rewrites links from the mapping table; the link checker gates every PR |
| Live agents drift from Git after M1 and M2 | Apply instruction changes in the same session as each merge; record the date |
| M3 breaks running worktrees (absolute paths) | Do it with all agents paused and no task in progress; `git worktree repair` |
| A split hides a shared rule | Placement rule 2 (§3): when in doubt, keep it in `knowledge/company/` |
| Readers and other sessions use old paths | The `CHANGELOG.md` entry lists the mapping; `AGENTS.md` points to `knowledge/README.md` |

## Related documents
[repository-architecture.md](repository-architecture.md) · [../decisions/ADR-014-platform-project-type.md](../decisions/ADR-014-platform-project-type.md) · [../decisions/ADR-018-rename-framework-repository.md](../decisions/ADR-018-rename-framework-repository.md) · [../design/agent-system.md](../design/agent-system.md) · [../operations/studio-bootstrap.md](../operations/company-bootstrap.md)
