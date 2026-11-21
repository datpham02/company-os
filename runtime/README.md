# Agent Runtime

**Status: `PLANNED`, except one gap filler and a start script.** The only implemented code is [`tools/review-wake-watchdog.ts`](tools/review-wake-watchdog.ts) with its rules [`tools/stuck-rules.ts`](tools/stuck-rules.ts) (review wakes, OQ-035, see [../docs/architecture/stage1-gap-analysis.md](../docs/architecture/stage1-gap-analysis.md); stuck-issue alerts, OQ-048) and [`tools/start-studio.cmd`](tools/start-studio.cmd), which starts Paperclip, the watchdog and the UI. Do not describe any other Runtime command as working.

The Agent Runtime executes Tasks locally on the studio's Windows machine ([ADR-013](../docs/decisions/ADR-013-native-windows-studio-host.md)). Its scope is set by [ADR-011](../docs/decisions/ADR-011-execution-path-selection.md). Stage 1 uses Paperclip's built-in adapters and needs no Runtime code. In Stage 2 the Runtime is built only for verified gaps, and Paperclip's `process` adapter invokes it.

- Design: [../docs/architecture/runtime-architecture.md](../docs/architecture/runtime-architecture.md)
- Component contracts: [../docs/architecture/system-components.md](../docs/architecture/system-components.md) §8–13
- Before writing code: [../docs/roadmap/phases.md](../docs/roadmap/phases.md) Phase 0 and Phase 2

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
