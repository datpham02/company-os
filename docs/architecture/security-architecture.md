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

## 9. Destructive operation safeguards

1. Prohibited for all automated actors (no approval can enable them in v1): force-push, deleting repositories, deleting the Default Branch, rewriting published history, deleting tags.
2. Worktree cleanup never discards uncommitted changes.
3. Branch protection is the technical backstop if an agent ignores rules.
4. Every Run's commit range is recorded so changes can be reverted.

## Related documents
- [../operations/security-operations.md](../operations/security-operations.md) · [../../company/RULES.md](../../company/RULES.md) · [../decisions/ADR-009-approval-before-merge.md](../decisions/ADR-009-approval-before-merge.md)
