<!-- Phase A audit of the local_trusted -> authenticated migration, 2026-11-20. Delivered outside the repository and added unchanged under D-AUTH-08 (docs/roadmap/auth-migration-phase-a3-board-decisions.md). -->

# Phase A: Paperclip API caller audit for the `local_trusted` → `authenticated` migration

- **Date:** 2026-11-20
- **Scope:** read-only audit of `datpham02/company-os` at `origin/main` `78341b1`, and of the installed Paperclip 2026.1023.0 source.
- **Not done in this phase:** no files edited, no branch or commit, no call to the live Paperclip instance, no agent touched.
- **Status:** Phase A nearly complete. Every repository caller is classified. The open items are in §6 and §8.

## 1. Executive summary

- **Five repository callers** use the Paperclip API: `pc.py`, `post-import.py`, `sync-instructions.py`, `review-wake-watchdog.ts` and `start-studio.cmd`.
  - The first four send **no `Authorization` header**, so all four fail once the instance runs in `authenticated` mode.
  - `start-studio.cmd` only calls `GET /api/health`. That route keeps answering in `authenticated` mode (measured in the sandbox).
- **Three agent-side callers** live outside the repository: the two helper scripts bundled with Paperclip, and the `Paperclip projects` MCP server.
  - They use per-run agent keys, so by design they should not be affected.
  - This is **not verified with real runs**: the sandbox agent runs were cancelled.
- **Two blockers** were found that the migration plan did not list:
  1. **`pc.py` hardcodes the Board identity as `local-board`** (line 25). The constant is used three ways:
     - to display assignees;
     - to gate `approve` and `request-changes`;
     - as the approver stage participant set by `create`.

     In `authenticated` mode `local-board` cannot sign in, and a new Board user has a different id. As a result, `approve` is refused, and **any open issue whose stage participant is `local-board` cannot get a decision**: Paperclip accepts a stage decision only from the active participant.
  2. **No company role gives a least-privilege automation identity.**
     - The roles are `owner`, `admin`, `operator` and `viewer`.
     - `viewer` grants nothing.
     - `operator` already includes `agents:create`, `agents:configure`, `tools:admin`, `environments:manage` and more.
     - A Board API key belongs to a user and carries all of that user's permissions.
- **Correction to the plan's background, point 4:** `local-board` does keep `instance_admin` and its company access after the switch. However, it **has no way to sign in**. The human operator's user must be promoted and given company access by hand. That procedure was verified in the sandbox; see `step2-board-decisions.md` §6b.

## 2. Files inspected

**Code:**
- `.claude/skills/paperclip/scripts/pc.py`
- `.claude/skills/paperclip/scripts/review_pack.py`: no API calls; works from fixtures only.
- `scripts/setup/post-import.py`
- `scripts/setup/sync-instructions.py`
- `scripts/setup/build-package.py`: no API calls.
- `scripts/maintenance/move-files.py`: no API calls.
- `runtime/tools/review-wake-watchdog.ts`
- `runtime/tools/start-studio.cmd`

**Configuration and documentation:**
- `.claude/skills/paperclip/SKILL.md`
- `config/paperclip/agents.json`
- `dependencies/registry.yaml`
- 22 Markdown files that mention API routes, found by pattern search.

**Outside the repository (read only):**
- Paperclip server routes and authorization code: `routes/authz.js`, `services/authorization.js`, `services/company-member-roles.js`, `routes/access.js` (the `board-api-keys` route).
- Paperclip CLI board-auth code: where the CLI stores its token.
- The two helper scripts bundled with the `claude_local` adapter.
- Windows Task Scheduler.

**Search patterns used:**
`PAPERCLIP_URL`, `PAPERCLIP_API_URL`, `PAPERCLIP_API_KEY`, `Authorization`, `Bearer`, `urllib.request`, `fetch(`, `curl`, `/api/`, `paperclipai auth`, `127.0.0.1:3100`, `localhost:3100`.

## 3. API caller inventory

| Caller | Execution context | Current identity | After the switch |
|---|---|---|---|
| `pc.py` (12 commands) | Interactive, run by the Board Operator through Claude Code | Implicit `local_trusted`, plus a hardcoded `BOARD_USER = "local-board"` | **Fails:** 403 with no token, plus the `local-board` logic error |
| `post-import.py` | Run by hand after an import | Implicit | **Fails** |
| `sync-instructions.py` | Run by hand | Implicit | **Fails** |
| `review-wake-watchdog.ts` | Unattended loop, sweeping on an interval | Implicit | **Fails:** every sweep throws |
| `start-studio.cmd` | Interactive launcher | Calls only `GET /api/health` | Does not fail, but still starts a watchdog that will fail |
| `paperclip-issue-update.sh`, `paperclip-upload-artifact.sh` (bundled with Paperclip) | Inside an agent run | `PAPERCLIP_API_KEY` and `PAPERCLIP_RUN_ID`, issued per run | Unchanged by design; **not verified with real runs** |
| MCP `Paperclip projects` | Inside an agent run | Agent identity | Same as above |
| Paperclip UI | Browser | Implicit session | Needs sign-in (verified on Windows) |

**`pc.py` commands:** `health`, `overview`, `show`, `log`, `release`, `triage`, `cancel`, `comment`, `assign`, `create`, `wake`, `cancel-run`. `approve` and `request-changes` also exist and go through `board_decision`.

## 4. Endpoint × caller × identity × permission matrix

The "Server requires" column is taken from the Paperclip 2026.1023.0 source.

| Endpoint | Caller | Operation | Server requires |
|---|---|---|---|
| `GET /health` | `pc.py`, launcher | Read | No authentication |
| `GET /companies` | `pc.py`, `post-import`, `sync`, watchdog | Read | `assertBoard` |
| `GET /companies/:id/agents` | `pc.py`, `post-import`, `sync` | Read | Company access |
| `GET /companies/:id/projects` | `pc.py`, `post-import` | Read | Company access |
| `GET /companies/:id/issues` | `pc.py`, watchdog | Read | Company access |
| `GET /issues/:id`, `/issues/:id/runs`, `/issues/:id/comments` | `pc.py`, watchdog | Read | Issue read allowed |
| `GET /heartbeat-runs/:id/log` | `pc.py log` | Read | Run read and run telemetry allowed |
| `PATCH /issues/:id` | `pc.py` `release`, `approve`, `request-changes`, `cancel`, `assign` | Status, assignee, workspace, decision | `issue:mutate`; a stage decision **must come from the active participant** |
| `POST /issues/:id/comments` | `pc.py comment` | Create | A Board user |
| `POST /companies/:id/issues` | `pc.py create` | Create | Company access; the created stage names `local-board` |
| `POST /agents/:id/wakeup` | `pc.py wake`, watchdog | Wake | Board, company access, and the `agent:wake` action (needs a role other than `viewer`) |
| `POST /heartbeat-runs/:id/cancel` | `pc.py cancel`, `cancel-run` | Cancel | `assertBoard` |
| `GET /companies/:id/secrets` | `post-import` | Read secret metadata | Board and secret-definition admin |
| `GET /agents/:id` | `post-import` | Read config | Agent read allowed |
| `PATCH /agents/:id` (`adapterConfig`) | `post-import` | Bind secrets | `agents:configure`; agents cannot change their own config |
| `POST /agents/:id/resume` | `post-import --resume` | Resume | `assertCanResumeAgent` |
| `PATCH /projects/:id/workspaces/:wid` | `post-import` | Set `cwd` | Project read allowed; agent command paths blocked |
| `GET /agents/:id/instructions-bundle/file` | `sync` | Read role text | `assertCanReadAgent` |
| `PUT /agents/:id/instructions-bundle/file` | `sync` | Write role text | `assertCanManageInstructionsPath` |

**How far this is verified:**
- The guard functions in the last column were read directly from the source.
- What each **role** actually grants per action was read only from the role grant table. The policy logic behind it was not traced in full, so treat those role conclusions as provisional.

## 5. Authentication gaps

1. None of the four scripts has a way to send a token: no token variable, no `Authorization` header.
2. `pc.py` hardcodes `local-board` in three places: the assignee display (line 162), the `board_decision` gate (line 602) and the approver participant set by `create` (line 686). Open issues already have stages that name `local-board`.
3. The watchdog runs unattended, and a Board API key inherits all of its user's permissions, including instance admin if that user is an admin.
4. No caller tells a 401 apart from a 403. `pc.py` turns every HTTP error into one `ApiError`. The watchdog would throw on every sweep and keep producing errors.
5. The launcher does not check authentication before it starts the watchdog.

## 6. External dependencies not yet verified

- Agent behaviour in `authenticated` mode with real runs: the helper scripts, MCP, and the per-run keys. The test was cancelled, so this stays unverified.
- How the Cursor agents call the API; they have no allowlist.
- **CLI token store:** `paperclipai auth login` writes `~/.paperclip/auth.json` as **plain JSON** (from the source; in the sandbox the token sat in the `token` field). File permissions, token refresh and use by concurrent processes are not verified.
- **Board API key expiry:** `expiresAt` is optional, so keys may never expire unless one is set. Revocation exists: `DELETE /board-api-keys/:keyId`.
- **Scheduled tasks:** none calls Paperclip. `StoveWatchdog` belongs to Smilegate and is unrelated.

## 7. Recommended authentication contract (not implemented)

| Caller | Proposed identity | Credential source |
|---|---|---|
| `pc.py` | The Board Operator's own Board user | The `paperclipai auth login` store, or a `PAPERCLIP_BOARD_TOKEN` variable set only in the Board's session. Never a command-line argument |
| `post-import.py`, `sync-instructions.py` | The same Board user (manual, rare) | Same as above |
| Watchdog | A **separate automation user** with the `operator` role, company access to Soucean only, **not** instance admin, and a Board API key with an expiry | An environment variable of the watchdog process; never written into the `.cmd` file |
| Agents | Unchanged: their own agent keys | **Never** a Board token |

**Shared rules:**
- One small Python helper loads the token and **fails closed** when it is missing. It never falls back silently to unauthenticated access.
- Tokens are redacted from every log line and exception.
- 401 and 403 are handled separately, with an actionable message for each.
- `BOARD_USER` comes from `GET /cli-auth/me` instead of a hardcoded value.

**Residual risk:** the `operator` role grants far more than the watchdog needs. The Board must accept that risk or choose an alternative.

## 8. Risks and unresolved questions

- **Stage participant migration:** open issues whose Board approver is `local-board` must be moved to the new user, or `local-board` must be kept in some form. The supported way to do either is not yet known.
- Whether a `viewer` user can be given only `agent:wake`. `updateMemberPermissionsSchema` accepts a `grants` list; not verified.
- **Rollback:** returning to `local_trusted` (as done in the sandbox) reopens the keyless Board path while the instance runs in that mode.
- The workspace folder ACL risk (all Authenticated Users have Modify) remains, independent of this migration.

## 9. Phase A completion status

- **Complete:** every repository API caller is classified.
- **Open:** the items in §6 and §8. Each needs either a live check or a Board decision.

## 10. Next actions requiring Board approval

1. Allow this audit to be committed, for example as `docs/architecture/auth-migration-audit.md`, on a new branch with a PR.
2. **Decide the Board identity after the switch:** keep `local-board`, or move stage participants to the new user. This blocks Phase B.
3. Accept the **`operator` role for the watchdog's automation user**, or choose an alternative: drop the watchdog, or run its sweeps by hand as the Board.
4. Decide whether a **test environment** is allowed for verifying §6 and §8. No sandbox exists any more.
