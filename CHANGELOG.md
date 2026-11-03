# Changelog

All notable changes to the Game Studio framework are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow Semantic Versioning; the current version is in [VERSION](VERSION).

## [Unreleased]

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
