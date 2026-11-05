# Web Department

- **Status:** `APPROVED`. Founded by [ADR-014](../../../docs/decisions/ADR-014-platform-project-type.md) (platform project type, `web-engineer`, production rules).
- **Head:** `director` (company-wide, [ADR-019](../../../docs/decisions/ADR-019-knowledge-tree-and-departments.md)). No separate department lead yet.
- **Audience:** agents and humans working on platform projects. Company-wide rules in [../../company/README.md](../../company/README.md) apply first.

## Mission
Build and run the platform that lists and hosts the company's games: the website, its backend and its non-production environments.

## Scope
- In scope: projects with `type: platform`; frontend, the Laravel + MySQL backend (API, migrations, authorization, Reverb real-time, [ADR-021](../../../docs/decisions/ADR-021-laravel-mysql-backend.md)), deploy configuration for non-production environments. Everything runs locally until the Board decides hosting.
- Out of scope: game code (games are separate projects); production deploys, production secrets and external accounts (Board only, below); payment code until a payments ADR and legal review exist.

## Roles

| Role | Scope | Definition |
|---|---|---|
| `web-engineer` | Web only | [agents/web-engineer](agents/web-engineer/AGENTS.md) |
| `director` | Company (head of this department) | [director](../../company/agents/director/AGENTS.md) |
| `producer`, `project-manager`, `ui-designer`, `qa` | Company (shared) | [company agents](../../company/agents/) |

`devops-engineer` is a planned role, added when the company runs more than one platform or self-hosted infrastructure (ADR-014 §4).

## Platform projects
- Each platform project has its own repository, Paperclip project and registry entry with `type: platform` and `department: web`.
- From its seed commit the repository contains `AGENTS.md` (stack, commands, environments, security-sensitive paths), `docs/requirements.md`, `docs/architecture.md` and `docs/game-platform-contract.md` (a pointer to the company contract, never a redefinition) (ADR-014 §3).
- A project may be `planned` before its repository exists; agents then write plans only, never repositories or accounts (ADR-014 §2).

## Production and security
The full rules are in [production-environments.md](domain/production-environments.md). In short:
- Agents never receive production credentials; they work against dev or test projects only.
- Production deploys, migrations, secrets, DNS and ad-network settings are Board actions.
- Authentication, authorization policies, server-side scoring or rewards, secrets configuration, security headers and payment code are security-sensitive: `qa` review **and** a human Board review.

## Board-only actions
Creating the platform repository, the Paperclip project and agent instances, and the hosting, domain, ad-network and payment accounts (ADR-014 §6). Agents may propose them and write step-by-step instructions.

## Design tools
Web-design tools and skills are listed in the dependency registry with category `web-design`. Use only entries with status `approved` or `integrated`, after the supply-chain review ([security-architecture.md §11](../../../docs/architecture/security-architecture.md#11-supply-chain-safety)).

## Contract with the Game department
[game-platform-contract.md](../../company/shared/game-platform-contract.md): ads only on platform pages; no ad hook inside a game; rewards and purchases only granted by the platform server.

## Projects
| Project | Status | Registry |
|---|---|---|
| Soucean Game | see registry | [knowledge/projects/soucean-game](../../projects/soucean-game/README.md) |

## Open questions
OQ-036 (superseded by ADR-021), OQ-037 (hosting; candidate Vietnix VPS), OQ-038 (ads and consent), OQ-039 (Vietnamese legal requirements) in [open-questions.md](../../../docs/roadmap/open-questions.md).

## Related
[../README.md](../README.md) · [../../company/ORGANIZATION.md](../../company/ORGANIZATION.md)
