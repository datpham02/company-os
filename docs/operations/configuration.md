# Configuration

## 1. Configuration layers

| Layer | Location | In Git? | Holds |
|---|---|---|---|
| Studio definition | `knowledge/company/`, `knowledge/company/agents/`, `knowledge/company/workflows/` | Yes | Roles, rules, processes |
| Registries | `knowledge/projects/registry.yaml`, `dependencies/registry.yaml` | Yes | Portable project and dependency data |
| Paperclip | Paperclip instance (UI/API) | No | Company, agents, adapter configs, secrets, projects |
| Provider config | `~/.claude/`, `~/.codex/` | No | Auth, MCP servers, provider settings |
| Runtime config (`PLANNED`) | `~/.config/game-studio/runtime.yaml` | No | Paths, limits, agent mapping |
| Secrets | Paperclip secrets; `~/.config/game-studio/secrets.env` (mode 600, `PLANNED`) | Never | Tokens |

## 2. Paperclip agent configuration (Stage 1)

Per Agent Instance (fields `VERIFIED` in Paperclip adapter docs):

| Setting | Value guidance |
|---|---|
| Adapter type | `claude_local` or `codex_local` per [../../knowledge/company/ORGANIZATION.md](../../knowledge/company/ORGANIZATION.md) |
| `cwd` | Required by the adapter. For project work, Paperclip's execution workspace supplies the effective directory. Point the base `cwd` at a neutral directory such as `~/game-studio-workspace` (exact interplay `UNVERIFIED`, OQ-002) |
| `model` | Leave unset for the adapter default unless the Board chooses otherwise |
| `timeoutSec` / `graceSec` | 3600 / 30 (`PROPOSED`) |
| `dangerouslySkipPermissions` (Claude) | `false` unless the Board approved `bypass` for this instance (C-002) |
| `dangerouslyBypassApprovalsAndSandbox` (Codex) | `false` |
| `instructionsFilePath` (Codex) | Absolute path to `~/game-studio/agents/<agent-id>/AGENTS.md` |
| `promptTemplate` | Include `{{agent.name}}` and a pointer to studio rules (OQ-023) |
| `env` | `GH_TOKEN` via secret ref for code-writing roles; Git author variables |

## 3. Runtime configuration (`PLANNED`, Stage 2)

Proposed shape of `~/.config/game-studio/runtime.yaml` (not read by anything yet):

```yaml
paperclip:
  apiUrl: http://localhost:3100/api
frameworkRepo: /home/<user>/game-studio
workspaceRoot: /home/<user>/game-studio-workspace
stateDir: /home/<user>/.local/state/game-studio
limits:
  maxConcurrentRuns: 2
  maxConcurrentRunsPerProject: 2
  defaultTimeoutSec: 3600
  graceSec: 30
agents:                         # Paperclip agent UUID → Agent ID
  "<paperclip-agent-uuid>": { role: gameplay-programmer, provider: claude_local, permissionProfile: workspace-write }
projects:                       # Project ID → local overrides
  node-arena: { primaryCheckout: /home/<user>/game-studio-workspace/repos/node-arena }
```

A JSON Schema for this file is `PLANNED` in `schemas/runtime-config.schema.yaml`.

## 4. Environment variables

| Variable | Set by | Used by |
|---|---|---|
| `PAPERCLIP_API_URL`, `PAPERCLIP_API_KEY`, `PAPERCLIP_AGENT_ID`, `PAPERCLIP_COMPANY_ID`, `PAPERCLIP_RUN_ID`, `PAPERCLIP_TASK_ID`, `PAPERCLIP_WAKE_REASON` | Paperclip per heartbeat (`VERIFIED` names) | Agents; Runtime |
| `GH_TOKEN` | Paperclip secret binding | `gh`, git over HTTPS |
| `ANTHROPIC_API_KEY` / `CLAUDE_CODE_OAUTH_TOKEN` | Optional, per instance | Claude Code |
| `CODEX_HOME` | Paperclip-managed per agent (`VERIFIED`) | Codex |
| `GAME_STUDIO_CONFIG` | `PLANNED` | Runtime config path override |

## Related documents
[../architecture/repository-architecture.md](../architecture/repository-architecture.md) · [../integrations/paperclip-integration.md](../integrations/paperclip-integration.md) · [security-operations.md](security-operations.md)
