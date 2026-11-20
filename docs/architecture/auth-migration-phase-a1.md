# Authentication migration, Phase A.1: blockers and design

- **Status:** `PROPOSED`. Investigation and design only. Nothing here is implemented or authorized.
- **Board decisions:** the five decisions of §7 were approved on 2026-11-20 as D-AUTH-01 to D-AUTH-05 in [auth-migration-board-decisions.md](../roadmap/auth-migration-board-decisions.md). Approval is not authorization to implement; runtime verification and Phase B are still pending.
- **Date:** 2026-11-20.
- **Paperclip:** 2026.1023.0.
- **Repository:** `datpham02/company-os`, `main` at `78341b1`.
- **Builds on:** the Phase A audit, [auth-migration-phase-a-audit.md](auth-migration-phase-a-audit.md) (added to the repository under D-AUTH-08).
- **Related records:** OQ-043, G-14, and [step2-board-decisions.md](../roadmap/step2-board-decisions.md) §6b (sandbox results).

## How to read the evidence labels

| Label | Meaning |
|---|---|
| **[source]** | Read in the installed Paperclip source. Runtime behaviour is not confirmed. |
| **[sandbox]** | Observed in the OQ-043 sandbox on 2026-11-20 (§6b). No agent runs took place there. |
| **[live-read]** | Read from the studio instance with GET requests only, on 2026-11-20. |
| **[design]** | A recommendation or an assumption. |

**Source path prefixes** (below `node_modules\paperclipai` of the global install):
- `S` = `node_modules\@paperclipai\server\dist`
- `SH` = `node_modules\@paperclipai\shared\dist`
- `D` = `node_modules\@paperclipai\db\dist`
- `CLI` = `dist\index.js`

---

## 1. Executive summary

1. **Paperclip has a supported way to hand `local-board` over to a real user: board claim.** **[source]** This corrects the Phase A audit and the "promote in `local_trusted`" workaround used in the sandbox.
   - When the instance starts in `authenticated` mode and `local-board` is the only instance admin, Paperclip creates a one-time claim link and prints it to the server console.
   - The link is valid for 24 hours and kept in memory only (`S\board-claim.js` 6, 31-46; `S\index.js` 547, 1620-1629).
   - A signed-in user who opens it (`POST /api/board-claim/:token/claim`, which needs a browser session: `S\routes\access.js` 2106-2112) is given instance admin. That user also becomes **`owner` of every company**.
   - In the same transaction, **`local-board` loses instance admin** (`S\board-claim.js` 66-103).
   - The claim was **not exercised** in the sandbox, so this path is not runtime-verified.
2. **The `local-board` stage participants do not migrate by themselves, and they block decisions.** **[source]**
   - A stage decision matches the actor on its exact `userId`. Board, owner or instance-admin status does not count as a match (`S\services\issue-execution-policy.js` 323-336, 603, 750-751).
   - **[live-read]** 29 of the 30 SOU issues reference `local-board`. Three are open:
     - **SOU-28** is `in_review`, and its approval stage is waiting on `local-board` now;
     - **SOU-17** and **SOU-30** are `backlog`, with `local-board` as their approver.
   - **[source]** A signed-in Board user can repair these with a `PATCH` of `executionPolicy` that keeps the stage and participant ids. Past decisions stay in their own table and are not rewritten.
3. **No least-privilege watchdog identity exists.** **[source]**
   - Waking an agent needs an active membership with a role other than `viewer`. No permission grant can give it.
   - Board API keys cannot be scoped; a key always acts with its owner's full rights.
   - The narrowest working setup is an `operator` member with every grant cleared. That user can still change and comment on any issue in the company, and can perform `secrets:read` and `runtime:manage`.
4. **CLI tokens are 30-day plaintext keys with no refresh.** **[source]**
   - `paperclipai auth login` stores the key in `~/.paperclip/auth.json` as plain JSON.
   - The file is not encrypted, not locked, and not written atomically.
   - There is no refresh endpoint. An expired key gets a 401 whose message talks about an agent token.
5. **Recommendation, in short:** **[design]**
   - Clear pending Board decisions before the switch.
   - Use board claim instead of the `local_trusted` promotion workaround.
   - Repoint the open issues' `local-board` participants to the claimed user.
   - Make `pc.py` read the Board user id from `/cli-auth/me`.
   - **Do not run the watchdog with Board credentials.** Retire it if Paperclip's own scheduler already covers review wakes; otherwise run sweeps by hand. Accept an `operator` automation user only as an explicit Board-approved risk.

---

## 2. Task 1: `local-board` identity and stage participants

### 2.1 Findings

| # | Finding | Evidence | Status |
|---|---|---|---|
| 1.1 | `executionPolicy` and `executionState` are JSONB columns on `issues`. Stage participants are `{id, type, agentId \| userId}`. | `D\schema\issues.js` 56-57; `SH\validators\issue.js` 274, 312, 360, 426 | [source] |
| 1.2 | A stage decision is accepted only when the actor matches the current participant: same type, and the same `userId` or `agentId`. | `S\services\issue-execution-policy.js` 323-336 (`principalsEqual`), 603, 750-751 | [source] |
| 1.3 | The route passes `actorId = req.actor.userId ?? "board"`, so in `authenticated` mode the actor is the signed-in user's id. | `S\routes\authz.js` 187; `S\routes\issues.js` 9989-9992 | [source] |
| 1.4 | **Board override:** a Board session or Board key (but not MCP OAuth) can clear the stage by setting a status other than `in_review`, or reassign to another participant of the active stage. Clearing the stage records **no decision row**. | `S\routes\issues.js` 9993; `issue-execution-policy.js` 719-748 | [source] |
| 1.5 | `executionPolicy` can be updated with `PATCH /issues/:id`, even while `in_review`. If the stage ids are not resent, new ids are generated and the active stage is **reset**: the issue returns to `in_progress`. If the ids are kept and a participant is swapped, the current participant is recomputed and the issue stays `in_review`. | `SH\validators\issue.js` 617, 727, 735; `S\routes\issues.js` 9962-9995; `issue-execution-policy.js` 242-271, 525-532, 577-602 | [source] |
| 1.6 | Policy participants are not checked for company membership. Only the issue's assignee is checked (`assertAssignableUser`). | `S\services\issues.js` 4661-4669, 7359-7360 | [source] |
| 1.7 | Decision history lives in `issue_execution_decisions` (actor ids, outcome, body). Participant changes are logged as `issue.reviewers_updated` / `issue.approvers_updated`. Nothing rewrites history. | `D\schema\issue_execution_decisions.js` 6-18; `S\routes\issues.js` 10397-10409, 10716-10740 | [source] |
| 1.8 | Paperclip's recovery scheduler only picks up issues with **no user assignee**. An `in_review` issue held by `local-board` is never escalated. | `S\services\recovery\service.js` 2938-2944 | [source] |
| 1.9 | **Board claim** moves instance admin from `local-board` to the claimer and makes the claimer `owner` of all companies. The claim needs a signed-in browser session. | `S\board-claim.js` 31-103; `S\routes\access.js` 2096-2125; `S\index.js` 547, 1620-1629 | [source], not run |
| 1.10 | In `local_trusted` mode, `ensureLocalTrustedBoardPrincipal` re-creates `local-board` with instance admin and company memberships at startup. | `S\index.js` 207-255, 510-511 | [source] |
| 1.11 | `local-board` is special-cased elsewhere: as a fallback actor id, in comment attribution (`NON_HUMAN_SENTINEL_AUTHOR_USER_IDS`) and in cost lists. None of these affects stage decisions. | `S\services\issues.js` 83; `S\services\costs.js` 348, 374; other files listed in the investigation notes | [source] |
| 1.12 | In `pc.py`, `BOARD_USER = "local-board"` is used at line 162 (assignee display), line 602 (the `approve` / `request-changes` gate) and line 686 (approver set by `create`). | `pc.py` | [source] |
| 1.13 | SOU issues touching `local-board`: 25 `done`, 1 `cancelled`, 1 `in_review` (SOU-28, active approval), 2 `backlog` (SOU-17, SOU-30, approver stage). SOU-20 does not. No other user is an assignee. | GET `/companies/:id/issues` and `/issues/:id` | [live-read] |

### 2.2 Recommended strategy [design]

**Keep `local-board` as a historical identity, not a login.** Its past decisions and comments stay attributed to it. After a claim it has no admin role. It would get one back only if the instance returned to `local_trusted` (finding 1.10).

Migration order:

1. **Before the switch, while still in `local_trusted`:** record every pending Board decision (today only SOU-28) with `pc.py approve` or `request-changes`. That writes a proper decision row as `local-board`. Avoid starting new Board-approval stages after this point.
2. **Switch** (see §5.1). Sign up in the browser, then open the board-claim link printed on the server console. Verify with `GET /api/cli-auth/me` (instance admin) and `GET /api/companies` (Soucean listed).
3. **Repoint open issues.** For every issue that is not done or cancelled and has a participant with `userId: "local-board"` (today SOU-17 and SOU-30):
   - `PATCH /issues/:id` with `executionPolicy` equal to the current policy, with **only** the `userId` replaced;
   - keep all stage and participant ids (finding 1.5);
   - use `expectedExecutionPolicy` so that the update fails if the issue changed in the meantime and cannot touch status or assignee (`S\routes\issues.js` 9660-9662, 10009-10012).
   - **Required permission:** the claimed owner's Board session or key.
4. **Leave done and cancelled issues alone.** Their history is final.
5. **`pc.py`:** read the Board user id from `GET /api/cli-auth/me` instead of a constant. Show `local-board` as "Board (legacy)". The decision gate should compare against the current user, and `create` should name the current user.

**Risks:**
- If a stage id is lost in step 3, the active stage resets with no decision row.
- The Board override (finding 1.4) can bypass a stage without leaving a decision record. `pc.py` must never use it implicitly.
- A rollback to `local_trusted` after step 3 leaves participants pointing at the claimed user, whom `local-board` cannot match. A rollback needs the reverse policy patch, or a Board override.

---

## 3. Task 2: least-privilege watchdog

### 3.1 Findings

| # | Finding | Evidence | Status |
|---|---|---|---|
| 2.1 | Permission keys exist (21 of them), but **none maps to `agent:wake`**. | `SH\constants.js` 732-754; `S\services\authorization.js` 13-27 | [source] |
| 2.2 | `agent:wake` needs an active membership whose role is not `viewer` (`requiresNonViewer`). Grants are not consulted. | `S\services\authorization.js` 1452-1484 (line 1466) | [source] |
| 2.3 | Separately, every non-GET company route refuses `viewer` ("Viewer access is read-only"). | `S\routes\authz.js` 78-92 | [source] |
| 2.4 | Grants **replace** rather than add. Role defaults are stored as rows when a member joins, and `PATCH /api/companies/:companyId/members/:memberId/permissions` deletes and re-inserts them. The caller needs `users:manage_permissions`, which by default only `owner` has. | `S\services\access.js` 286-307, 357-371; `S\routes\access.js` 3616, 3549, 1612 | [source] |
| 2.5 | Even with all grants cleared, a non-viewer member still has membership-based rights: `agent:wake`, `runtime:manage`, **`secrets:read`**, `decision_queue:manage`, `decision_triage:manage`, `issue:mutate` and `issue:comment` on company issues, and every non-GET route guarded only by company access. | `S\services\authorization.js` 1381-1388, 1431-1437, 1466-1470 | [source], not all routes reviewed |
| 2.6 | A non-admin user is limited to the companies it is a member of. | `S\services\board-auth.js` 53-84; `S\routes\companies.js` 304-309; `S\routes\authz.js` 78-82 | [source] |
| 2.7 | Board API keys **cannot be scoped**. A key resolves to its owner's live access on every request. `requestedCompanyId` only affects activity logging. | `D` `board_api_keys` schema; `S\middleware\auth.js` 240-256; `S\services\board-auth.js` 86-113 | [source] |
| 2.8 | Agent keys can only wake themselves ("Agent can only invoke itself"). | `S\routes\agents.js` 4632-4636, 4881 | [source] |
| 2.9 | There is no service-account actor type: principals are `user` and `agent` only. | `SH\constants.js` 706 | [source] |
| 2.10 | Plugins can request wakes (`issues.wakeup`, `agents.invoke`), and Paperclip has built-in issue watchdogs, execution monitors with `wake_owner`, and routines. None was evaluated for the review-wake case. | `S\services\plugin-host-services.js` 2039-2135; `SH\constants.js` 403-407, 1018, 1038; `S\routes\issues.js` 6508, 6517 | [source], not evaluated |
| 2.11 | The Step 2 audit found that Paperclip's 30-second scheduler already re-wakes reviewers of stranded `in_review` issues. The watchdog was written before that was known (OQ-035). | [stage1-gap-analysis.md](stage1-gap-analysis.md) G-12 | [source], not run |

### 3.2 Permission matrix

| Operation | Endpoint | Required | Can a custom grant give it? | Excess privilege of the minimum working identity |
|---|---|---|---|---|
| List companies | `GET /api/companies` | Board actor; filtered to memberships | Not needed; `viewer` is enough | none |
| List in-review issues | `GET /api/companies/:id/issues?status=in_review` | Company access | Not needed; `viewer` is enough | none |
| Read an issue | `GET /api/issues/:id` | `issue:read` (membership) | Not needed; `viewer` is enough | none |
| Read issue runs | `GET /api/issues/:id/runs` | `issue:read` | Not needed; `viewer` is enough | none |
| Wake an agent | `POST /api/agents/:id/wakeup` | Non-`viewer` membership plus `agent:wake` | **No** (finding 2.2) | Role `operator` with grants cleared still has everything in finding 2.5, including `secrets:read` and changing any issue |

### 3.3 Options and recommendation [design]

| Option | Security | Operation | Verified |
|---|---|---|---|
| **A. Retire the watchdog.** Rely on Paperclip's scheduler (finding 2.11); add a manual `pc.py` sweep for leftovers | No new identity | Simplest; reviews may wait until a sweep | Scheduler coverage of this case is **not verified at runtime** |
| **B. Manual sweep only,** as the Board | Board credentials, interactive only | Board must remember to sweep | [design] |
| **C. Dedicated `operator` automation user,** grants cleared, Soucean only, not instance admin, Board key with an expiry | Residual: `secrets:read`, issue mutation, runtime and decision-queue control in Soucean | Unattended; key rotation every ≤ 30 days | [source] for the rights |
| **D. Plugin job** using the host's wake capability | No Board user | New code inside Paperclip; plugin install rights unknown | Not evaluated |

**Recommendation:** Option A, with B as its fallback.
- Option C only if the Board accepts finding 2.5 as residual risk in writing.
- Option D needs its own investigation.

---

## 4. Task 3: Windows token lifecycle

### 4.1 Findings

| # | Finding | Evidence | Status |
|---|---|---|---|
| 3.1 | **Login is a challenge flow.**<br>• `POST /api/cli-auth/challenges` needs no authentication.<br>• The CLI receives a challenge secret, plus the future `pcp_board_…` key, before approval; the server stores only hashes.<br>• Approval (a signed-in Board user) activates the key, named "paperclipai cli (board)".<br>• Challenge TTL is 10 minutes. | `CLI` 25324-25386; `S\routes\access.js` 2154-2168, 2193; `S\services\board-auth.js` 6, 17-22, 221-233, 300-347 | [source]; flow seen working [sandbox] |
| 3.2 | **Expiry and renewal.**<br>• CLI login keys expire after 30 days, fixed.<br>• Named keys (`POST /api/board-api-keys`, `paperclipai token board create`) also default to 30 days, but `expiresAt: null` means **never expires**.<br>• There is no refresh. Any valid Board key can mint another one. | `S\services\board-auth.js` 5, 24, 159-180, 328; `S\routes\access.js` 2268-2302; `CLI` 68575-68590 | [source] |
| 3.3 | **Where the key is stored.**<br>• File: `PAPERCLIP_AUTH_STORE`, else `<PAPERCLIP_HOME>/auth.json`, else `%USERPROFILE%\.paperclip\auth.json`.<br>• Format: plain JSON, one `token` per API base.<br>• Written with `mode: 0o600`, which on Windows only affects the read-only attribute. Not atomic, no locking. | `CLI` 25101-25105, 25158-25159, 25203-25284 | [source] |
| 3.4 | **Who can read it.**<br>• `%USERPROFILE%\.paperclip` grants access to SYSTEM, BUILTIN\Administrators and ADMIN only.<br>• No `auth.json` exists on the studio machine today. | ACL metadata | [live-read] |
| 3.5 | **How the CLI picks a key:** `--api-key`, then `PAPERCLIP_API_KEY`, then a profile variable, then the stored credential. On an interactive terminal the CLI re-runs login after a 401 or 403 and overwrites the store. | `CLI` 56330-56375, 56416-56432 | [source] |
| 3.6 | **Expired or revoked keys** fall through to the agent-key and agent-JWT checks and return 401 "Agent token did not verify; obtain fresh credentials and retry". There is no Board-specific message. | `S\services\board-auth.js` 115-123; `S\middleware\auth.js` 48-58, 240-271 | [source] |
| 3.7 | **Revocation.**<br>• `auth logout` revokes the current key (`POST /api/cli-auth/revoke-current`; errors are ignored) and removes the local entry.<br>• `DELETE /api/board-api-keys/:keyId` works for the owner's own keys.<br>• Revocation is a soft delete (timestamp). | `CLI` 68207-68247, 25387-25396; `S\routes\access.js` 2303-2363 | [source] |
| 3.8 | **Server-side storage:** keys are SHA-256 hashed (unsalted). `lastUsedAt` is updated at most once a minute. | `S\services\board-auth.js` 9-16, 124-149 | [source] |
| 3.9 | **No OS key store support:** there is no Windows Credential Manager, DPAPI or keychain integration. | grep of `CLI` | [source] |
| 3.10 | **Commands that print a Board token:**<br>• `token board create`<br>• `auth challenge create`<br>• `connect` (prints `export PAPERCLIP_API_KEY='…'`)<br>The challenge secret also appears in the approval URL and the poll query string. | `CLI` 68262-68268, 68384-68385, 68487-68504, 68586; 25354 | [source] |
| 3.11 | `PAPERCLIP_API_KEY` is also the variable Paperclip gives agents in every run. | Agent helper scripts; Phase A | [source] |

### 4.2 Credential design [design]

| Caller | Issuance | Storage and retrieval | Expiry and rotation | Revocation | Failure behaviour |
|---|---|---|---|---|---|
| `pc.py` (interactive) | `paperclipai auth login` by the Board Operator | The CLI store in the Board's profile (finding 3.4). `pc.py` reads it through one helper, in read-only mode, checking `version: 1` and the API base. A dedicated `PAPERCLIP_BOARD_TOKEN` variable may override it. **Never `PAPERCLIP_API_KEY`** (finding 3.11) | 30 days; log in again when it expires | `paperclipai auth logout` | Missing store or key: stop and tell the user to run `paperclipai auth login`. 401: same message (finding 3.6). 403: name the missing right. Never fall back to keyless requests |
| `post-import.py`, `sync-instructions.py` | Same Board key | Same helper | Same | Same | Same; `--dry-run` still needs a key because it reads |
| Watchdog (only if option C) | A named key created by the automation user with `--ttl-days 30` (never `--never-expires`) | DPAPI-protected file or Windows Credential Manager in the account that runs the watchdog. Paperclip has neither (finding 3.9), so a small helper would be needed. Never in the `.cmd` file, arguments or logs | Rotate before 30 days; record the key id | `DELETE /api/board-api-keys/:keyId` by that user, or demote or remove the member | On 401 or 403: log once, stop, exit non-zero. No retry loop and no keyless fallback |

**Rules that apply to every caller:**
- Redact anything that looks like `pcp_` in exceptions.
- Never pass a token on the command line, which would expose it to other processes.
- Never use the token-printing commands of finding 3.10 in scripts or in agent-visible terminals.
- Agents keep their own keys. No Board token in any `adapterConfig.env` or agent environment.

**Residual risk:**
- Any process running as ADMIN, or any administrator, can read the plaintext CLI store.
- A same-user process can do the same.
- This matches today's exposure of `.paperclip` data, but the store makes it a reusable Board credential.

---

## 5. Consolidated design

### 5.1 Identity model [design]

| Identity | Used by | How it authenticates | Rights |
|---|---|---|---|
| Board Operator (the claimed user) | Browser, `pc.py`, setup scripts | Browser session; CLI-login Board key | Instance admin; `owner` of every company (from the claim) |
| `local-board` | Nobody after the switch | Cannot sign in | History only; loses instance admin at the claim |
| Automation user (only with option C) | Watchdog | Named Board key with an expiry | `operator` in Soucean, grants cleared, not instance admin |
| Agents | Agent runs | Per-run agent key or JWT (`PAPERCLIP_API_KEY`) | Unchanged |

### 5.2 Endpoint, caller, identity and permission

Unchanged from the Phase A audit §4, with these changes:
- The Board identity is the claimed user (owner and instance admin), so every Board endpoint in that table is covered.
- Watchdog endpoints follow §3.2.
- Stage decisions require the claimed user to be the stage participant (finding 1.2).

### 5.3 Failure handling [design]

| Condition | `pc.py` / setup scripts | Watchdog |
|---|---|---|
| No key | Stop; tell the user to run `paperclipai auth login` | Do not start; the launcher says why |
| 401 (expired or revoked; the message says "Agent token…") | Same as "no key" | Log once, exit |
| 403 | Show the server message and the action that needs the right | Log once, exit |
| Paperclip unreachable | Current message (start the studio) | Back off; no busy loop |
| Health OK but the auth check fails | n/a | The launcher does not start the watchdog |

### 5.4 Switch and rollback outline (to be expanded in Phase E) [design]

**Switch:**
1. Database backup.
2. Clear pending decisions (§2.2 step 1).
3. Deploy the script changes.
4. Stop Paperclip and set `deploymentMode: authenticated`.
5. Start Paperclip and sign up.
6. Claim from the console link.
7. Log in with the CLI.
8. Repoint the open issues (§2.2 step 3).
9. Verify `pc.py` read commands, then one decision on a test issue.

**Rollback:**
1. Stop Paperclip and set `deploymentMode: local_trusted`; `local-board` and its admin role come back (finding 1.10).
2. Revert the participant patches on open issues, or use the Board override.
3. Restore from the backup only if the data is damaged.

Keyless Board access is open again while in `local_trusted`, as it is today.

---

## 6. Risks and unresolved questions

| # | Item | Status | Minimum test to resolve |
|---|---|---|---|
| R1 | Board claim works on Windows and the console shows the link | Not runtime-verified | One isolated instance: start in `authenticated` with only `local-board` as admin, sign up, claim |
| R2 | A participant patch keeps an `in_review` stage active for the new user | Not runtime-verified | On that instance: one issue with a `local-board` approval stage, then the patch from §2.2 step 3 |
| R3 | Paperclip's scheduler re-wakes agent reviewers well enough to retire the watchdog | Not runtime-verified | Agent runs on a test instance; cancelled on 2026-11-20 |
| R4 | Agents still work in `authenticated` mode | Not runtime-verified | Agent runs; cancelled |
| R5 | `secrets:read` for a non-viewer member: what exactly it exposes | Not traced | Read the secrets routes for how `secrets:read` is decided |
| R6 | Plugin-based or built-in alternatives to the watchdog | Not evaluated | Source study of plugin install rights and execution monitors |
| R7 | Reading the CLI store directly depends on its internal format | Design risk | Pin to `version: 1`; recheck on every Paperclip upgrade |
| R8 | All local users can modify the workspace folder (Step 2 finding) | Open, separate from this work | Board decision |

---

## 7. Decisions for the Board

1. **Board identity:** use **board claim**, and keep `local-board` as a historical identity only. Alternative: the manual promotion in `local_trusted` (§6b), which leaves `local-board` as a second instance admin.
2. **Open stage participants:** approve the §2.2 order. Decide SOU-28 before the switch, and patch SOU-17 and SOU-30 after the claim.
3. **Watchdog:** option A (retire it, with a manual sweep as fallback), or option C (an `operator` automation user, accepting finding 2.5 in writing), or D (study plugins first).
4. **Credentials:** approve the §4.2 design, including a dedicated `PAPERCLIP_BOARD_TOKEN` variable rather than `PAPERCLIP_API_KEY`, and a 30-day Board key lifetime.
5. **Verification environment:** whether R1 and R2 may be checked on an isolated instance without agent runs, and R3 and R4 with agent runs, under the §3/§3.1 boundaries of the Step 2 decision record.

Phase B (authentication contract) and later phases need decisions 1-4 first.
