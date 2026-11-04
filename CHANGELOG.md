# Changelog

All notable changes to the Game Studio framework are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow Semantic Versioning; the current version is in [VERSION](VERSION).

## [Unreleased]

### Added
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
