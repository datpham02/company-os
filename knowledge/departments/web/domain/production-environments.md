# Production Environments (Web Department)

- **Status:** `APPROVED` ([ADR-014](../../../../docs/decisions/ADR-014-platform-project-type.md)). Moved here from `docs/architecture/security-architecture.md` §10 on 2026-11-05 ([ADR-019](../../../../docs/decisions/ADR-019-knowledge-tree-and-departments.md)); the company-wide principle stays there.
- **Applies to:** every project with `type: platform`. Game repositories have no production backend.

## 1. Environments

| Environment | Who uses it | Backend project | Credentials held by |
|---|---|---|---|
| Local / dev | Agents, Board | The Laravel application on the company machine with a local MySQL or SQLite database and fake data only (ADR-021) | Paperclip company secrets bound **only** to the agents of that platform project |
| Preview | Agents (read results), Board | Not set up while everything runs locally. When hosting exists: a separate staging database with fake data, on non-production URLs | Board only; no hosting token for agents |
| Production | Board only | Not created yet (hosting pending; candidate Vietnix VPS). A separate production database with real player data, reachable only by the production Laravel application | The Board Operator, in a password manager and in the hosting provider's secret store. **Never** in Paperclip, a repository or an agent environment |

## 2. Production keys are never bound to agents
- Agents MUST NOT receive any production credential. This covers the production Laravel `APP_KEY` and `.env`, database passwords, server SSH keys, hosting API tokens with production rights, DNS or registrar logins, ad-network accounts and payment-provider keys.
- These MUST NOT be stored as Paperclip company secrets, because a binding mistake would reach an agent. The Board keeps them outside Paperclip.
- The browser never receives a database credential. It receives only the backend base URL and, per player, a token issued by Laravel.
- Dev-project credentials MUST be different from production credentials, and MUST NOT give access to production data.
- An agent that finds a production credential MUST stop and report it. The Board then rotates the credential.

## 3. Production deploys are done by the Board
- Code reaches production only through a Board action. Either the Board merges to the Default Branch and the hosting provider auto-deploys it, or the Board promotes a build by hand.
- Database migrations reach production only when the Board applies them after the PR is merged. Agents MUST NOT run migration commands against production.
- Production secrets, environment variables, DNS, ad-network settings and domain changes are Board actions.
- Agents MAY prepare release notes and a deploy checklist for each release.

## 4. Human review for security-sensitive code
- A PR that touches any of the following is **security-sensitive**:
  - authentication and account linking;
  - authorization policies and gates, middleware, rate limiters, and migrations that create or change tables;
  - endpoints or jobs that accept scores or grant rewards or entitlements;
  - payment code;
  - secret or environment configuration;
  - Content-Security-Policy and other security headers.
- A security-sensitive PR needs **two approvals:** a `qa` review **and** a review by the Board Operator, a human. A `qa` approval alone MUST NOT lead to a merge.
- The platform repository SHOULD list these paths in `.github/CODEOWNERS` and its `AGENTS.md`. The authoring agent MUST mark the PR (`Security-sensitive: yes`).
- Payment code MUST NOT be written before a separate payments ADR and legal review exist. That review covers the Vietnamese online-game licence (Decree 147/2024/ND-CP), a payment provider, refunds and tax.

## 5. Player data
- Store the minimal data set defined by the platform's `docs/requirements.md` and the [game platform contract](../../../company/shared/game-platform-contract.md) §9. Every table with player data is accessed only through Laravel code that checks the caller.
- Agents MUST NOT read, export or copy production player data, including for debugging. Production incidents are handled by the Board.
- Ads and any non-essential cookies load only after consent. Consent and the privacy policy are platform features.

## Related
[../README.md](../README.md) · [security-architecture.md](../../../../docs/architecture/security-architecture.md) · [web-engineer](../agents/web-engineer/AGENTS.md)
