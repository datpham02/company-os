# Security Architecture

**Threat model (v1):** a single trusted Board Operator on a single Windows machine. AI agents are *semi-trusted*: they act in good faith but can misunderstand instructions, be prompt-injected through repository content, issues, web pages, or tool output, and run arbitrary commands through their Provider. There is no container isolation in v1 (ADR-013). Security therefore relies on **least-privilege credentials, Provider permission controls, Git branch protection, and approval gates**.

## 1. Assets

| Asset | Impact if compromised |
|---|---|
| GitHub credentials | Push malicious code, delete repos |
| Provider credentials (Claude, OpenAI) | Spend, data exfiltration |
| Paperclip board access and API keys | Reassign tasks, approve actions, change agents |
| Game source code (Default Branch) | Corrupted product |
| User home directory | SSH keys, VPN config, other projects (the audit found e.g. `~/.ssh`, `*.ovpn` in home) |
| Production credentials of platform projects (backend admin keys, hosting, DNS, ad network, payments) | Player data leak, defacement, ad-account ban, fraud ([§10](#10-production-environments-platform-projects)) |
| Production player data | Privacy breach (Decree 13/2023/ND-CP, GDPR) |

## 2. Credential handling

| Credential | Storage | Delivered to agents as | Rules |
|---|---|---|---|
| Claude Code auth | `~/.claude/` (subscription login) or `ANTHROPIC_API_KEY` | Provider reads its own store | MUST NOT be copied into repos or prompts. |
| Codex auth | `~/.codex/auth.json` (Codex reads credentials from `auth.json`; `VERIFIED`, Paperclip codex-local docs) | Provider reads its own store | Same. |
| GitHub token for agents | Paperclip company secret bound to the agent/project (`VERIFIED` mechanism: `GH_TOKEN`/`GITHUB_TOKEN` bindings), or local Runtime secret file mode `0600` | Environment variable `GH_TOKEN` | MUST be a **fine-grained token scoped to the specific Game Repositories**, permission *Contents: read/write* and *Pull requests: read/write* only. MUST NOT have admin, delete, or workflow-secrets scope (OQ-017). |
| Paperclip run JWT | Injected by Paperclip per heartbeat (`PAPERCLIP_API_KEY`) | Env | Short-lived, agent-scoped. Never logged. |
| Paperclip long-lived agent API keys | Paperclip (hashed at rest, `VERIFIED`) | Only if the Runtime needs one outside heartbeats | Avoid in v1. |

Rules:
- Secrets MUST be passed via environment variables or files with mode `0600`, never as command-line arguments (visible in `ps`).
- Logs and Run summaries MUST NOT contain secret values. The Runtime SHOULD redact values of known secret variables from captured output.
- `.env` files and credential files MUST be gitignored in every repository.

## 3. Repository access

- Each Agent Instance's GitHub token covers only the Game Repositories it is assigned to.
- Every Game Repository's Default Branch MUST have GitHub branch protection: require pull request, require 1 approving review, block force-push, block deletion. (GitHub feature; configured by the Board Operator.)
- Agents MUST NOT have access to the Framework Repository's write permissions unless a Task explicitly targets the framework.

## 4. Agent permissions (Provider level)

Permission profiles (`PROPOSED`) are assigned per Agent Instance:

| Profile | Intended roles | Claude Code | Codex |
|---|---|---|---|
| `read-only` | `game-director`, `producer`, `project-manager` (planning) | `--permission-mode plan` or `--restricted`, no edit tools | `--sandbox read-only` |
| `workspace-write` | `game-designer` (docs), `gameplay-programmer`, `ui-designer`, `qa` | `--permission-mode acceptEdits` plus `--allowedTools` allowlist for build/test/git commands and `--disallowedTools` for dangerous ones | `--sandbox workspace-write` |
| `bypass` | None by default | `--dangerously-skip-permissions` | `--dangerously-bypass-approvals-and-sandbox` |

Cursor CLI (third provider) mapping: [cursor-integration.md §5](../integrations/cursor-integration.md#5-permission-mapping-proposed-oq-033). Paperclip's `cursor` adapter adds `--yolo` unless `--trust` is in `extraArgs`.

All flags are `VERIFIED` present in the installed CLIs (Claude Code 2.1.273, Codex 0.166.0-alpha.5.1). How well each mode actually confines a headless run is `UNVERIFIED` (OQ-011).

**Stage 1 profile tested through Paperclip (`PROPOSED`, OQ-011, 2026-11-03).** Under the default ACP engine, `claude_local` approves every tool request, and the only alternative mode, `approve-reads`, also blocks the agent's reports to Paperclip. Use the Claude CLI engine instead:

```json
{
  "engine": "cli",
  "dangerouslySkipPermissions": false,
  "extraArgs": [
    "--permission-mode", "acceptEdits",
    "--allowedTools",
    "Bash(curl *)", "Bash(cat *)",
    "Bash(*paperclip-issue-update.sh*)", "Bash(*paperclip-upload-artifact.sh*)", "mcp__Paperclip_projects",
    "Bash(git status*)", "Bash(git diff*)", "Bash(git log*)", "Bash(git show*)", "Bash(git add*)", "Bash(git commit*)",
    "--disallowedTools", "Bash(git push*)",
    "--append-system-prompt", "<reporting rule, below>"
  ]
}
```

This is the `workspace-write` profile. Add each project's build and test commands to `--allowedTools`. For `read-only` roles, drop `--permission-mode acceptEdits` and the `git add` / `git commit` entries.

The **reporting rule** is required. Without it, an agent sometimes wraps Paperclip's helper in its own script or uses shell variables, both of which the permission layer refuses. It then cannot report, and the Task ends `blocked` (OQ-011). The rule passed through `--append-system-prompt`:

> Paperclip reporting rule for this environment: to post comments or change issue status, call the Paperclip skill's paperclip-issue-update.sh as one standalone Bash command, for example: `bash "<absolute path to paperclip-issue-update.sh>" --issue-id <literal issue id> --status done <<'MD' ... MD`. Never wrap it in a script of your own, never use shell variables such as `$PAPERCLIP_TASK_ID` or `$PAPERCLIP_API_KEY` in a command, and never chain it with other commands using `&&` or `;`. Use the literal issue id from your task. The permission layer refuses anything else.

**Task-branch push (added for the first Game Repository, 2026-11-03).** `workflows/development-cycle.md` needs agents to push their Task Branch and open a PR. The `workspace-write` profile therefore:
- replaces the blanket `Bash(git push*)` deny with allow rules for the task-branch pattern: `Bash(git push -u origin GAM-*)`, `Bash(git push origin GAM-*)`. Paperclip names task branches `<ISSUE-KEY>-<slug>`, and the studio company's issue prefix is `GAM`. It also allows `Bash(gh pr create*)`, `Bash(gh pr view*)` and `Bash(gh pr list*)`;
- keeps these denied: `Bash(git push origin main*)`, `Bash(git push -u origin main*)`, `Bash(git push --force*)`, `Bash(git push -f*)`, `Bash(git push *--force*)` and `Bash(gh pr merge*)`. Merging stays with the Board (ADR-009);
- adds npm build/test commands: `Bash(npm ci*)`, `Bash(npm install*)`, `Bash(npm run *)`, `Bash(npm test*)`, `Bash(npx tsc*)`;
- appends a git rule to the reporting rule: push only the task branch by its literal name, as one standalone command, and open the PR with one standalone `gh pr create --base main --head <branch>` command.

**Syncing a task branch with `main` (added 2026-11-04, Board decision during GAM-11).** Parallel tasks conflict once one of them merges, and a rebase would need a force-push, which stays denied. The `workspace-write` profile therefore also allows `Bash(git fetch origin*)`, `Bash(git merge origin/main*)`, `Bash(git merge --no-edit origin/main*)`, `Bash(git merge --continue*)` and `Bash(git merge --abort*)`. The git rule adds: to bring the task branch up to date with main, run `git fetch origin`, then `git merge origin/main` as separate standalone commands (never rebase), resolve conflicts, commit the merge and push normally. A local merge cannot reach `main` on GitHub, because pushes to `main` stay denied here and blocked by branch protection.

The `read-only` profile still denies every push. The hard guard is GitHub branch protection on `main`: PR required, 1 approval, no force-push, no deletion.

Each Game Repository's local clone uses `credential.helper = !gh auth git-credential`, so a `GH_TOKEN` in the agent's environment is the credential for both `git push` and `gh`. **Until the fine-grained `GH_TOKEN` is bound, a push would use the host's own `gh` login, which can reach every repository of the account** ([security-operations.md](../operations/security-operations.md) §2).

Applied on 2026-11-03 to the six `claude_local` agents of the studio company (`read-only`: `game-director`, `producer`, `project-manager`; `workspace-write`: `game-designer`, `gameplay-programmer`, `ui-designer`).

Paperclip's `filesystemScope` / `networkScope` confinement needs Bubblewrap and is not available on Windows.

**Important conflict with Paperclip defaults:** Paperclip's `claude_local` adapter defaults `dangerouslySkipPermissions` to `true` ("required for headless runs where interactive approval is impossible", `VERIFIED`). Using the `bypass` profile by default contradicts this document. Until OQ-011 is resolved, the `bypass` profile MAY be used only for Agent Instances whose GitHub token cannot push to protected branches and whose working directory is a Task Workspace, and the Board Operator MUST approve its use per Agent Instance. Recorded as C-002.

## 5. Filesystem permissions

- Agents run as the Board Operator's Windows user account (ADR-013). They can technically read anything that user can read.
- Mitigations: run in a Task Workspace cwd; use Provider directory restrictions (Claude Code confines file tools to working directories plus `--add-dir`; Codex `workspace-write` sandbox limits writes to the workspace); never `--add-dir` the home directory.
- `PROPOSED` (OQ-027): a dedicated local Windows user `studio-agent` with NTFS access only to the Workspace Root, if stronger isolation is needed before containers.

## 6. Command execution restrictions

Agents MUST NOT run (enforced by Provider deny lists where possible, and by rules in [company/RULES.md](../../company/RULES.md)):
- `git push --force`, `git push origin main` (or Default Branch), `git reset --hard origin/*` on shared branches, `git branch -D` on non-task branches;
- `rm -rf` outside the Task Workspace; any command on `~/.ssh`, `~/.claude`, `~/.codex`, `~/.config/game-studio`;
- `sudo`, package installation system-wide, `curl | sh` style installers;
- commands that print environment variables or secret files into logs.

## 7. Secret isolation

- Provider credentials, GitHub tokens, and Paperclip tokens are separate and scoped.
- Game Repositories MUST NOT contain secrets; game runtime secrets (if any) use the game's own secret mechanism.
- Prompt-injection risk: content from issues, web pages, or repository files can instruct an agent to exfiltrate secrets. Least privilege and no-secrets-in-env-unless-needed are the primary defences.

## 8. Approval boundaries

| Action | Approval required | Approver | Recorded in |
|---|---|---|---|
| Merge to Default Branch | Yes (ADR-009) | Board Operator | Paperclip + GitHub PR |
| Release a game version | Yes | Board Operator | Paperclip approval + Git tag |
| Create a Game Repository | Yes | Board Operator | Paperclip approval |
| Install/upgrade a Dependency | Yes | Board Operator | Paperclip approval + registry change PR |
| Hire (create) an Agent Instance | Yes | Board Operator | Paperclip `hire_agent` approval (`VERIFIED` type) |
| Use `bypass` permission profile | Yes | Board Operator | Agent Instance config change log |
| Budget override | Yes | Board Operator | Paperclip `budget_override_required` (`VERIFIED` type) |
| Create an external account or project for a platform (backend, hosting, domain, ad network, payments) | Yes (ADR-014) | Board Operator | Paperclip issue comment |
| Production deploy, production migration or production secret change | Yes (ADR-014) | Board Operator, who also performs it | Platform repository release notes |
| Merge a security-sensitive platform PR (auth, RLS, reward or payment code) | Yes: human review **plus** `qa` (ADR-014) | Board Operator | GitHub PR review + Paperclip |

## 9. Destructive operation safeguards

1. Prohibited for all automated actors (no approval can enable them in v1): force-push, deleting repositories, deleting the Default Branch, rewriting published history, deleting tags.
2. Worktree cleanup never discards uncommitted changes.
3. Branch protection is the technical backstop if an agent ignores rules.
4. Every Run's commit range is recorded so changes can be reverted.

## 10. Production environments (platform projects)

Status: `APPROVED` ([ADR-014](../decisions/ADR-014-platform-project-type.md)). It applies to every project with `type: platform`. Game repositories have no production backend, so it does not apply to them.

### 10.1 Environments

| Environment | Who uses it | Backend project | Credentials held by |
|---|---|---|---|
| Local / dev | Agents, Board | A separate **dev** backend project (for example a Supabase free-tier project named `<platform>-dev`) with fake data only | Paperclip company secrets bound **only** to the agents of that platform project |
| Preview | Agents (read results), Board | The dev project. Preview deploys of Task Branches go to non-production URLs | Hosting's own build integration; no hosting token for agents |
| Production | Board only | A separate **prod** backend project with real player data | The Board Operator, in a password manager and in the hosting provider's secret store. **Never** in Paperclip, a repository or an agent environment |

### 10.2 Production keys are never bound to agents
- Agents MUST NOT receive any production credential. This covers backend service-role or admin keys, database passwords, backend management access tokens, hosting API tokens with production rights, DNS or registrar logins, ad-network accounts and payment-provider keys.
- These MUST NOT be stored as Paperclip company secrets, because a binding mistake would reach an agent. The Board keeps them outside Paperclip.
- A public client key that ships in the production web build by design (for example Supabase's anon or publishable key) MAY appear in production build configuration that the Board manages. It is protected by RLS, not by secrecy. Agents still use the dev project's key during development.
- Dev-project credentials MUST be different from production credentials, and MUST NOT give access to production data.
- An agent that finds a production credential MUST stop and report it. The Board then rotates the credential.

### 10.3 Production deploys are done by the Board
- Code reaches production only through a Board action. Either the Board merges to the Default Branch and the hosting provider auto-deploys it, or the Board promotes a build by hand.
- Database migrations reach production only when the Board applies them after the PR is merged. Agents MUST NOT run migration commands against production.
- Production secrets, environment variables, DNS, ad-network settings and domain changes are Board actions.
- Agents MAY prepare release notes and a deploy checklist for each release.

### 10.4 Human review for security-sensitive code
- A PR that touches any of the following is **security-sensitive**:
  - authentication and account linking;
  - RLS policies, migrations that create or change tables or policies, and database functions with elevated rights (`SECURITY DEFINER`);
  - server functions that accept scores or grant rewards or entitlements;
  - payment code;
  - secret or environment configuration;
  - Content-Security-Policy and other security headers.
- A security-sensitive PR needs **two approvals:** a `qa` review **and** a review by the Board Operator, a human. A `qa` approval alone MUST NOT lead to a merge.
- The platform repository SHOULD list these paths in `.github/CODEOWNERS` and its `AGENTS.md`. The authoring agent MUST mark the PR (`Security-sensitive: yes`).
- Payment code MUST NOT be written before a separate payments ADR and legal review exist. That review covers the Vietnamese online-game licence (Decree 147/2024/ND-CP), a payment provider, refunds and tax.

### 10.5 Player data
- Store the minimal data set defined by the platform's `docs/requirements.md`. Every table with player data MUST have RLS enabled.
- Agents MUST NOT read, export or copy production player data, including for debugging. Production incidents are handled by the Board.
- Ads and any non-essential cookies load only after consent. Consent and the privacy policy are platform features.

## 11. Supply-chain safety

Status: Board rule (Board Operator request, 2026-11-04; merged with ADR-014's PR). External code is the easiest way to get malicious behaviour into the studio. A skill, plugin, hook or MCP server runs **with the agent's permissions**, and its text is read as instructions. An npm package's install script runs on the studio machine. Every external item is therefore treated as untrusted code until it is reviewed.

### 11.1 Studio dependencies (registry entries)
Before an entry moves to `approved`, the evaluation Task MUST record a security review against the reviewed commit or version. It covers:
1. **Origin.** The repository is the official one: the owner matches the project, it is not a fork or a copy, and the npm package name and publisher match the repository (check for typosquats).
2. **Install path.** Read the install scripts (`preinstall` / `postinstall`), installers, `curl | sh` lines, and anything that writes outside the install directory or changes Provider settings.
3. **Agent-facing text.** Read every `SKILL.md`, plugin manifest, hook, command and agent prompt in full. Look for prompt injection, instructions to read secrets or home-directory files, to send data out, to disable permissions (for example `--dangerously-skip-permissions`, `bypassPermissions` or `--dangerously-bypass-approvals-and-sandbox`), or to install more things.
4. **Runtime behaviour.** Network calls, telemetry, required accounts or API keys, paid services, and data sent to third parties.
5. **Health.** Maintainer activity, recent ownership or maintainer changes, open security advisories (GitHub Security Advisories, OSV, `npm audit`), and license.
6. **Trial.** If installation is local and harmless, test in a scratch directory outside every repository, with no secrets in the environment and no Paperclip keys bound.

Rules:
- Pin integrated items to an exact version or commit SHA. `@latest` MUST NOT be used for integrated items. An upgrade is a new review of the diff since the reviewed version.
- The Board installs. Agents MUST NOT install skills, plugins, hooks or MCP servers by themselves.
- A finding of malicious or deceptive behaviour → `rejected`, with the reason in `notes`. A risky but legitimate option (for example a mode that bypasses permissions) → approve only with that option disabled, and record how.

### 11.2 Game and platform repositories
- A Task MAY add a runtime or dev package only when its acceptance criteria need it. The PR MUST list each added or upgraded package with its version and why it is needed.
- The lockfile is committed. CI and agents install with `npm ci`, not `npm install`, except when adding a package on purpose.
- Check new packages for look-alike names, very new or single-maintainer packages, install scripts, and advisories (`npm audit`). Reviewers (`qa`, and the Board for platform security-sensitive PRs) check the package list in the diff.
- No script tags from CDNs without a pinned version and Subresource Integrity. The platform's CSP allows only the origins that are needed (the backend, the ad network after consent).
- Art, audio, fonts and code snippets come only from sources with a known license, recorded in the repository (for example in `CREDITS.md`).
- A game build MUST NOT include any third-party script that the game's design does not list. In particular: no analytics, no ad SDK, and no remote code loading.

## Related documents
- [../operations/security-operations.md](../operations/security-operations.md) · [../../company/RULES.md](../../company/RULES.md) · [../decisions/ADR-009-approval-before-merge.md](../decisions/ADR-009-approval-before-merge.md)
