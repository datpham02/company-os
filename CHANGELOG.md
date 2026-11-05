# Changelog

All notable changes to the Game Studio framework are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow Semantic Versioning; the current version is in [VERSION](VERSION).

## [Unreleased]

### Added
- ADR-021: backend is Laravel + MySQL (no Supabase); Laravel Reverb for event-driven real-time, a dedicated server per fast-paced game; everything local in a Docker Compose stack until hosting is decided (candidate Vietnix VPS). Contract, Web production rules, `web-engineer` role, OQ-036/037 and the dependency registry (Docker Desktop) updated; QA may run `docker compose run --rm test`.
- Game platform contract version 1 (ADR-020): the Board-approved GAM-16 design (adapter, mount, embedding, manifest, host behaviour, identity, names, server-side validation, weekly boards, data, credentials) recorded in `knowledge/company/shared/game-platform-contract.md`, replacing the placeholder. The backend part of D4 is decided in ADR-021.

### Added
- `scripts/setup/sync-instructions.py`: pushes role texts from Git into a live Paperclip company (OQ-040). Used on 2026-11-05 after the M1 restructure; `Game Director` renamed `Director` in Soucean; old company `GAM` archived after its open work moved to SOU-1..SOU-10.

### Changed
- **Restructure into `knowledge/` and departments (ADR-019, migration map step M1).** Moved with `scripts/maintenance/move-files.py` (mapping in `scripts/maintenance/m1-moves.json`, links rewritten):
  - `company/` → `knowledge/company/` (`RULES.md` → `policies/rules.md`); `workflows/` → `knowledge/company/workflows/`;
  - shared roles → `knowledge/company/agents/`; game roles → `knowledge/departments/game/agents/`; `web-engineer` → `knowledge/departments/web/agents/`;
  - `projects/` → `knowledge/projects/` (`project-registry.yaml` → `registry.yaml`);
  - `task-contract.md` → `knowledge/company/standards/`, `provider-allocation.md` → `knowledge/company/policies/`, `game-platform-contract.md` → `knowledge/company/shared/`;
  - `docs/glossary.md` → `docs/vision/terminology.md`; `open-questions.md` and `implementation-roadmap.md` → `docs/roadmap/`; `studio-bootstrap.md` → `company-bootstrap.md`.
- `game-director` is renamed **`director`**, the company-wide director and Paperclip root for every department.
- Split: `COMPANY.md` (company mission; game values to the Game charter), `ORGANIZATION.md` (scopes, live providers), rules R1.4–R1.6 and R7.1, `project-initialization.md` (company workflow plus the game concept workflow), `company-design.md`, `security-architecture.md` §10 (principle stays; platform rules to the Web department).
- Project registry entries have `department` and `contributingDepartments`; `config/paperclip/agents.json` has `department` per agent; the package builder reads the new tree and rejects duplicate slugs.

### Added
- Department charters (`knowledge/departments/game/`, `knowledge/departments/web/`), `game-rules.md`, `new-game-concept.md`, `production-environments.md`, knowledge indexes and project entrypoints; ADR-019.
- Task contract, WIP limit, blocker protocol and liveness rules (`docs/design/task-contract.md`, ADR-017 proposed), the daily triage workflow (`workflows/daily-triage.md`), and a `## Task hygiene` section in every role file.
- Provider allocation rule for any number of AI providers (`docs/design/provider-allocation.md`, `config/providers.example.yaml`, ADR-015 proposed) and `allocation` metadata in role files.
- Studio bootstrap procedure for importing pre-configured agents (`docs/operations/studio-bootstrap.md`, ADR-016 proposed); open questions OQ-040, OQ-041; gaps G-11, G-12.
- `scripts/setup/build-package.py`, `scripts/setup/post-import.py` and `config/paperclip/agents.json`: build a clean Paperclip package with full agent configuration and finish an import. Used on 2026-11-05 to create the company **Soucean** (`SOU`); the old company `GAM` is paused as an archive.
- ADR-018 (accepted): the repository is renamed `datpham02/company-os`.
- Paperclip skill: read-only `triage` command; `release` now checks write set, review/approval stages, open blockers and WIP (`--force` to override).
- `runtime/tools/review-wake-watchdog.ts`: first Stage 2 gap filler. It wakes reviewer agents that Paperclip leaves idle after an in-run hand-off (OQ-035).
- `docs/architecture/stage1-gap-analysis.md`.
- `.claude/skills/paperclip`: Claude Code skill and stdlib Python CLI (`pc.py`) for running Paperclip from chat as the Board Operator.
- `runtime/tools/start-studio.cmd`: one-click start of Paperclip, the review watchdog and the UI; skips anything already running.

### Changed
- `agents/qa` declares `slug: qa-engineer` so imports match the live Paperclip agent instead of creating a second one.
- Parallel-task, delegation and failure workflows check overlap against every unmerged Task, use blocker relations, and handle cancelled blockers and stalled reviews.
- Paperclip now runs as a global, pinned install (`paperclipai run` from `~/game-studio-workspace`) instead of `npx`, so `npm_*` variables no longer leak into agents (OQ-034).

### Changed
- ADR-013: the studio machine is now the Board Operator's Windows 11 computer. ADR-013 supersedes ADR-003 (native Ubuntu). `docs/operations/ubuntu-setup.md` is replaced by `windows-setup.md`, and Linux-specific guidance (systemd, Unix permissions, paths) is rewritten for Windows.
- Dependency registry: versions re-verified on the Windows machine (Claude Code 2.1.316, GitHub CLI 2.97.0). Codex and OpenSpec are not installed there.
- Cursor CLI added as a third execution provider (registry `cursor-cli`, `docs/integrations/cursor-integration.md`, OQ-033).
- Open questions: added OQ-031 (Paperclip on native Windows) and OQ-032 (Codex sandbox and `process` shell on Windows); OQ-028 resolved.

## [0.1.0] — 2026-11-03

### Added
- Documentation system v1.0: architecture, design, ADRs (ADR-001 to ADR-012), workflows, integrations, operations, and guides.
- Studio definition: `company/` and seven agent role definitions in `agents/`.
- Project registry (empty) and project configuration schema (`PROPOSED`) in `projects/`.
- External dependency registry with candidate dependencies in `dependencies/registry.yaml`.
- `AGENTS.md` and `CLAUDE.md` so the repository works with both Codex and Claude Code.

### Notes
- No Runtime code exists. All Runtime behavior is `PLANNED`.
- Paperclip capabilities were verified against Paperclip's repository documentation at commit `7b8aa60` (2026-11-03). Unverified items are tracked in `docs/architecture/open-questions.md`.
