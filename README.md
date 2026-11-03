# Game Studio

Game Studio is a reusable, AI-powered framework for operating a **multi-project game development studio**. It defines the studio's organization, agent roles, rules, workflows, project registry, and external dependencies. It also plans a local Agent Runtime that integrates with **Paperclip**, the independent orchestration platform.

> **Status:** documentation-only, framework version `0.1.0` ([VERSION](VERSION)). Architecture documentation v1.0. The Runtime is `PLANNED`, apart from one gap filler (`runtime/tools/review-wake-watchdog.ts`).

## Responsibility split

| System | Owns | Lives in |
|---|---|---|
| **Paperclip** | Company, agents, projects, tasks (issues), assignment, approvals, heartbeats, budgets, audit log | Independent application ([paperclipai/paperclip](https://github.com/paperclipai/paperclip)) |
| **Game Studio** | Studio organization, agent role definitions, rules, workflows, project registry, dependency registry, integration contracts | This repository (`datpham02/game-studio`) |
| **Agent Runtime** | Local task execution on the studio's Windows machine: project resolution, workspaces, Git branches/worktrees, CLI launch, result reporting | `runtime/` in this repository (`PLANNED`) |
| **AI Execution Providers** | Doing the actual coding work | Claude Code CLI, Codex CLI |
| **External Tools** | Specialized capabilities (specs, browser testing, API testing, game-dev skills) | Their own projects, registered in [dependencies/](dependencies/) |
| **GitHub** | Hosting the framework repository and each game repository | e.g. `datpham02/node-arena` |

Game source code never lives in this repository.

## Repository layout

```text
game-studio/
├── AGENTS.md / CLAUDE.md   Instructions for AI coding agents working on this repo
├── company/                Studio identity, organization, rules, operating model
├── agents/                 Agent role definitions (one directory per role)
├── workflows/              Operational workflows (canonical)
├── projects/               Project registry and project-config schema
├── dependencies/           External dependency registry
├── runtime/                Agent Runtime (PLANNED; README only)
└── docs/                   Architecture, design, ADRs, integrations, operations, guides
```

Directories in the target architecture that would be empty today (`integrations/`, `templates/`, `schemas/`, `scripts/`, `runtime/src/`) are intentionally **not** created yet. See [docs/architecture/repository-architecture.md](docs/architecture/repository-architecture.md).

## Where to start

- Humans: [docs/README.md](docs/README.md), then [docs/architecture/overview.md](docs/architecture/overview.md).
- AI agents: [AGENTS.md](AGENTS.md), then [docs/guides/ai-agent-onboarding.md](docs/guides/ai-agent-onboarding.md).
- Implementers: [docs/guides/implementation-roadmap.md](docs/guides/implementation-roadmap.md).

## License

Not yet chosen. See [docs/architecture/open-questions.md](docs/architecture/open-questions.md) (OQ-019).
