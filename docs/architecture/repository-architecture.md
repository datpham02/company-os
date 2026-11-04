# Repository Architecture

## 1. Repositories

| Repository | Contents | Owner | Status |
|---|---|---|---|
| `datpham02/company-os` (renamed from `game-studio` on 2026-11-05, ADR-018) | Framework: studio definition, registries, docs, Runtime source | Board Operator | Local directory exists at `/home/datpt/game-studio`; **not yet a Git repository**, no remote configured (audit 2026-11-03) |
| `datpham02/<project-id>` (one per game) | Game source, assets, game docs, game-local agent instructions, game-local OpenSpec specs | Board Operator | None registered yet |
| `paperclipai/paperclip` | Paperclip | Paperclip maintainers | External; installed via npm (`paperclipai`), never cloned into this repo |
| Other dependencies | See [dependencies/registry.yaml](../../dependencies/registry.yaml) | Their maintainers | External |

Rules (ADR-001, ADR-005, ADR-007): the Framework Repository holds no game code and no external source. Game Repositories hold no framework copy.

## 2. Framework Repository layout

Legend: ✅ exists · ◻ planned, created when first needed (not created empty).

```text
company-os/
├── README.md, VERSION, CHANGELOG.md, CONTRIBUTING.md    ✅
├── AGENTS.md, CLAUDE.md                                  ✅ instructions for AI agents working on this repo
├── .gitignore                                            ✅
├── knowledge/                                            ✅ operating knowledge (ADR-019)
│   ├── company/    COMPANY, ORGANIZATION, OPERATING_MODEL, policies/, standards/, agents/ (5 shared roles), workflows/ (13 + README), shared/
│   ├── departments/ game/ (charter, 2 roles, workflows/, domain/), web/ (charter, 1 role, domain/)
│   └── projects/   registry.yaml, project-config.schema.yaml, one entrypoint per project
├── dependencies/   README.md, registry.yaml              ✅
├── config/         paperclip/agents.json, providers.example.yaml   ✅
├── scripts/        setup/ (build-package, post-import), maintenance/ (move-files)   ✅
├── integrations/   ◻ adapter code/config per system
├── runtime/        README.md, tools/ (review-wake watchdog, start script)   ✅
│   ├── src/        ◻ Runtime (PLANNED)
│   └── tests/      ◻
├── templates/      ◻ files seeded into a new project repository
└── docs/           ✅ vision, architecture, design, decisions, integrations, operations, guides, roadmap
```

### 2.1 Deviations from the target structure (documented)

| Target item | Decision | Reason |
|---|---|---|
| Empty directories (`integrations/`, `templates/`, `schemas/`, `runtime/src`) | Not created | Brief: "Do not create unnecessary empty directories." |
| `dependencies/<category>/` subdirectories | Not created; category is a field in `registry.yaml` | Avoids duplicating data between the registry and per-category files. Subdirectories are created only for long-form notes. |
| `knowledge/company/workflows/` has 4 files in the target | 12 files + README | Brief §4.4 requires 12 workflows; the 4 target names are kept for the corresponding workflows. |
| `docs/design/workflows/` | Not created | Brief allows using `knowledge/company/workflows/` instead. |
| Schema location: `knowledge/projects/project-config.schema.yaml` vs `schemas/` | Kept in `knowledge/projects/` as specified; future schemas go in `schemas/` | Logged as C-003 for a final decision. |
| Added `AGENTS.md`, `CLAUDE.md`, `.gitignore`, `docs/conventions.md`, `docs/vision/terminology.md` | Added | Required for Codex/Claude Code usability and consistent terminology. |

## 3. Game Repository layout (`PROPOSED`)

The framework does not dictate engine structure. It requires only:

```text
<project-id>/
├── AGENTS.md            Instructions for agents working on this game (engine, build, test, conventions)
├── CLAUDE.md            Points to AGENTS.md (same pattern as the framework)
├── .game-studio.yaml    PROPOSED: project ID and framework version this repo was set up with
├── openspec/            OPTIONAL: OpenSpec specs and changes (see openspec-integration.md)
└── <engine-specific source and assets>
```

Seeding these files is part of [project-initialization.md](../../knowledge/company/workflows/project-initialization.md). A template directory (`templates/game-project/`) is `PLANNED`.

## 4. Local directory organization on the studio machine

| Path (default, `PROPOSED`) | Purpose | In Git? |
|---|---|---|
| `~/game-studio/` | Framework Repository clone (current location `/home/datpt/game-studio`) | Yes (framework repo) |
| `~/game-studio-workspace/repos/<project-id>/` | Primary Checkout of each Game Repository | Yes (game repo), but agents never work here |
| `~/game-studio-workspace/worktrees/<project-id>/<task-key>/` | Task Workspaces (Git worktrees) when the Runtime owns worktrees | Worktree of game repo; directory itself is Runtime Data |
| `~/.config/game-studio/` | Runtime configuration (local paths, concurrency, provider defaults) | No |
| `~/.local/state/game-studio/runs/<run-id>/` | Run records, logs, transcripts | No |
| `~/.claude/`, `~/.codex/` | Provider credentials and settings | No, never |
| Paperclip instance directory | Paperclip DB, managed workspaces, run logs | No. Location set by Paperclip (`UNVERIFIED`, OQ-002/OQ-025) |

When Paperclip owns execution workspaces (ADR-011 Stage 1), Task Workspaces live where Paperclip puts them, not under `~/game-studio-workspace/worktrees/`.

## 5. Git ownership boundaries

| Action | Allowed actor | Where |
|---|---|---|
| Edit framework definitions | Board Operator; agents via PR | Framework Repository |
| Create Task Branch, commit | Agent Instance (through its Provider) | Task Workspace only |
| Push Task Branch | Agent Instance or Git Manager, with project-scoped credentials | Game Repository remote |
| Open pull request | Agent Instance or Git Manager (`PLANNED`) | GitHub |
| Approve and merge PR | Board Operator only (ADR-009) | GitHub |
| Push to Default Branch, force-push, delete branches/repos, rewrite history | **Nobody automated.** Board Operator manually, deliberately | — |
| Create a new Game Repository | Board Operator (or Runtime after approval, OQ-018) | GitHub |

## 6. What belongs in Git and what stays local

| In Git (Framework Repository) | Local only |
|---|---|
| Studio definitions, agent roles, rules, workflows | Runtime configuration with absolute paths |
| Project registry (portable fields only) | Credentials, tokens, `.env` files |
| Dependency registry | Run logs, transcripts, run state |
| Schemas, templates, scripts, Runtime source | Primary Checkouts and Task Workspaces |
| Docs, ADRs | Paperclip database and instance data |
| Example config (`*.example.yaml`) | Provider session data |

## Related documents
- [../decisions/ADR-001-single-game-studio-repository.md](../decisions/ADR-001-single-game-studio-repository.md) · [../decisions/ADR-005-independent-game-repositories.md](../decisions/ADR-005-independent-game-repositories.md) · [../decisions/ADR-010-runtime-data-outside-repository.md](../decisions/ADR-010-runtime-data-outside-repository.md)
- [../design/project-system.md](../design/project-system.md) · [../operations/configuration.md](../operations/configuration.md)
