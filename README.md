# Company OS

Company OS is the framework of **Soucean**, a company run by one human Board Operator and a team of AI agents, organized in departments (today **Game** and **Web**). It defines the Company Core, each department's roles and knowledge, the project registry, the dependency registry, and the setup that builds the company in **Paperclip**, the independent control plane.

> **Status:** framework version in [VERSION](VERSION). Mostly documentation; the Paperclip skill, the setup scripts and one Runtime gap filler are implemented. The Agent Runtime is `PLANNED`.

## Responsibility split

| System | Owns | Lives in |
|---|---|---|
| **Paperclip** | Company, agents, projects, tasks (issues), assignment, approvals, heartbeats, budgets, audit log | Independent application ([paperclipai/paperclip](https://github.com/paperclipai/paperclip)) |
| **Company OS** | Company Core, departments, roles, rules, workflows, project and dependency registries, integration contracts, setup | This repository (`datpham02/company-os`) |
| **Agent Runtime** | Local task execution: workspaces, branches, CLI launch, reporting | `runtime/` (`PLANNED`) |
| **AI Execution Providers** | The actual work | Claude Code CLI, Cursor CLI ([provider allocation](knowledge/company/policies/provider-allocation.md)) |
| **External Tools** | Specialized capabilities | Their own projects, registered in [dependencies/](dependencies/) |
| **GitHub** | This repository and each project repository | e.g. `datpham02/lamplight-vigil`, `datpham02/soucean-game` |

Project source code never lives in this repository.

## Repository layout

```text
company-os/
├── AGENTS.md / CLAUDE.md   Instructions for AI coding agents working on this repository
├── knowledge/              What the company knows and how it operates
│   ├── company/            Company Core: definition, organization, policies, standards, shared roles, workflows, contracts
│   ├── departments/        game/, web/: charters, department roles, workflows, domain rules
│   └── projects/           Project registry and one entrypoint per project
├── dependencies/           External dependency registry
├── config/                 Portable Paperclip agent configuration, provider example
├── scripts/                setup/ (build the Paperclip package, post-import), maintenance/ (move files with link rewrite)
├── runtime/                Runtime gap filler and start script; the Runtime itself is PLANNED
└── docs/                   Engineering documentation: vision, architecture, design, decisions, integrations, operations, guides, roadmap
```

## Where to start

- Humans: [docs/README.md](docs/README.md), then [knowledge/README.md](knowledge/README.md).
- AI agents: [AGENTS.md](AGENTS.md), then [docs/guides/ai-agent-onboarding.md](docs/guides/ai-agent-onboarding.md).
- Setting up a machine: [docs/operations/company-bootstrap.md](docs/operations/company-bootstrap.md).

## License

Not yet chosen. See [open-questions.md](docs/roadmap/open-questions.md) (OQ-019).
