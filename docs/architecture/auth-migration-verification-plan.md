# Authentication migration: verification plan

- **Status:** `PROPOSED`. Nothing in this plan has been run.
- **No test runs without its own approval:**
  - Creating the environment needs Board approval. D-AUTH-05 approves planning, not creation.
  - Every `VR` case runs agents, which needs a separate, explicit Board approval.
- **Date:** 2026-11-20. Paperclip 2026.1023.0.
- **Read with:** [auth-migration-phase-a2-readiness.md](auth-migration-phase-a2-readiness.md) (cited as "A2") and [auth-migration-phase-a1.md](auth-migration-phase-a1.md) (cited as "A1").

## 1. Sandbox and live verification are separate

| Where | What | Authorization |
|---|---|---|
| **Isolated test instance** (this plan) | All VA and VR cases | Environment creation: Board approval (A2 E4). VR cases: separate agent-run approval |
| **Live studio instance** | Only GET re-reads before the migration (A2 §3.B step 3), and the migration itself in Phase E | Phase E approval. Never as a test |

No case below may touch the live instance, its data folder, credentials, workspace or agents.

## 2. Test environment

**Boundaries:** those of [step2-board-decisions.md](../roadmap/step2-board-decisions.md) §3 and §3.1 apply:
- the live Paperclip is stopped and port 3100 is confirmed free;
- the test instance uses its own home folder, instance id, port and Postgres port, and fresh secrets;
- telemetry and backups are off;
- no `GH_TOKEN` and no production secrets.

**Seed data:** created through the API in the test instance:
- one company;
- for VR cases only, two `claude_local` agents ("author" and "reviewer") using a throwaway repository, and only after the agent-run approval;
- issues with a review or approval stage that names `local-board`.

**The instance must start in `local_trusted`,** so that `local-board` exists as the only instance admin (`S\index.js` 207-255). Then it is switched. That is the precondition for the claim (A1 1.9).

**Identity:** the Board Operator signs up and approves in a browser. No password or token is typed by the assistant.

**Evidence collection:**
- JSON responses saved with tokens redacted (`pcp_…` replaced);
- the server console log, for the claim link and wake warnings;
- issue activity from the API;
- for VR cases, wakeup and run rows from the API.

If a needed row (for example `agent_wakeup_requests`) has no API route, a read-only database query through the embedded Postgres may be used. Its method is decided when the environment is approved.

**Teardown:** stop every test process, delete the test folder, confirm the ports are closed, then restart the live instance. Record each step.

## 3. Cases without agents (VA)

| ID | Purpose | Preconditions | Trigger | Expected | Evidence | Failure criteria |
|---|---|---|---|---|---|---|
| VA-1 | `authenticated` mode and keyless refusal | Test instance switched to `authenticated` | Keyless GET and POST to company, issue and admin routes | 403 "Board access required" / 401 on admin routes; `GET /health` 200 | Saved responses | Any keyless 2xx except health |
| VA-2 | Board claim (D-AUTH-01) | `local-board` is the only instance admin; switched to `authenticated`; server restarted | Read the claim link from the console; the Board Operator signs up and opens it | Claimer becomes instance admin and `owner` of every company; `local-board` loses `instance_admin` | Console line; `GET /api/admin/users`; `GET /api/cli-auth/me` | No link printed; claim refused; `local-board` still admin; memberships missing |
| VA-3 | Identity through `/api/cli-auth/me` (D-AUTH-04) | VA-2 done; `paperclipai auth login` with `PAPERCLIP_AUTH_STORE` set to the test folder | Call `/api/cli-auth/me` with the stored key | Returns the claimed user id; no token in the output | Redacted response | Wrong user, or the token appears in output |
| VA-4 | Participant update, case (a) (D-AUTH-02) | Issue in `backlog` with an approval stage whose participant is `local-board` | Guarded policy-only PATCH replacing only `userId` (A2 §3.B step 5) | 200; same stage and participant ids and order; `executionState` null; status and assignee unchanged; `issue.approvers_updated` logged; no decision row | Before and after GET; activity list | Any id change, a state change, or a dropped stage |
| VA-4b | Guard mismatch | As VA-4 | Same PATCH with a stale `expectedExecutionPolicy` | 409 `execution_policy_changed`; nothing written | Response; GET | Write succeeds |
| VA-4c | Deduplication trap | Stage already contains the new user | Same PATCH | The edited entry is dropped (A2 §3.B); recorded as a known hazard | Before and after GET | (Documents behaviour; the procedure must pre-check) |
| VA-5 | Participant update, case (b) | Issue `in_review`, active approval stage held by `local-board` | The guarded PATCH | 422 "Snapshot-guarded policy updates cannot change task status or ownership"; nothing written | Response; GET | Any write |
| VA-6 | Rollback of case (a) | VA-4 done | Reverse guarded PATCH back to `local-board` | 200; original policy restored exactly | GET compared with the first snapshot | Any difference |
| VA-7 | Expired, revoked and forbidden tokens | VA-3 done; a second user with role `viewer` | (1) revoke the key and call `/api/companies`; (2) the viewer key on a POST | (1) 401, with the agent-token message (A1 3.6); (2) 403 "Viewer access is read-only" | Responses | Other codes, or the token appears in a message |
| VA-8 | Mode rollback | VA-2 done | Stop; set `local_trusted`; start | `local-board` re-created with admin; keyless Board works again; claimed user still exists; data intact | `GET /api/admin/users`; company and issue counts | Data loss, or no Board access |
| VA-9 | Backup and restore (OQ-025) | Test data present | `POST /api/instance/database-backups`; restore into a second test folder using Paperclip's supported method (to be identified first) | Restored instance shows the same companies, issues and decisions | Counts and sample comparisons | Restore fails or differs |

## 4. Cases with agents (VR): need separate agent-run approval

| ID | Purpose | Preconditions | Trigger | Expected per source (A2 §3.C) | Evidence | Failure criteria |
|---|---|---|---|---|---|---|
| VR-1 | OQ-035: reviewer wake after an in-run hand-off | Author agent assigned; review stage with the reviewer agent; **no** custom watchdog | The author sets its issue to `done` from inside its run | The `execution_review_requested` wake is created. If it is lost, the sweeper **skips** the issue on every tick (source); the issue stays `in_review` | Wakeup rows for the reviewer (status, reason); run list; server log line "failed to wake agent on issue update" | A reviewer run starts on its own (contradicts source; record it) |
| VR-2 | Stranded reviewer with a terminal previous run | The reviewer has a finished run on the issue; issue `in_review` with no active run | Wait two scheduler ticks (≤ 60 s) | Re-dispatch with reason `execution_review_participant_recovery` | Wakeup and run rows | No re-dispatch after 2 ticks |
| VR-3 | Silent work | A running agent run with no output for more than 5 minutes | Wait | Reported at 5 and 15 minutes; no automatic change | Server log; run evaluation | Run killed, or nothing reported |
| VR-4 | Blocked issue | Issue `blocked` by another issue | (1) leave it; (2) resolve the blocker | (1) not swept; (2) woken once by the dependency backstop | Wakeup rows | Swept while blocked, or no wake after resolve |
| VR-5 | Scheduler restart | Situation of VR-1 and VR-2 in place | Restart the test instance | Startup pass applies the same rules: VR-1 still skipped, VR-2 re-dispatched | Wakeup rows after restart | Different behaviour from VR-1 and VR-2 |
| VR-6 | Several reviewers | Review stage with two agent participants | Hand-off | Only the first eligible participant is woken | Wakeup rows | Both woken, or the wrong one |
| VR-7 | Duplicate wakes | VR-1 situation; manual sweep run twice | Run the proposed manual sweep twice | The server does not de-duplicate manual Board wakes, so the sweep must check for an existing queued or running run itself; at most one reviewer run | Run list | Two reviewer runs |
| VR-8 | Agents in `authenticated` mode | VA-2 done; agents configured | One agent task through `paperclip-issue-update.sh`, an artifact upload and an MCP read | All succeed with per-run keys; no Board credential in the agent environment | Run logs; agent environment listing with values redacted | Any failure, or a Board token visible to the agent |
| VR-9 | G-14 from an agent run | `local_trusted`; Claude profile without `Bash(curl *)` | The agent attempts `curl http://127.0.0.1:<test port>/api/companies` | Refused by Claude Code's permission layer | Run log | The command runs |

## 5. Rollback considerations

- Every case runs only on the test instance; rolling back means tearing it down (§2).
- **Per-case undo:**
  - VA-6 is the undo for VA-4.
  - VA-8 is the mode rollback.
  - VA-9 proves the restore path that the real migration needs.
- **Results feed Phase E:** the real migration's rollback (A1 §5.4) is not approved until VA-6, VA-8 and VA-9 pass.

## 6. Exit and report

Each run produces a record in the style of `step2-board-decisions.md` §6a and §6b:
- authorization;
- environment;
- per-case result and evidence;
- failures;
- teardown.

Any failed case stops the plan, and the result returns to the Board.
