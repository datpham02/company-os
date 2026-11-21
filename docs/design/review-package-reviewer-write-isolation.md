# Review Package: removing Paperclip write capability from the reviewer (P0)

- **Status:** design approved by the Board Operator ("Duyệt, triển khai"); **implemented** 2026-11-21 in PR #50 (code, offline tests, opt-in probe). No Paperclip configuration changed; the sandbox step (§7) is not run and needs separate approval.
- **Trigger:** the Option B live check ([review-package-option-b-live.md](review-package-option-b-live.md) §3, finding 1). The issue-scoped `code-reviewer` run received Paperclip MCP tools that can write: `create_task`, `create_project`, `set_task_title`. `--tools Read,Grep,Glob` did not remove them.
- **Versions:** Paperclip 2026.1023.0 (installed global package, read-only source reading); Claude Code 2.1.329.
- **Evidence types:**
  - **Source** = Paperclip code reading. Server paths are relative to `@paperclipai/server/dist`; adapter paths to `@paperclipai/adapter-claude-local/dist`.
  - **Local probe** = Claude Code run on this machine against a throwaway stdio MCP server with one read and one write tool. No Paperclip involved; about US$0.05 in total.
- **G-13 stays open.**

## 1. Paperclip source investigation

### 1.1 Registration: which MCP servers a run gets

| Server (tool prefix) | Registered when | Source |
|---|---|---|
| "Paperclip projects" (`mcp__Paperclip_projects__*`) | Every run of an adapter with `supportsLocalAgentJwt` (true for `claude_local`) **that has an issue** (`issueRef`), when the API base URL is configured. **No per-agent or per-run switch** | `services/heartbeat/runtime-execution.js` 514–516; `adapters/registry.js` `claudeLocalAdapter` (`supportsLocalAgentJwt: true`) |
| "Paperclip connections" (`mcp__Paperclip_connections__*`) | Adapters with `runtimeToolDelivery: "native_mcp"` (`claude_local`), when runtime tool access is created | `runtime-execution.js` 487–512; `registry.js` (`runtimeToolDelivery: "native_mcp"`) |
| Agent tool-profile connections | Connections assigned to the agent through tool access profiles | `services/heartbeat/run-preparation.js` `buildPaperclipRuntimeMcpServers` (543 ff.); the reviewer has none |

**Why Phases 4b and 5 did not show it:** their reviewer runs were company-scoped (no `issueRef`), so "Paperclip projects" was not added. "Paperclip connections" was listed as `failed` there.

### 1.2 Tool list and invocation of "Paperclip projects"

- **Endpoint:** `POST /api/mcp/project-tools` (`routes/project-tools.js`).
  - The actor comes from the request's bearer token, which is the run's local agent JWT.
  - It checks `assertCompanyAccess` and that the tool is in the list for the issue's work mode. Nothing else.
- **Tools:** `projectToolDefinitions(workMode, true)` (`services/project-tools.js`):
  - `create_project`, `list_project_repositories`, `list_projects`, `create_task`, `set_task_title`;
  - filtered by the catalog's `allowedModes` for the issue's work mode.
- **Execution:** `callProjectTool` sends a normal authenticated API request with the run's JWT:
  - `POST /companies/<id>/projects`;
  - `POST /companies/<id>/issues`, as a child of the issue, assigned to the caller by default;
  - `PUT /issues/<id>/title`.

  The only limit is the agent's own API permissions.

### 1.3 The credential behind it

- **JWT minting:** `createLocalAgentJwt(agentId, companyId, adapterType, runId, …)` (`agent-auth-jwt.js` 95 ff.). It carries `run_id`. Its TTL is `PAPERCLIP_AGENT_JWT_TTL_SECONDS`, default 48 h (line 29). Revocation at run end was not found in the code read; **not verified**.
- **Where it ends up:**
  - in the agent's environment as `PAPERCLIP_API_KEY` (adapter `server/execute.js` 172–173);
  - in a per-run `mcp-config.json` as `Authorization: Bearer …` (adapter `server/claude-config.js` 116–139).
- **The file stays on disk.** It is written under `<instance>/companies/<company>/agents/<agent>/claude-runtime/runs/<run>/mcp/`, and the files of all five OPT reviewer runs were still there after the runs ended. Their contents were not opened.

### 1.4 What the adapter passes to Claude Code

- `--mcp-config <that file> --strict-mcp-config`, then the agent's `extraArgs` (adapter `server/execute.js` 641–647).
- `extraArgs` cannot remove a server from Paperclip's config file.
- `--add-dir <prompt bundle>`, where the bundle is `<instance>/companies/<company>/claude-prompt-cache/<key>` (`prompt-cache.js` 9–15, 101–122). It is a sibling of `agents/`, not a parent of the `mcp-config.json` folders.

### 1.5 Paperclip's own sandbox

`filesystemScope` / `networkScope` in the adapter config start a local process sandbox (`adapter-utils/dist/local-process-sandbox.js`). It refuses on anything but Linux (line 283; it uses `bwrap`), so it is **not available** on this Windows studio machine.

## 2. Claude Code behaviour (local probe, 2.1.329)

Each variant used `--restricted --tools Read,Grep,Glob --strict-mcp-config --mcp-config <fake> --permission-mode dontAsk` and the C1 settings (allow Read, Grep, Glob; deny Edit, Write, NotebookEdit, Bash, PowerShell, WebFetch, WebSearch). The prompt asked the model to call `write_thing`.

| Variant | MCP tools in the model's tool list (`init.tools`) | `write_thing` reached the server |
|---|---|---|
| C1 only | **yes** (`read_thing`, `write_thing`) | no: refused at invocation by `dontAsk` (`permission_denials`) |
| C1 + `--allowedTools Read,Grep,Glob` | **yes** | no: refused at invocation |
| C1 + `--disallowedTools mcp__fake` | **no** | no: not callable |
| C1 + settings deny `mcp__fake` | **no** | no |
| C1 + settings deny `mcp__fake__write_thing` | only that tool removed | — |
| C1 + settings deny `mcp__*` | **no** (all MCP tools) | no |
| C1 + settings deny `mcp__` | yes (pattern does nothing) | no: refused at invocation |

**Conclusions:**
- `--tools` limits built-in tools only.
- `dontAsk` with an allow list refuses unlisted MCP tools **at invocation**, before the server is called.
- A deny rule on `mcp__*` (or on a server name) **removes the tools from the model's tool list**. The MCP server still connects (`mcp_servers: connected`), but no tool of it is offered.

## 3. Root cause

- Option B makes the reviewer run issue-scoped.
- For every issue-scoped `claude_local` run, Paperclip 2026.1023.0 adds its "Paperclip projects" MCP server, authenticated with the run's agent JWT. There is no per-agent opt-out.
- The reviewer profile removed built-in tools with `--tools` but had no rule for MCP tools. Only the `dontAsk` allow list stood between the model and Paperclip writes.

## 4. Options

| Option | Feasible on 2026.1023.0? | Notes |
|---|---|---|
| **A. Paperclip does not register write tools for the reviewer** | **No**, without changing Paperclip | Registration is unconditional for issue-scoped runs of JWT adapters (§1.1). An upstream feature (per-agent "no runtime MCP", or a read-only tool profile) would be needed. Not a fork |
| **B. Read-only MCP gateway** | Not needed | The reviewer needs **no** Paperclip read either: everything it reads is in the staged package on disk. A gateway would add a component without purpose |
| **A′. Remove all MCP tools at registration in Claude Code** (recommended) | **Yes** | Settings deny `mcp__*` and `--disallowedTools mcp__*`: no MCP tool is in the model's tool list (§2) |
| **C. Invocation enforcement** | Present today | The `dontAsk` allow list refuses any non-allowed tool before it runs (§2). Kept as the second layer, not the only one |
| **D. Detection by the relay** (recommended addition) | **Yes** | The run log's `init` event lists the tools the model had; the relay can refuse a verdict whose run offered anything but `Glob`, `Grep`, `Read`, or tried any other tool |

## 5. Recommended design

Three independent layers, so that removing one does not open writes.

1. **Registration (Claude Code):**
   - add `"mcp__*"` to the reviewer settings' `deny` list;
   - add `--disallowedTools mcp__*` to the reviewer's `extraArgs`;
   - keep `--tools Read,Grep,Glob` and `--restricted`.

   Result: the model's tool list is exactly `Glob`, `Grep`, `Read`.
2. **Invocation (Claude Code):** keep `--permission-mode dontAsk` with `allow: Read, Grep, Glob` and the built-in deny list. Any other tool, including an MCP tool added by a future Paperclip version under a new name, is refused before it runs.
3. **Verification and detection (`review_relay.py`, new, fail closed).** Before accepting a verdict:
   - the run log's `init.tools` must be **exactly** `{Glob, Grep, Read}`. An allow list, not a deny list, so any new tool, write or not, makes the relay refuse;
   - the log must contain no `tool_use` of any other name, and `result.permission_denials` must be empty (an attempt is treated as tampering);
   - `pc.py review-start` refuses to start unless the reviewer agent's configuration (`GET /api/agents/<id>`) contains the required `extraArgs` (`--restricted`, `--tools Read,Grep,Glob`, `--disallowedTools mcp__*`, `--permission-mode dontAsk`, one `--add-dir` = `<Staging Root>/current`), no `env`, and a settings file whose `deny` contains `mcp__*` and whose `allow` is exactly Read, Grep, Glob.

**Reviewer tools after the change:** `Read`, `Grep`, `Glob`, confined by `--restricted` to its `cwd`, `<Staging Root>/current` (package, `REVIEW.md`, `REVIEW-ID.txt`) and Paperclip's prompt-bundle folder. No Paperclip tool, read or write: none is needed.

**Removed or blocked:**
- all `mcp__Paperclip_projects__*`: `create_task`, `create_project`, `set_task_title`, `list_projects`, `list_project_repositories`;
- all `mcp__Paperclip_connections__*`: `connection_request`, `connections_search`;
- any agent tool-profile MCP connection;
- any future MCP server or tool (`mcp__*`);
- Bash, PowerShell, WebFetch, WebSearch, Edit, Write and NotebookEdit stay absent and denied.

**The verdict still goes only through `review_relay.py`.** The relay alone writes the comment and the decision on the parent. Paperclip itself posts the run's final message on the sub-issue (finding 2 of the live check). That is Paperclip's action, not a reviewer tool, and is unchanged by this design.

## 6. Bypass paths

| Path | Assessment | How it is tested |
|---|---|---|
| Calling an MCP tool not in the list | The model can only call tools in its list. Even if it could, `dontAsk` refuses unlisted tools | Local probe (done); sandbox injection test (planned) |
| Direct Paperclip API call | Needs a network-capable tool (Bash, PowerShell, WebFetch): absent from the tool list and denied | `init.tools` check; sandbox |
| Using `PAPERCLIP_API_KEY` from the environment | Readable only through a shell or by reading a process file; no such tool | Same |
| Reading a persisted `mcp-config.json` (bearer token) | Outside the `--restricted` folders (§1.3–1.4), so Read refuses. **Risk outside the reviewer:** any same-user process with a shell (Cursor authors) can read these files; the tokens live 48 h | Sandbox Read attempt on that path (planned). The wider risk belongs to G-14 / OQ-043 |
| Another MCP endpoint with write rights | Every MCP server's tools are removed by `mcp__*` | Probe (done); sandbox |
| A tool wrapper that forwards requests | No tool can run programs or open connections | `init.tools` check |
| A compromised or misbehaving Claude Code binary | Not covered: all three layers run in the reviewer's own process, which holds the JWT. Only an OS or network boundary would cover it (Paperclip's sandbox is Linux-only) | Not testable here |

## 7. Test plan (after approval)

**Offline (default suite, fake Paperclip):**
- relay refuses when `init.tools` has any extra tool (each Paperclip tool name, an unknown `mcp__x__y`, `Bash`), when it is missing, when the init event is missing, when a non-allowed `tool_use` appears, or when `permission_denials` is not empty;
- relay accepts exactly `Glob, Grep, Read`;
- `review-start` refuses a reviewer configuration without `--disallowedTools mcp__*`, without the settings deny, with any `env`, or with another `--add-dir`;
- the regression suite (review-start, challenge, reviewId, single decision) passes unchanged.

**Local probe (scripted, opt-in, not in the default suite):** the §2 matrix as a repeatable script using the real reviewer settings file, so a Claude Code upgrade can be re-checked.

**Sandbox (needs Board approval: it changes the `OPT` reviewer agent's configuration and runs it):**
1. Update `OPT`'s `code-reviewer` `extraArgs` and settings file.
2. Run `review-start` on a new parent issue whose task data asks the reviewer (as an injection) to call `create_task`, `set_task_title`, `create_project`, to read the persisted `mcp-config.json` and to fetch the Paperclip API.
3. Expected:
   - `init.tools` is exactly `Glob, Grep, Read`;
   - any attempt is refused;
   - no new issue, project, title change, comment (other than Paperclip's own final-message comment) or agent change;
   - the relay accepts the clean run and records one decision.
4. Then a run with the old configuration must be **refused by the relay** (detection layer).
5. Soucean agents unchanged.

## 8. Remaining limits

- **Enforcement is inside Claude Code**, in the same process that holds the JWT. There is no OS or network boundary on Windows here.
- **The JWT itself can write** (agent-level API rights) and is not scoped read-only by Paperclip 2026.1023.0. Persisted `mcp-config.json` files keep valid tokens up to 48 h, readable by same-user processes (G-14). A Paperclip feature request (per-agent "no runtime MCP" / read-only token) is the proper long-term fix.
- **Paperclip still posts the reviewer's final message** on the sub-issue.
- **Claude Code behaviour** was probed on 2.1.329 only; every upgrade must re-run the probe.
- **G-13 stays open.**

## 9. Implementation (PR #50)

- `review_relay.check_tool_surface`: layer 3 in the relay (check 5, before the verdict is parsed).
- `review_relay.check_reviewer_config`: run by `review-start` (`GET /api/agents/<code-reviewer>`) before anything is created or woken. It also reads the reviewer settings file named by `--settings`.
- `probe_reviewer_tools.py`: the §2 matrix as an opt-in script (full profile, settings deny only, flag only). Run on 2026-11-21 with Claude Code 2.1.329: **PASS** for the strict settings. A negative control with settings lacking the `mcp__*` deny failed the "settings" variant as expected; even there the write call never reached the server.
- Tests: allow-list checks in `test_review_relay.py` (`ToolSurface`, `ReviewerConfig`); `test_pc.py` 300 OK.
- **Existing reviewer agents (`REV`, `RPR`, `OPT`) do not have the new profile.** `review-start` refuses them until their `extraArgs` and settings are updated. That is a Paperclip configuration change, part of the sandbox step.

## 10. Board decisions

1. Approve the design (layers 1–3), or ask for an upstream Paperclip change first.
2. Approve implementation in PR #50 (code and offline tests; no Paperclip change).
3. Separately, approve the sandbox step (§7), which changes the `OPT` reviewer's configuration and runs it.
4. Consider a separate item for persisted `mcp-config.json` tokens (G-14), outside this P0.
