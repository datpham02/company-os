# Authentication migration, Phase B: repository work and A.5 documents

- **Status:** `IN PROGRESS`. Repository code done and tested offline. Isolated run WS-1 **passed** on 2026-11-21 (§7.1); WS-2 and WS-5 not done. No live configuration, data, credential or ACL change was made; the live Paperclip was only stopped and restarted for WS-1 (§7.1).
- **Date:** 2026-11-21. Paperclip 2026.1023.0.
- **Authorization:** Board Operator, 2026-11-21: "Authentication Migration: làm các phần còn lại" (do the remaining parts), with the decisions in §1.
- **Builds on:**
  - [auth-migration-phase-a5-plan.md](auth-migration-phase-a5-plan.md) ("A5-P"), workstreams WS-1 to WS-7;
  - [auth-migration-board-decisions.md](../roadmap/auth-migration-board-decisions.md) D-AUTH-01 to D-AUTH-05;
  - [auth-migration-phase-a5-board-decisions.md](../roadmap/auth-migration-phase-a5-board-decisions.md) D-AUTH-10 to D-AUTH-15;
  - [auth-migration-phase-a4-verification.md](auth-migration-phase-a4-verification.md) ("A4"); [auth-migration-phase-a1.md](auth-migration-phase-a1.md) ("A1").

**Still not authorized:** Phase D (the live switch), any live credential, user, role, membership, ACL or agent change, and any agent or VR run.

## 1. Board decisions of 2026-11-21

| Topic | Decision | Effect |
|---|---|---|
| A5-P §4 step 2: isolated runs WS-1, WS-2, WS-5 | **Yes, isolated only** | Authorizes those runs in a new isolated instance, never the live one. Not yet run (§7) |
| WS-7: Cursor agent policy | **Accept the risk for now** | Cursor roles (`gameplay-programmer`, `web-engineer`) keep running without an allowlist until the switch. **G-14 stays open**; this is not a G-14 acceptance (D-AUTH-15) |
| WS-4: retention of logs that contain a claim URL | **Delete after the claim** | §4 step 5 |
| Project registry | `soucean-game` marked `active` | Recorded in `knowledge/projects/registry.yaml` |

## 2. Implemented in the repository (offline-tested, no live effect)

### 2.1 Board credential (D-AUTH-04)

[`.claude/skills/paperclip/scripts/board_auth.py`](../../.claude/skills/paperclip/scripts/board_auth.py), one shared helper, used by:
- `pc.py`;
- `scripts/setup/post-import.py` and `sync-instructions.py`;
- `scripts/setup/check-agent-drift.py` and `scripts/maintenance/merge-audit.py`.

| D-AUTH-04 / A2 §3.D rule | Implementation |
|---|---|
| Board scripts read `PAPERCLIP_BOARD_TOKEN`; agents keep `PAPERCLIP_API_KEY` | `PAPERCLIP_BOARD_TOKEN` is a per-session override. `PAPERCLIP_API_KEY` is never read |
| Storage: Windows Credential Manager through `ctypes` (A2 recommendation) | Generic credential `company-os/paperclip-board` (override with `PAPERCLIP_BOARD_CREDENTIAL`), DPAPI under the user's logon. `board_auth.py store` takes the key with hidden input; `forget` deletes it |
| Fail closed; never fall back to a keyless request | In `authenticated` mode without a key the script stops with "run `paperclipai auth login` …" |
| No credential in arguments, logs or exceptions | The key is only a request header, sent only to a loopback `PAPERCLIP_URL`. `redact()` masks it, any `pcp_board_…` value and any bearer value in error text |
| 401 and 403 handled separately | 401: missing, expired or revoked, with the login hint (Paperclip's 401 text talks about agent tokens, A1 3.6). 403: the right is missing |
| Identity from `GET /api/cli-auth/me`, not `local-board` | `pc.py board_user()`, read once per process. `local-board` stays known as "Board (legacy)" in listings |
| Agents never get the Board credential | Inside an agent run (`PAPERCLIP_RUN_ID` set) the helper refuses to load it |

**Behaviour today:** the mode comes from `GET /api/health` (`deploymentMode`, readable without a credential). In `local_trusted` the helper reads no credential and sends no header, so every script behaves exactly as before. Verified live, read-only: `board_auth.py status` reports `local_trusted`, no credential, identity `local-board` (source `local_implicit`); `pc.py overview` and `check-agent-drift.py` work unchanged.

**Not changed:**
- the review watchdog. A1 §2 and D-AUTH-03R: it never gets a Board credential, and it is retired at the switch in favour of a manual Board sweep;
- the Review Package relay identity default (`review_pack.BOARD`, `--identity`). It stays `local-board` while the pilot runs in `local_trusted`. After the switch, `create --review-package` names the claimed user while the relay still defaults to `local-board`, so the relay refuses (fail closed) until `--identity` is passed or the default is changed. That change is a Phase D runbook item.

**Residual risk** (accepted by the Board in D-AUTH-06): any process running as the same Windows user, including the assistant session, can read the stored key.

### 2.2 Participant migration (D-AUTH-02)

[`scripts/maintenance/migrate-participants.py`](../../scripts/maintenance/migrate-participants.py) implements exactly the A.4-verified method:
- the dry run is the default;
- the change is a guarded `PATCH` with `executionPolicy` plus `expectedExecutionPolicy` (VA-4); a stale guard is refused with 409 (VA-4b);
- it skips a stage that already contains the target user, which would silently drop a participant (VA-4c);
- it skips an issue whose current participant is `local-board`, which Paperclip refuses with 422 (VA-5, verified for `in_review`). That one needs a Board decision before the switch (D-AUTH-02 step 1);
- an open issue that is not `backlog` and names `local-board` only in a later stage was not covered by A.4; if Paperclip refuses it, the script stops before any further change;
- after each change it re-reads the issue and stops on any difference in stage or participant ids, order, status, assignees or execution state;
- rollback is the same tool with `--from` and `--to` swapped (VA-6);
- `--apply` requires `--backup` naming an existing database backup.

**Read-only inventory today** (dry run with a placeholder target, 2026-11-21):

| Issue | Status | Plan |
|---|---|---|
| SOU-28 | `in_review`, current participant `local-board` | **Skip:** the Board decides it while still in `local_trusted` |
| SOU-30 | `backlog` | Change the approval-stage participant |
| SOU-17 | `backlog` | Change the approval-stage participant |

That matches D-AUTH-02. The inventory must be read again just before the switch.

### 2.3 Sandbox control (A5-P §4 step 2)

[`scripts/maintenance/auth-sandbox.py`](../../scripts/maintenance/auth-sandbox.py) builds and controls isolated instances and enforces the step2 §3.1 boundaries:
- each instance lives under `%USERPROFILE%\.company-os-sandbox\<name>`;
- the live ports 3100 and 54329 are never used, and `start` refuses while either is listening;
- fresh secrets per instance; telemetry, update checks and automatic backups off; no `GH_TOKEN`, no agents;
- `PAPERCLIP_*` variables of the calling shell are not passed on;
- `config.json` is written without a BOM (the A.4 VA-1 failure);
- `clone` makes the WS-1 candidate B cold copy, only from a stopped instance;
- `mode` switches `deploymentMode`, only while stopped.

Exercised on 2026-11-21 for WS-1 (§7.1). `start` also refused correctly while the live instance was listening on 3100. Fixed during the run:
- `config.json` needs `$meta.updatedAt` and `$meta.source: onboard`, or Paperclip's doctor refuses to start;
- Paperclip is started as `node <paperclipai>/dist/index.js` (a detached `cmd /c paperclipai` died at once);
- `stop` kills only the Paperclip node process, never Postgres, then runs `pg_ctl stop` if the postmaster is still alive. The embedded postmaster goes down with Paperclip anyway, so a stop is **crash-consistent**, not a clean Postgres shutdown; `stop` says which it was;
- a stale `postmaster.pid` whose process is gone counts as stopped (`clone` and `stop`).

### 2.4 Tests

| Suite | Tests |
|---|---|
| `.claude/skills/paperclip/scripts/test_board_auth.py` | 14, including an opt-in Credential Manager round trip (`BOARD_AUTH_CREDMAN_TEST=1`), run once on 2026-11-21 with a throwaway entry that was deleted again |
| `scripts/maintenance/test_migrate_participants.py` | 6 |
| `scripts/setup/test_check_agent_drift.py` | 5: a new test that only 401 and 403 stop the run; a 404 on a role file keeps its old handling |
| Existing suites (`test_pc.py` and the others) | Unchanged results; `test_pc.py` presets the identity so it stays offline |

## 3. WS-3: agent verification plan (D-AUTH-12)

A plan only. **Running it needs a separate Board authorization.** E11 stays unmet until the runs pass, or until the Board accepts migrating without them.

**Environment:** an `auth-sandbox.py` instance in `authenticated` mode, the live instance stopped, a throwaway GitHub repository, no `GH_TOKEN`.

**Prerequisites** (each a Board decision):

| # | Prerequisite | Proposal |
|---|---|---|
| P1 | Agent identity | A separate Windows user with its own Claude Code login (the A5-P preferred option); or a recorded exception to reuse the Board Operator's session |
| P2 | Repository | A new throwaway repository, deleted after the runs |
| P3 | Quota | About 4 short runs on Claude Code; 2 on Cursor if P5 is yes |
| P4 | Live instance | Stopped for the whole session (step2 §3.1) |
| P5 | Cursor agents | Included, because they are the ones without an allowlist (WS-7) |

**Cases:**

| Case | Agent | Steps | Pass | Evidence |
|---|---|---|---|---|
| VR-8a | Claude author | Release a small Task; the run reads its issue and comments, and posts a comment | The run succeeds with its per-run key; no keyless call is accepted | Run log; environment variable **names** (values redacted); wakeup and run rows |
| VR-8b | Claude reviewer | Review stage on VR-8a's Task; the reviewer records a decision | Decision recorded by the agent participant | Issue activity |
| VR-9a | Claude agent | The run tries `GET /api/companies` and a Board-only route without its key, and with its key | Keyless: 401 or 403. With the agent key: same-company read only, admin route refused | Run log; HTTP codes |
| VR-9b | Cursor agent (P5) | As VR-9a, through its shell | Same as VR-9a. Also: the run cannot read the Board credential (Credential Manager entry absent under the agent's identity) | Run log |

**Stop conditions:**
- any request reaches port 3100;
- any path outside the throwaway repository and the sandbox is touched;
- a Board credential is visible to an agent;
- P1 is not met.

## 4. WS-4: claim-URL handling procedure (D-AUTH-13)

This goes into the Phase D runbook unchanged.

1. **Before the switch:** confirm that the instance folder, logs included, grants only SYSTEM, Administrators and the Board Operator (read-only `Get-Acl` on `%USERPROFILE%\.paperclip`).
2. **Reading the link:**
   - the Board Operator reads the claim link from the Paperclip console personally;
   - it is never pasted into chat, tickets or the assistant;
   - the assistant never reads the raw link from the console or a log, and never prints log lines that could contain it.
3. **Window:** claim straight after the switch. The link expires after 24 hours.
4. **Confirm:**
   - the Board Operator checks the status `claimed` (`GET /api/board-claim/<token>`, the only check that needs the token);
   - the assistant checks only through `GET /api/cli-auth/me`, which needs the Board credential, not the token.
5. **Retention (Board, 2026-11-21): delete after the claim.**
   - Once the claim is confirmed, stop Paperclip, delete the server log files written during the migration window, and start again.
   - Logs are never edited in place.
   - Whether a used claim token has any further value is unverified; until then it is treated as sensitive.
6. **Found anywhere else** (chat, a ticket, a file): claim immediately, then record where it was found.
7. **Upstream:** report SF-1 (claim URL at INFO in the request log) to Paperclip; optional.

## 5. WS-5: explicit membership roles (D-AUTH-14)

**Rule for every script and runbook:** a provisioning step names the role and a verification.

| Role | Use |
|---|---|
| `viewer` | Read-only humans and any read-only automation |
| `operator` | Only a user who must wake agents or edit company issues; every grant reviewed |
| `admin`, `owner` | The Board Operator only |
| Instance admin | The claimed Board user only (WS-2) |

**Provisioning order:**
1. Prefer a company invite with an explicit `humanRole`.
2. If `PUT /api/admin/users/:id/company-access` must be used, follow it **in the same step** with `PATCH /api/companies/:id/members/:memberId` to the intended role. The brief `operator` window is a known exposure.
3. Verify with `GET /api/companies/:id/members`. Stop if the role differs.

**Current scripts:** none provisions users or memberships, so nothing relies on the default. A future provisioning script must follow this rule.

**Isolated invite test** (authorized, not yet run): one sandbox company; an invite with `humanRole: viewer`; the Board Operator signs up a second sandbox account in a browser and accepts it. **Pass:** the membership is `viewer` from its first read, with no `operator` state in the activity. Evidence: the invite response (token redacted), the membership read, the activity rows.

## 6. WS-6: R8 account inventory method (D-AUTH-15)

Read-only. Nothing here changes an ACL. The ACL change itself needs its own approval.

1. **Current ACL:** `Get-Acl <workspace> | Format-List` and `icacls <workspace>`. Record the entries for `Authenticated Users` and `Users`.
2. **Local accounts:** `Get-LocalUser | Where-Object Enabled`. Each enabled account besides the Board Operator is a reader today.
3. **Services and tasks that may need the folder:**
   - `Get-ScheduledTask` whose actions mention the workspace;
   - services running as other accounts (`Get-CimInstance Win32_Service`, `StartName` not LocalSystem and not the Board Operator);
   - container engine or WSL mounts (Docker Desktop file sharing);
   - IDE helpers that run as another account.
4. **Record** the inventory in the R8 decision request, with option A (tighten the ACL) or B (move the repositories into the profile), and the rollback (`icacls … /save` before, `/restore` after).

## 7. Isolated runs: status

| Run | Status | Needs |
|---|---|---|
| WS-1 restore, candidate B (cold copy of the stopped instance folder) | **Passed** (§7.1). E8 still needs the Board's acceptance of this unsupported method | — |
| WS-2 demotion sequence (migrate → rollback → demote → re-migrate) | **Not run** | The live Paperclip stopped (as for WS-1), plus the Board Operator in a browser for the sandbox sign-up and claim |
| WS-5 invite path | **Not run** | As WS-2, plus a second sandbox account |

### 7.1 WS-1 result (2026-11-21)

**Authorization:** the Board's yes to isolated runs (§1), and "Yes, run WS-1" on 2026-11-21, which included stopping the live instance.

**Live handling:**
- Before the stop, all 8 agents were idle.
- The live Paperclip process tree was stopped, and ports 3100 and 54329 were confirmed free. Its Postgres went down uncleanly, as in A.4.
- After teardown, the studio was restarted with the unchanged `start-studio.cmd`. Checked:
  - health `ok` in `local_trusted`;
  - the same 8 agents, all idle;
  - the same open issues (SOU-17, SOU-20, SOU-28, SOU-30);
  - the same 2 known drift findings (P4-T01, not applied);
  - the review watchdog running.
- No live configuration, data or credential was touched.
- The old Paperclip console window stays open with its process ended; `start-studio.cmd` opened a new one. The old one can be closed.

**Steps and results:**

| Step | Result |
|---|---|
| Source `ws1src` (ports 3300 and 54349, `local_trusted`, fresh secrets) | Started; ports 3100 and 54329 stayed closed |
| Seed | Company `WSR`: WSR-1 `backlog` with an approval stage for `local-board` (AVE-1); WSR-2 `in_review`, approval pending (AVE-2); WSR-3 approved by `local-board`, now `done` with the stage `completed` (AVE-3); 4 comments; 1 dummy secret; 13 activity rows |
| Snapshot S1 | Companies; full issues (policy, state, assignees, timestamps); comments; memberships; secret metadata; activity rows (id, action, entity, time); `/cli-auth/me`; master-key hash |
| Unclean stop, restart, snapshot S2 | **Identical to S1**: data survived a crash-stop with WAL recovery |
| Stop (crash-consistent), cold copy to `ws1dst` (ports 3301 and 54350; paths and ports rewritten in `config.json`), start | Healthy start, `local_trusted`, 2026.1023.0 |
| Snapshot S3 on the copy | **Identical to S1**: 1 company, 3 issues (WSR-3 still `done`, stage `completed`), 4 comments, 1 membership, 1 secret, all 13 activity rows, the same instance-admin identity, the same master key |
| Write test on the copy | WSR-2 approved (`done`, stage `completed`) and a comment added: the copy is fully writable |
| Teardown | Both instances stopped and deleted; no sandbox port or Postgres process left |

**What this shows:** a cold copy of a stopped instance folder brings back a working instance with identical data. The copy is crash-consistent; the live studio is also always stopped that way. It meets the E8 test condition, "a restore into the test environment succeeds".

**Limits:**
- the method is **not Paperclip-supported**;
- Postgres was never shut down cleanly from outside on Windows (it goes down with Paperclip), so recovery relies on WAL replay;
- secret values were not decrypted after the copy: only the metadata and the master key file were compared;
- decision rows were not read directly (2026.1023.0 has no decision-history endpoint). The approval shows only as WSR-3's state and its `issue.updated` activity; the copy is byte for byte, so the rows travel with it, but that was not observed through the API;
- the test was small (one company, three issues). Object storage was copied with the folder but held no files.

**Board decision needed:** accept candidate B as the restore method, which turns E8 to met. Proposed procedure for the live instance, for the Phase D runbook:
1. Stop Paperclip.
2. Copy `%USERPROFILE%\.paperclip\instances\default` to a dated folder in the profile.
3. Start Paperclip again.
4. To roll back: stop Paperclip, move the damaged folder aside, put the copy back, and start Paperclip.

### 7.2 Procedure (as run for WS-1; reused for WS-2 and WS-5)
1. Stop the live Paperclip and confirm ports 3100 and 54329 are free.
2. Build the sandbox: `auth-sandbox.py init ws1src --port 3300 --pg-port 54349`, then `start`.
3. Seed and snapshot through the API:
   - a company;
   - issues in the AVE-1, AVE-2 and AVE-3 shapes;
   - a comment and a dummy secret;
   - a snapshot of companies, issues, policies and states, comments, memberships, secret metadata, the activity count and the master-key hash.
4. `stop`, then `clone ws1src ws1dst --port 3301 --pg-port 54350`, then `start ws1dst`. Take the same snapshot and compare.
5. **Pass** (E8 condition): identical snapshots and a healthy start.
6. Candidate A (dump plus restore) needs PostgreSQL 18 client tools, which is a separate Board decision ([auth-migration-ws1-restore-research.md](auth-migration-ws1-restore-research.md)).
7. Even with a pass, the Board must accept the unsupported method before E8 counts as met.
8. `teardown` both instances; restart the studio with `start-studio.cmd`; check health, the 8 agents and the open issues.

## 8. Readiness

| Criterion | State |
|---|---|
| Scripts send `Authorization` (A2 blocker "Phase B work") | **Done in code**, tested offline; exercised live only in `local_trusted` |
| Credential storage | Implemented as A2 recommended; issuing and storing the real key is the Board Operator's step at the switch |
| Participant migration | Tool ready; the method was verified in A.4; SOU-28 must be decided first |
| E8 (restore) | **Test passed** (WS-1, §7.1). Counts as met once the Board accepts candidate B |
| E11 (agents in `authenticated` mode) | **Not met.** WS-3 plan awaits approval |
| E12 (R8, G-14) | **Not met.** WS-6 inventory method written; G-14 open; Cursor risk accepted for now |
| VA-8 (dual admin) | WS-2 not run |

Phase D stays not authorized and needs a go/no-go immediately before execution.
