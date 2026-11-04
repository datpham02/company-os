# ADR-014: Platform Project Type, Web Engineer Role and Production Security Rules

- **Status:** Proposed
- **Date:** 2026-11-04
- **Deciders:** Board Operator
- **Related:** ADR-005, ADR-009, ADR-010, ADR-012, [project-system.md](../design/project-system.md), [security-architecture.md §10](../architecture/security-architecture.md#10-production-environments-platform-projects), [game-platform-contract.md](../design/game-platform-contract.md), Paperclip issue GAM-16, OQ-036 to OQ-039

## Context
The Board Operator plans a **multi-game website**. It lists the studio's games, lets players play them in the browser, runs shared online features (one player identity, weekly leaderboards) and earns money from **ads placed on the website page, never inside a game**. Lamplight Vigil is the first game on it.

Board decisions of 2026-11-04 (recorded in GAM-16):
- online weekly leaderboard: best score per week, weekly reset, weekly crawler variation;
- moderate anti-cheat only;
- anonymous identity with optional real-account linking;
- minimal data;
- ads only on the website, none inside Lamplight Vigil;
- later games may add rewarded ads or in-game purchases, so the contract between a game and the website has optional capabilities, and their rewards are granted only by the server.

The framework so far knows only one kind of project, a game. A website differs in four ways:
1. It is not a game. It hosts games and owns the shared services.
2. It has a backend with **production data and production secrets**, such as a database of player records, hosting and ad-network accounts. No game repository has these today.
3. It needs web and backend skills that no current role covers.
4. Games and the website must agree on a **game platform contract**. GAM-16 (Game Director, backlog, starts after GAM-15) designs it. This ADR does not.

Facts about external services in this ADR (Supabase anonymous sign-in and account linking, Cloudflare Pages, ad-network requirements) are `UNVERIFIED` and tracked in OQ-036 to OQ-039.

## Decision

### 1. Project type
- Every registry entry MAY carry `type: game | platform`. A missing `type` means `game`, so existing entries do not change.
- A **platform** project is a product that hosts or serves games, for example the website and its backend. It has its own repository, its own Paperclip project and its own registry entry, like a game ([ADR-005](ADR-005-independent-game-repositories.md)).
- Games MUST NOT depend on a platform's source code. A game depends only on the published game platform contract. The website depends only on each game's manifest and build output.
- One platform project may host many games. Which games it hosts is website data (each game's manifest), not a registry field.

### 2. `planned` status
- The project lifecycle gains a status `planned`: the Board has decided the project will exist, but no repository, Paperclip project or external account exists yet.
- A `planned` entry MAY omit `repository`. All other statuses still require it.
- While a project is `planned`, agents MAY write plan documents in this framework repository only. They MUST NOT create repositories, Paperclip projects or external accounts.
- `planned → initializing` happens when the Board creates the repository and the Paperclip project, following [project-initialization.md](../../workflows/project-initialization.md).

### 3. Platform documentation set
A platform repository MUST contain, from its seed commit:

| Document | Content |
|---|---|
| `AGENTS.md` | Stack, build and test commands, environments, which paths are security-sensitive (§5) |
| `docs/requirements.md` | Pages, features, non-goals, privacy and data rules, ad rules |
| `docs/architecture.md` | Frontend, backend, data model, RLS model, environments, deploy flow |
| `docs/game-platform-contract.md` | A pointer to the framework contract version this platform implements, plus any platform-side notes. It MUST NOT redefine the contract. |

- The **game platform contract** lives in this framework repository at [docs/design/game-platform-contract.md](../design/game-platform-contract.md), because several games and platforms share it. Until GAM-16 delivers, that file is a placeholder with status `PLANNED`. A new or superseding ADR adopts GAM-16's design. Nobody designs the contract in parallel to GAM-16.
- The contract MUST keep the Board's rules: ads only on platform pages; no ad SDK or ad hook inside a game that declares no ad capability; rewards and purchases are optional capabilities that only the platform server grants.

### 4. New role: `web-engineer`
- A new role **Web Engineer** ([agents/web-engineer/AGENTS.md](../../agents/web-engineer/AGENTS.md)) builds platform projects: frontend, backend schema, migrations, data-access rules (RLS), server functions and deploy configuration for non-production environments. It reports to `project-manager`, has permission profile `workspace-write`, and writes code.
- No DevOps role is added now. A single website on managed hosting does not need one. Deploy configuration is part of `web-engineer` work, and production deploys stay with the Board (§5). `devops-engineer` joins the planned-roles list in [ORGANIZATION.md](../../company/ORGANIZATION.md). Add it when the studio runs more than one platform, or self-hosted infrastructure.
- `qa` reviews platform work as it reviews games, including web end-to-end tests with Playwright MCP.

### 5. Production security rules
Recorded in full in [security-architecture.md §10](../architecture/security-architecture.md#10-production-environments-platform-projects). In short:
- **Production keys are never bound to agents.** This covers database admin keys, service-role keys, platform access tokens, hosting tokens, ad-network accounts, DNS and payment keys. Agents get dev or test projects only.
- **Production deploys are done by the Board.** This covers code promotion, database migrations and secret changes in production.
- **Auth, RLS and payment code need human review in addition to QA.** A `qa` approval alone is not enough to merge them.

### 6. Board-only actions
Creating the platform repository, the Paperclip project and the Paperclip agent instances, and the Supabase, hosting, domain, ad-network and payment accounts, is a Board action. Agents may only propose these and write step-by-step instructions.

## Alternatives considered
| Alternative | Why not chosen |
|---|---|
| Build the website inside the Lamplight Vigil repository | Breaks the one-game-per-repository rule (ADR-005). The second game would have to depend on the first game's repository. |
| Treat the website as a `game` project | Hides the facts that matter: production data, secrets and ads. The role and security rules would not apply cleanly. |
| Put the website in this framework repository | Rule 1 of [AGENTS.md](../../AGENTS.md): no product code here. |
| Let `gameplay-programmer` build the website | Wrong skills and wrong focus. Web security and RLS need a role that owns them. |
| Add `devops-engineer` now | No workload yet. Managed hosting plus Board-run production deploys covers one site. |
| Design the contract in this ADR | GAM-16 already owns it and has the game-side context. Two designs would conflict. |

## Consequences
- The schema and the project-system contract change: they gain `type` and `planned`, and `repository` becomes optional while `planned`.
- Security architecture gains production environments, which game repositories never had.
- Agent onboarding must not bind any production secret in Paperclip. The Board keeps them outside Paperclip.
- The human review rule adds Board effort on security-sensitive PRs. It is meant to be rare and focused on a few paths.
- Follow-up work:
  - GAM-16 fills the contract.
  - The Board creates the accounts listed in the website plan.
  - The website project goes through `planned → initializing → active`.
  - Payments get their own ADR and legal review before any code exists: the Vietnamese online-game licence (Decree 147/2024/ND-CP), a payment provider, refunds and tax.

## Reconsider when
- The studio runs a second platform, or self-hosted servers. Then reconsider `devops-engineer`.
- Paperclip gains per-environment secret scoping that would make production bindings safe.
- Payments or rewarded ads are actually built. They need their own ADR.
- GAM-16's contract makes the embedding model incompatible with §1, for example if games must share code with the platform.
