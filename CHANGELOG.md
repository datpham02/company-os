# Changelog

All notable changes to the Game Studio framework are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow Semantic Versioning; the current version is in [VERSION](VERSION).

## [Unreleased]

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
