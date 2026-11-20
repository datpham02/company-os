# Board Decision Package — Authentication Migration, Phase A.3 (re-decision)

**Date:** 2026-11-20
**Status:** All seven decisions approved as recommended (Board Operator, in chat, 2026-11-20). **No implementation is authorized:** every "Implementation authorization" field stays Pending.
**Scope:** the open points that Phase A.2 sends back to the Board.
**Authority:** Board Operator

**Inputs:**
- [auth-migration-phase-a2-readiness.md](../architecture/auth-migration-phase-a2-readiness.md), cited as "A2";
- [auth-migration-verification-plan.md](../architecture/auth-migration-verification-plan.md), cited as "VP";
- [auth-migration-board-decisions.md](auth-migration-board-decisions.md) (D-AUTH-01 to D-AUTH-05);
- [auth-migration-phase-a1.md](../architecture/auth-migration-phase-a1.md), cited as "A1";
- the Phase A audit: [auth-migration-phase-a-audit.md](../architecture/auth-migration-phase-a-audit.md) (added under D-AUTH-08; §4).

**Rules for this package:**
- An approval here is a design decision. Implementation and runtime work each have their own "Implementation authorization" field, which stays empty until the Board fills it.
- D-AUTH-01, D-AUTH-02, D-AUTH-04 and D-AUTH-05 stay as approved.
- **D-AUTH-03 is under reconsideration.** Its approval stays in the record, but its condition is not met (§1).

**Follow-up:** the open points of the Phase A.4 report were decided in [auth-migration-phase-a5-board-decisions.md](auth-migration-phase-a5-board-decisions.md) (D-AUTH-10 to D-AUTH-15). The decisions below are unchanged.

## Summary

| ID | Question | Recommendation | Approval | Implementation authorization |
|---|---|---|---|---|
| D-AUTH-03R | Reviewer wake strategy | A: manual Board sweep after migration | Approved: option A | Pending |
| D-AUTH-06 | Board credential storage | Windows Credential Manager, with the mitigations in §2 | Approved: Credential Manager; residual risks accepted | Pending |
| D-AUTH-07a | Create an isolated verification environment | Approve | Approved | Pending |
| D-AUTH-07b | Run the VA cases (no agents) | Approve | Approved | Pending |
| D-AUTH-07c | Run the VR cases (agents) | Defer | Approved: deferred (no VR case is authorized) | Pending |
| D-AUTH-08 | Commit the Phase A to A.3 records | Approve | Approved | Authorized 2026-11-20: branch, commits, PR (no merge) |
| D-AUTH-09 | Board stage freeze around the claim | Approve | Approved | Pending |

---

## 1. D-AUTH-03R — Reviewer wake strategy

### Background and evidence

**What D-AUTH-03 approved.** On 2026-11-20 the Board approved retiring the custom watchdog **if** Paperclip's built-in scheduler reliably recovers reviewer wakeups. The fallback was a manual Board sweep, with no Board credential for the watchdog and no automation user.

**Why the condition fails** (source, Paperclip 2026.1023.0; A2 §3.C):
1. On a stage hand-off the server sends the reviewer one wake, `execution_review_requested`. It is fire-and-forget and never retried. It can be skipped, deferred or lost without anyone noticing; a thrown error leaves only the log line "failed to wake agent on issue update" (`routes/issues.js` 1667-1712, 11358-11393).
2. The scheduler's sweeper, `reconcileStrandedAssignedIssues`, does select `in_review` issues (`services/recovery/service.js` 2938-2944).
3. But for an `in_review` issue whose reviewer has **no run on the issue**, or only a non-terminal run, it does nothing: the issue is counted as `skipped`. The only exception is a reviewer agent that cannot be invoked, which is escalated (`service.js` 3412-3440):
   ```
   if (!participantLatestRun || !isTerminalIssueRun(participantLatestRun)) {
       if (!agentInvokable) { ...escalate... } else { result.skipped += 1; }
       continue;
   ```
4. This happens on every 30-second tick and on the startup pass. The OQ-035 case (a reviewer never woken after an in-run hand-off) is therefore never recovered.
5. The sweeper does re-dispatch a reviewer whose **previous** run on the issue is terminal. That is a different case.

These conclusions come from source only, not runtime. Which branch dropped the original wake on 2026-11-04 is unknown (OQ-035).

**Effect on the live studio.**
- The live watchdog is untouched and keeps working while the instance stays in `local_trusted`.
- After a switch to `authenticated`, it would fail on every sweep (403), because D-AUTH-03 gives it no credential.

### Options

| Option | What it means | Security | Operation | Unknowns |
|---|---|---|---|---|
| **A. Manual Board sweep** (recommended) | A `pc.py` command (Phase B) runs the watchdog's logic as the Board. It is run by hand, for example after each hand-off or during daily triage. The watchdog is retired at the switch | No new identity, no unattended credential | A review can wait until someone sweeps. The sweep must check for an existing queued or running reviewer run, because the server does not de-duplicate manual wakes (A2 §3.C) | None structural |
| **B. Watchdog with a dedicated credential** | An automation user: role `operator`, all grants cleared, Soucean only, not instance admin, Board key with a 30-day expiry, stored per D-AUTH-06 | Accepts A1 §3: even with grants cleared the user can still perform `secrets:read` and `runtime:manage`, change and comment on any Soucean issue, and manage decision queues. Mitigations: a separate Windows account for the watchdog, key rotation, review of that user's activity log, and revocation on any anomaly | Unattended, as today | Each mitigation needs its own setup and review. Reverses D-AUTH-03's "no credential, no automation user" |
| **C. Investigate plugins first** | Study the plugin host's wake capabilities (`issues.wakeup`, `agents.invoke`) and the built-in issue watchdog and monitors (A1 2.10) | Possibly no Board user at all | Delays the decision; may need custom code inside Paperclip | Plugin install rights, maintenance across Paperclip upgrades |

### Recommendation and trade-offs

**A.** It keeps D-AUTH-03's security conditions (no credential, no automation user) and replaces only the premise that turned out false.

**Cost:** review latency depends on the Board's routine. Agents that hand off to reviewers will sometimes wait.

**Precondition:** the sweep command must exist and be tested before the switch.

### Fields

- **Approval:** Approved 2026-11-20 (Board Operator, in chat: "duyệt hết", read as approval of every recommendation): **option A**, manual Board sweep after migration. This supersedes D-AUTH-03's premise; its security conditions (no Board credential for the watchdog, no automation user) stay in force.
- **Implementation authorization:** Pending. Building the sweep command is Phase B work, and Phase B is blocked.
- **Preconditions:** none for the decision. Implementing A needs the Phase B credential helper (D-AUTH-06).
- **If deferred:** the switch to `authenticated` cannot happen without losing reviewer recovery. Phase B entry criterion E2 stays unmet.

---

## 2. D-AUTH-06 — Board credential storage

### Background and evidence

**Approved under D-AUTH-04:** Board scripts read `PAPERCLIP_BOARD_TOKEN`; agents keep `PAPERCLIP_API_KEY`; the identity comes from `/api/cli-auth/me`; failures are fail-closed; 401 and 403 are handled separately. The storage design was left for security review.

**What Paperclip offers** (source, A1 3.1-3.11; A2 §3.D):
- The CLI keeps Board keys in `%USERPROFILE%\.paperclip\auth.json` as **plaintext**.
- Writes are not atomic and not locked. The file's `0o600` mode has no effect on Windows.
- Keys last 30 days, with no refresh.
- There is no OS key-store support.
- Some CLI commands print tokens.

### Options

| Option | Protection | Rotation | Notes |
|---|---|---|---|
| CLI store `auth.json` | Folder ACL only (SYSTEM, Administrators, the user); plaintext | `paperclipai auth login` every 30 days | Depends on Paperclip's internal file format |
| `PAPERCLIP_BOARD_TOKEN` per session only | Process environment | Manual | Easy to leak through shell history or child processes |
| **Windows Credential Manager** (recommended) | DPAPI under the user's logon; not plaintext on disk | Re-issue, overwrite, revoke the old key id | Needs a small helper (`ctypes`) and an issuance step that stores the key without printing it |
| DPAPI-encrypted file | Same as Credential Manager | Same | Same effort; one more file to manage |

### The Claude Code risk (stated explicitly)

`pc.py` is run by Claude Code on the Board Operator's behalf, as the Board Operator's Windows user. Whatever `pc.py` can read, that Claude Code session can also read and use: Credential Manager, DPAPI, environment variables and the CLI store alike. The session is not a Paperclip agent, but it is an automated process. With the Board key it can approve, reassign, cancel and change Paperclip state as the Board, and, because the claimed Board user is instance admin and owner (D-AUTH-01), administer the instance.

**Practical mitigations** (proposed, for Phase B design):
1. **Never issue the key through the assistant.** The Board Operator runs the issuance (`paperclipai auth login` plus a store step) in their own terminal, so the key never appears in a Claude Code transcript.
2. **Short lifetime.** Use the CLI-login key (30 days, fixed). Revoke it with `paperclipai auth logout` at the end of a work period if desired; never use `--never-expires`.
3. **Confirmation on writes.** Keep Claude Code's permission prompts for `pc.py` write commands (`release`, `approve`, `request-changes`, `cancel`, `assign`, `create`, `wake`, `comment`) so each write needs the Board Operator's approval. Read commands can stay unprompted.
4. **Optional: a read-only key** for routine reads (`overview`, `show`, `triage`). That needs a second user with role `viewer` and separate storage. Decisions would then need the owner key, issued only when needed.
5. **Audit.** Paperclip records the key id on Board activity (A1 3.8). Review `board_api_key.*` and decision activity periodically.
6. **No token in output.** The helper redacts `pcp_…`, and `pc.py` never prints the key or passes it as an argument.

**Residual risks:**
- Any process running as the Board Operator's Windows user, and any administrator, can use the key while it is valid.
- Credential Manager protects the key at rest from other users. It does not protect against the same user.
- If option 4 is not used, every assistant session that runs `pc.py` holds instance-admin power.

### Recommendation and trade-offs

**Windows Credential Manager,** with mitigations 1, 2, 3, 5 and 6. Mitigation 4 is optional.

**Trade-off:** more setup than reading `auth.json`, but no plaintext key on disk and no dependence on Paperclip's internal format. The Claude Code risk is reduced by prompts and short key lifetime, not removed.

### Fields

- **Approval:** Approved 2026-11-20 (Board Operator, in chat: "duyệt hết", read as approval of every recommendation): **Windows Credential Manager** with mitigations 1, 2, 3, 5 and 6 (4 optional). The residual risks stated above, including the Claude Code risk, are accepted.
- **Implementation authorization:** Pending (Phase B).
- **Preconditions:** none for the decision.
- **If deferred:** Phase B cannot design the credential helper. Entry criterion E3 stays unmet.

---

## 3. D-AUTH-07 — Verification environment and scope

These are three separate decisions. D-AUTH-05 approved planning only; it does not create anything (D-AUTH-05 boundaries).

### D-AUTH-07a — Create an isolated verification environment

**What it is:**
- A new Paperclip instance with its own home folder, instance id, port and Postgres port, and fresh secrets.
- Telemetry and backups off; no `GH_TOKEN` and no production secrets.
- It starts in `local_trusted` so that `local-board` exists (VP §2).

**Risks:**
- Loopback collision with the live instance: the live Paperclip must be stopped for the duration, which means studio downtime.
- The Board Operator's test account is stored in the test instance. Use a non-personal email.
- The test folder sits under a path all local users can read, unless it is placed in the Board Operator's profile (R8).

**Cleanup requirements:**
- Stop every test process; delete the test folder; confirm the ports are closed.
- Restart the live instance and confirm health and agent states.
- Record each step, as in the step2-board-decisions §6b style.

**Approval:** Approved 2026-11-20 (Board Operator, in chat: "duyệt hết", read as approval of every recommendation). **Implementation authorization:** Pending.

### D-AUTH-07b — Run the VA cases (no agents)

**Cases** (VP §3):

| Case | Checks |
|---|---|
| VA-1 | Keyless refusal |
| VA-2 | Board claim |
| VA-3 | `/cli-auth/me` |
| VA-4, VA-4b, VA-4c | Participant update: case (a), guard mismatch, deduplication trap |
| VA-5 | Participant update, case (b): refusal |
| VA-6 | Participant rollback |
| VA-7 | 401 and 403 |
| VA-8 | Mode rollback |
| VA-9 | Backup and restore |

**Risks:**
- The Board Operator signs up and approves in the test instance.
- The VA-9 restore method must be identified first; if Paperclip has none, VA-9 is reported as not possible.
- No agent runs.

**Approval:** Approved 2026-11-20 (Board Operator, in chat: "duyệt hết", read as approval of every recommendation). **Implementation authorization:** Pending. **Requires D-AUTH-07a.**

### D-AUTH-07c — Run the VR cases (agents)

**Cases** (VP §4):

| Case | Checks |
|---|---|
| VR-1 | OQ-035 |
| VR-2 | Stranded reviewer with a terminal run |
| VR-3 | Silent run |
| VR-4 | Blocked issue |
| VR-5 | Restart |
| VR-6 | Several reviewers |
| VR-7 | Duplicate wakes |
| VR-8 | Agents in `authenticated` mode |
| VR-9 | G-14 from an agent run |

**Risks:**
- Agents run with a Claude Code identity. The separate Windows user approach was cancelled on 2026-11-20 (step2-board-decisions §6b), so an identity decision is needed again: a separate user, or a recorded exception to reuse the Board Operator's session.
- Agent runs use provider quota.
- VR-1 is expected, from source, to show the reviewer never woken. Running it only confirms that.

**Recommendation:** **defer.**
- D-AUTH-03R option A does not need VR-1.
- VR-8 and VR-9 matter for the final switch and can be decided later (Phase B criterion E11).

**Approval:** Approved 2026-11-20 (Board Operator, in chat: "duyệt hết", read as approval of every recommendation): the VR cases are **deferred**; none is authorized. **Implementation authorization:** Pending. **Requires D-AUTH-07a and an identity decision.**

### If deferred

- **07a and 07b:** criteria E5 to E9 (claim, participants, identity, restore, rollback) stay unverified, and Phase B stays blocked.
- **07c:** criterion E11 must later be met or explicitly accepted.

---

## 4. D-AUTH-08 — Documentation commits and traceability

### Uncommitted records

All are in the working tree of `docs/sandbox-cancel-accuracy`, which has the same content as `main` `78341b1`.

| Record | Location | State |
|---|---|---|
| Phase A audit | Outside the repository: a session scratch file, `phase-a-auth-migration-audit.md` (11,719 bytes, 2026-11-20). Temporary storage, may be deleted | **Not in the repository** |
| Phase A.1 report | `docs/architecture/auth-migration-phase-a1.md` | Untracked |
| D-AUTH decision record | `docs/roadmap/auth-migration-board-decisions.md` | Untracked |
| Phase A.2 readiness | `docs/architecture/auth-migration-phase-a2-readiness.md` | Untracked |
| Verification plan | `docs/architecture/auth-migration-verification-plan.md` | Untracked |
| This package | `docs/roadmap/auth-migration-phase-a3-board-decisions.md` | Untracked |
| OQ updates (OQ-025, OQ-035, OQ-043) | `docs/roadmap/open-questions.md` | Modified |
| Log entries (decisions, A.2, A.3) | `docs/roadmap/autonomous-execution-log.md` | Modified |

### Proposed grouping

One new branch from `main` and one pull request. Four commits, in order, so that each phase is traceable:
1. **Phase A audit:** add the audit as `docs/architecture/auth-migration-phase-a-audit.md`, unchanged apart from a header line giving its origin and date.
2. **Phase A.1 and D-AUTH decisions:** the A.1 report, the decision record, the OQ-043 decision line and the log entry.
3. **Phase A.2:** the readiness assessment, the verification plan, the OQ-025, OQ-035 and OQ-043 updates, and the log entry.
4. **Phase A.3:** this package, the D-AUTH-03 reconsideration note and the log entry.

The OQ and log edits of different phases are mixed in the working tree. They would be split into commits by applying them in order with non-interactive patch files.

**Traceability:**
- Each record names its inputs.
- A1 cites the Phase A audit by file name, which then exists in the repository.
- The verification records of 07a and 07b, when they exist, follow in later pull requests.

### Fields

- **Approval:** Approved 2026-11-20 (Board Operator, in chat: "duyệt hết", read as approval of every recommendation).
- **Implementation authorization:** Authorized 2026-11-20 (Board Operator, in chat: "Yes, commit and PR"): create the branch, commit, push and open the PR. Merging stays with the Board.
- **If deferred:** the Phase A audit may be lost with the session's temporary storage. Entry criterion E10 stays unmet.

---

## 5. D-AUTH-09 — Board stage freeze

### Background

- D-AUTH-02 repoints `local-board` participants after the claim.
- The guarded update works only on issues without an active stage (A2 §3.B).
- An issue that gains a `local-board` approval stage **after** the final inventory either is missed by the repoint or becomes active before the switch. It can then not be decided after the switch, except through a Board override that writes no decision row, which D-AUTH-02's invariants forbid.
- `pc.py create` adds a `local-board` approval stage by default (`--no-approval` skips it). The UI can do the same.
- Agent-created tasks (MCP `create_task`) get no execution policy (G-10), so they are not affected.

### Proposal

| Element | Definition |
|---|---|
| **Start** | When the Board Operator orders the final participant inventory (A2 §3.B step 3), at the beginning of the migration window |
| **End** | When the claim is done **and** every inventoried issue has been repointed and re-read (A2 §3.B step 5) |
| **Owner** | Board Operator. The assistant refuses `pc.py create` without `--no-approval` while the freeze is on |
| **In force** | No new issue with a Board approval or review stage naming `local-board`, created by `pc.py create` or the UI. No policy edit that adds `local-board`. No moving an issue with a `local-board` stage into `in_review` |
| **Exceptions** | Urgent work: create the issue with `--no-approval` and add the Board stage after the freeze. Otherwise, add the issue to the inventory and re-read before the switch. Any exception is recorded in the migration record |
| **If something slips through** | Stop the migration, decide the issue in `local_trusted`, re-run the inventory, then continue |

### Fields

- **Approval:** Approved 2026-11-20 (Board Operator, in chat: "duyệt hết", read as approval of every recommendation).
- **Implementation authorization:** Pending. The freeze takes effect only inside an authorized migration window.
- **Preconditions:** a migration window authorized under Phase E.
- **If deferred:** risk of a stage that cannot be decided after the switch.

---

## 6. Phase B

Approving any decision in this package does not authorize Phase B. Phase B stays blocked under A2 §5 (E1 to E12).
