# Agent Runtime

**Status: `PLANNED`. No code exists in this directory.** Do not run, document, or reference any Runtime command as working.

The Agent Runtime executes Tasks locally on the studio's Ubuntu machine ([ADR-003](../docs/decisions/ADR-003-native-ubuntu-agent-runtime.md)). Its scope depends on the proposed [ADR-011](../docs/decisions/ADR-011-execution-path-selection.md). Stage 1 uses Paperclip's built-in adapters and needs no Runtime code. In Stage 2 the Runtime is built only for verified gaps, and Paperclip's `process` adapter invokes it.

- Design: [../docs/architecture/runtime-architecture.md](../docs/architecture/runtime-architecture.md)
- Component contracts: [../docs/architecture/system-components.md](../docs/architecture/system-components.md) §8–13
- Before writing code: [../docs/guides/implementation-roadmap.md](../docs/guides/implementation-roadmap.md) Phase 0 and Phase 2

Planned layout (directories are created with the first code, not before):

```text
runtime/
├── src/
│   ├── dispatcher/   Run request validation, project resolution, limits
│   ├── launcher/     Process supervision + providers/ (Provider Adapters)
│   ├── workspace/    Primary checkouts, worktrees, locks, cleanup
│   ├── git/          Safe Git operations, branch naming, PRs
│   └── reporter/     Paperclip comments/status, outbox
├── config/           runtime.example.yaml only (real config: ~/.config/game-studio/)
└── tests/
```
