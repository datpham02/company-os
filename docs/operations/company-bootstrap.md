# Studio Bootstrap: Import Pre-configured Agents

- **Status:** procedure `PROPOSED` ([ADR-016](../decisions/ADR-016-versioned-paperclip-package.md)). `scripts/setup/build-package.py` and `scripts/setup/post-import.py` are `IMPLEMENTED` and were used on 2026-11-05 to create the company **Soucean** (`SOU`); `sync-agents` is `PLANNED`.
- **Goal:** a fresh Paperclip gets the company, every agent with its reporting line, provider, permission profile, allowlist, budget and WIP limit, and the projects, from one import of versioned files. Only secrets and machine-specific values are entered locally. Nobody creates agents in the UI.

## 1. Verified facts (Paperclip 2026.1023.0, Windows 11)

| Fact | Source |
|---|---|
| `paperclipai company import <dir>` reads `knowledge/company/COMPANY.md` and `knowledge/company/agents/<slug>/AGENTS.md`; `reportsTo` builds the tree | OQ-007, 2026-11-03 |
| Agent slug = frontmatter `slug`, else the folder name. `knowledge/company/agents/qa/` therefore declares `slug: qa-engineer` to match the live agent's URL key; without it a re-import creates a second QA agent | Installed code `company-portability.js`; dry run 2026-11-04 |
| Importing from the working repository also picks up gitignored copies under `.claude/worktrees/*/agents/` and the root `AGENTS.md`. **Build the package in a clean directory** | Dry run 2026-11-04 (18 agents found instead of 8) |
| From a clean directory containing only `knowledge/company/` and `knowledge/company/agents/`, a dry run against the live company matches all 8 agents by slug, no warnings | Dry run 2026-11-04 |
| Importing into an **existing** company uses the "safe" route, which refuses `--collision replace` (HTTP 403). Only `rename` and `skip` work there. Re-import cannot update existing agents | Dry run 2026-11-04; `routes/companies.js` |
| A vendor extension file `.paperclip.yaml` (`schema: "paperclip/v1"`) at the package root carries per agent `adapter.type`, `adapter.config`, `runtime` (incl. `heartbeat.maxConcurrentRuns`), `permissions`, `permissionGrants`, `budgetMonthlyCents`, `inputs.env` (secret names only); plus `projects`, `routines`, `sidebar` | Installed code; `company export` of the live company 2026-11-04 |
| Export drops system-dependent values (the Cursor CLI path) and writes `permissionGrants` scoped to agent UUIDs, which are not portable | Same export |
| Without `.paperclip.yaml`, imported agents get `claude_local`, empty config, budget 0, heartbeat off, `maxConcurrentRuns: 20` | OQ-007 |
| The agent API has instructions-bundle routes (`GET`/`PUT /api/agents/{id}/instructions-bundle/file`, history, diff) | Installed code; **not in the public docs we checked** (`UNVERIFIED`) |

## 2. Package layout

Git holds the sources; the setup script builds the package in a clean folder outside the repository:

```text
Git (this repository)                    Built package (%USERPROFILE%\game-studio-workspace\package\)
knowledge/company/COMPANY.md                     ──┐     company/COMPANY.md
knowledge/company/agents/<id>/AGENTS.md          ──┤
knowledge/departments/<dept>/agents/<id>/AGENTS.md ┼──►  agents/<slug>/AGENTS.md
config/paperclip/agents.json                     ──┤     .paperclip.yaml   (portable config + provider per agent)
                                                    ┘     projects/<slug>/PROJECT.md
```

[`config/paperclip/agents.json`](../../config/paperclip/agents.json) holds the portable per-agent values: permission profile allowlists and the reporting rule from [security-architecture.md §4](../architecture/security-architecture.md#4-agent-permissions-provider-level), budget, WIP limit, secret input names. The provider per agent comes from the allocation rule ([provider-allocation.md](../../knowledge/company/policies/provider-allocation.md)) applied to the local provider list.

Committed sources MUST NOT contain secrets, absolute paths, agent or company UUIDs, or UUID-scoped `permissionGrants`. The built package adds this machine's paths and is never committed. Paperclip's YAML parser does not read JSON, so the builder writes block YAML.

## 3. Fresh instance

1. **Preflight:** Node ≥ 24.11, Git, `gh`, every declared provider CLI installed and logged in, Paperclip pinned version answering on `http://127.0.0.1:3100`.
2. Turn on the instance setting `enableIsolatedWorkspaces` (G-3).
3. **Build** the package: `python -I scripts/setup/build-package.py --prefix <PREFIX>`. The prefix is the first three letters of the company name (Paperclip adds `A`s if it is taken); it goes into the push allowlists. Output: `~/game-studio-workspace/package/`. The built package contains this machine's paths, so it stays local.
4. **Preview, then import into a new company.** This also skips the onboarding wizard, whose model sign-in fails on Windows (OQ-031):

   ```bash
   cd ~/game-studio-workspace/package
   paperclipai company import . --target new --new-company-name <Name> --include company,agents,projects --dry-run
   paperclipai company import . --target new --new-company-name <Name> --include company,agents,projects --yes
   ```

5. **Post-import:** `python -I scripts/setup/post-import.py --company <Name>`. It points project workspaces at `~/game-studio-workspace/repos/<project>`, binds declared secrets to company secrets of the same name (the Board creates `GH_TOKEN` in Company > Secrets first; secrets do not move between companies), checks the prefix, and prints a table. `--resume` resumes paused agents (the import leaves `cursor` agents paused).
6. Paperclip **Test Environment** for every agent.
7. Smoke Task in a disposable project, then start the studio with `runtime/tools/start-studio.cmd`.

## 4. Existing instance (a role or allocation changed in Git)

Re-import cannot update existing agents (safe route, §1). Until a sync script exists:

1. The Board merges the change in Git.
2. New roles: import with `--target existing -C <company-id> --collision skip --include agents` from a clean package; existing agents are skipped, new ones created. Dry run first. Leave `projects` out: the safe route rejects project `executionWorkspacePolicy` (verified 2026-11-05).
3. Changed instructions, adapter config or limits of existing agents: the Board applies them in the Paperclip UI (agent → Configuration / Instructions), copying from Git, then runs Test Environment. Record the date in the agent's change note.
4. Planned: `sync-agents` script that diffs Git against `GET /api/agents/{id}` and applies changes through the agent API after the Board confirms the diff (`UNVERIFIED` which routes are supported; OQ-040).

Never edit an agent's instructions only in Paperclip: Git is the source of truth (ADR-012).

## 5. Who runs it
The Board Operator, or an agent with the Board's explicit approval for that run. Building the package is harmless; importing changes Paperclip (R3).

## Related documents
[installation.md](installation.md) · [../integrations/paperclip-integration.md](../integrations/paperclip-integration.md) · [../../knowledge/company/workflows/agent-onboarding.md](../../knowledge/company/workflows/agent-onboarding.md) · [../decisions/ADR-012-agent-definition-format.md](../decisions/ADR-012-agent-definition-format.md)
