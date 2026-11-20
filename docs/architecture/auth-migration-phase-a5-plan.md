# Authentication migration, Phase A.5: plan

- **Status:** `PROPOSED`. A planning document only. Nothing here is implemented, and nothing here authorizes implementation.
- **Date:** 2026-11-20. Paperclip 2026.1023.0.
- **Decisions:** [auth-migration-phase-a5-board-decisions.md](../roadmap/auth-migration-phase-a5-board-decisions.md), D-AUTH-10 to D-AUTH-15, all approved, all with implementation authorization Pending.
- **Evidence base:**
  - [auth-migration-phase-a4-verification.md](auth-migration-phase-a4-verification.md) (cited as "A4");
  - [auth-migration-phase-a2-readiness.md](auth-migration-phase-a2-readiness.md) ("A2");
  - [auth-migration-verification-plan.md](auth-migration-verification-plan.md) ("VP");
  - [auth-migration-phase-a1.md](auth-migration-phase-a1.md) ("A1").

**Labels used in this plan:**
- **Board-approved:** a decision recorded in a Board decision record.
- **Verified (runtime):** observed in the A.4 sandbox.
- **Verified (source):** read in the installed Paperclip source.
- **Unverified:** an assumption or open question.
- **Proposed:** an implementation step that is not authorized.
- **Needs approval:** an action that needs a future, separate authorization.

## 1. Objective and scope

**Objective:** turn the six Board decisions into planned workstreams that close, or explicitly manage, the remaining Phase B blockers E8, E11 and E12, plus the residual risks VA-8, SF-1 and SF-3.

**In scope:** planning, sequencing, acceptance criteria and stop conditions.

**Out of scope:**
- any change to the live instance, credentials, users, roles, company access, agent permissions, ACLs or logs;
- any sandbox, restore, or agent or VR run;
- Phase B.

## 2. Decisions and their implications

| Decision | Board-approved | Implication for the plan |
|---|---|---|
| D-AUTH-10 (E8) | A backup is not recoverability; E8 unmet until a restore is verified; no improvised restore against the live instance | WS-1 must find or define a restore method, then verify it in isolation, before E8 can be met |
| D-AUTH-11 (VA-8) | Two instance admins are not a final state; a demotion plan is needed; no demotion now | WS-2 designs a demotion step for the rollback and migration runbooks |
| D-AUTH-12 (E11) | A planning workstream only; agent and VR tests need a separate authorization | WS-3 produces the test plan; E11 stays unmet |
| D-AUTH-13 (SF-1) | Claim URLs in logs are sensitive; access, retention and post-claim handling must be documented; live logs untouched | WS-4 writes the handling procedure for the migration window |
| D-AUTH-14 (SF-3) | Explicit roles in scripts and runbooks; no reliance on the `operator` default | WS-5 defines role selection and verification |
| D-AUTH-15 (E12) | R8 remediation plan; G-14 open until mitigated with evidence; D-AUTH-06's acceptance ≠ G-14 acceptance | WS-6 (R8) and WS-7 (G-14) |

## 3. Workstreams

### WS-1 — Restore verification (E8, D-AUTH-10)

**Objective:** a restore procedure that is documented, repeatable and verified, and that brings a Paperclip instance back from a backup.

**Current evidence:**
- **Verified (runtime):** `POST /api/instance/database-backups` writes a gzip SQL dump (A4 VA-9).
- **Verified (source):** there is no user-facing restore command. `runDatabaseRestore` is used only by `worktree init` (A4 VA-9).
- **Unverified:** whether a newer Paperclip release offers a restore command. The CLI reported 2026.1117.0 as available (A4 SF-2); its contents were not checked.

**Proposed actions:**
1. Read Paperclip's release notes and documentation for a supported restore. A Paperclip upgrade is a separate decision.
2. If none exists, describe candidate methods and their support status:
   - (a) restore the gzip SQL dump with the embedded Postgres tools into a **new, empty** isolated instance;
   - (b) a cold copy of the stopped instance's data folder.
   Neither is Paperclip-supported; the Board would have to accept the chosen method.
3. Write the test: a fresh isolated instance; seed data; backup; stop; restore into a **second** isolated instance; start; compare companies, issues, decisions and memberships (VP VA-9).

**Dependencies:** an isolated environment (as in D-AUTH-07a); Board acceptance of a method if it is not Paperclip-supported.

**Required authorization:** needs approval: the method choice, and the isolated restore run.

**Acceptance criteria:** the restored instance starts healthy, and companies, issues, execution policies and states, decision history and memberships match the source. This is the E8 condition, "a restore into the test environment succeeds".

**Rollback and recovery:** isolated only. The source sandbox is never overwritten.

**Stop conditions:**
- the method needs the live instance or its data folder;
- the method would overwrite an existing instance;
- the restored data differs in any compared field.

### WS-2 — Instance-admin demotion plan (VA-8, D-AUTH-11)

**Objective:** a controlled way to reach exactly one intended instance admin after a migration or a rollback.

"Exactly one intended instance admin" is the **target end state**, reached only after the whole procedure and its verification are complete. It is **not** a requirement to demote anyone at the moment the mode is switched. Two admins may exist temporarily, for example right after a rollback or before a re-migration, as long as that state is recorded. The guard below always applies: no demotion until the remaining admin is verified to work.

**Current evidence:**
- **Verified (runtime):** after a claim, `local-board` loses admin but keeps its `owner` membership (A4 VA-2). After a rollback to `local_trusted`, `local-board` is admin again and the claimant stays admin (A4 VA-8).
- **Verified (source):**
  - `POST /api/admin/users/:userId/demote-instance-admin` needs an instance admin;
  - it deletes only the `instance_admin` role;
  - it has **no guard against removing the last instance admin** (`routes/access.js` demote route; `services/access.js` `demoteInstanceAdmin` 499-505);
  - the board-claim link is offered only when `local-board` is the **only** instance admin (A1 1.9).
- **Unverified:**
  - what an instance without any admin can still do;
  - whether demoting the claimant after a rollback makes a later switch offer a new claim link (expected from source, not run).

**Proposed actions:**
1. **Decide which admin is necessary in each state:**
   - in `authenticated` mode, the claimed Board user;
   - in `local_trusted` mode, `local-board`, which is the implicit actor.
2. **Rollback runbook step:** after returning to `local_trusted`, demote the claimant only if the rollback is meant to be final. Otherwise keep both until the re-migration and record the temporary state.
3. **Re-migration step:** before switching again, make sure `local-board` is the only admin so that a fresh claim link appears; or skip the claim when the claimant is still admin.
4. **Pre-checks before any demotion:** list the instance admins (`GET /api/admin/users`). Continue only if at least two exist **and** the remaining admin has been verified to work in the current mode. Examples:
   - in `authenticated` mode, the claimed user signs in and `GET /api/cli-auth/me` shows `isInstanceAdmin: true`;
   - in `local_trusted` mode, a keyless admin read succeeds.
   An admin that has not been verified does not count as the remaining admin.
5. Decide separately whether `local-board`'s leftover **owner membership** after a claim needs handling. It is not an admin role.

**Dependencies:** WS-1, so that a damaged admin state is recoverable; an isolated test of the sequence.

**Required authorization:** needs approval: any demotion, live or isolated.

**Acceptance criteria:** a verified, isolated run of migrate → rollback → demote → re-migrate. When each sequence is complete and verified, it ends with exactly one intended admin, and admin access is never lost. The temporary states with two admins along the way are allowed and recorded.

**Rollback and recovery:** promoting again (`POST …/promote-instance-admin`) needs an admin, so the demotion must never remove the last one.

**Stop conditions:**
- fewer than two admins before a demotion;
- the remaining admin cannot act in the current mode;
- any unexpected change to memberships.

### WS-3 — Agent verification planning (E11, D-AUTH-12)

**Objective:** a ready-to-approve plan for agent runs in an isolated `authenticated` instance. The plan only; nothing runs.

**Current evidence:**
- **Verified (runtime, OQ-043 sandbox, not A.4):** agent keys keep same-company reads and refuse admin reads, without any agent run ([step2-board-decisions.md](../roadmap/step2-board-decisions.md) §6b).
- **Not verified:** any agent **run** in `authenticated` mode: per-run keys, the helper scripts, MCP; G-14 from a run.

**Proposed scope:**
- VR-8 (agents work in `authenticated` mode) and VR-9 (G-14 from an agent run, both modes). These are the cases that matter for E11 and E12.
- VR-1 to VR-7 only if the Board wants scheduler evidence beyond the source finding (D-AUTH-03R did not require it).

**Prerequisites** (each needs a decision):
1. **Agent identity:**
   - a separate Windows user with its own Claude Code login (the preferred §3.1 option, cancelled once on 2026-11-20); or
   - a recorded exception to reuse the Board Operator's session.
2. A throwaway repository, with no production repository and no `GH_TOKEN`.
3. Provider quota acceptance.
4. The live instance stopped for the duration, as in §3.1.
5. **Cursor agents:** whether they are included. They have no allowlist, so a run gives them a full shell as the run's Windows user.

**Evidence requirements per run:**
- the run log;
- the run's environment variable names, with values redacted;
- the wakeup and run rows;
- for VR-9, the permission-layer refusal.

**Stop conditions:**
- an agent touches any path outside the throwaway repository and sandbox;
- any Board credential is visible to the agent;
- any request reaches port 3100;
- the identity prerequisite is not met.

**Required authorization:** a separate, explicit Board authorization before any run (D-AUTH-12).

**Acceptance criteria:** this workstream is complete when the plan is approved. E11 itself stays unmet until the runs pass, or until the Board accepts migrating without them (A2 E11).

### WS-4 — Claim URL handling (SF-1, D-AUTH-13)

**Objective:** a documented procedure for the claim-URL exposure during a real migration.

**Current evidence:**
- **Verified (runtime, sandbox):** the claim URL is in the server's request log at INFO, and in the `paperclipai run` console output (A4 SF-1).
- **Unverified:** the live log file location and rotation. **Not inspected:** live logs, as required.
- In A.4 the claim link and CLI approval links were also passed through the assistant conversation. That is another place a claim secret can appear.

**Proposed actions** (procedure for the migration window):
1. **Access:** the instance folder, including logs, stays inside the Board Operator's profile (SYSTEM, Administrators and the user only). Confirm before the switch.
2. **Handling:**
   - The Board Operator reads the claim link from the console personally.
   - The link is not pasted into chat, tickets or the assistant.
   - The assistant does not read the raw link from the log.
3. **Window:** claim immediately after the switch; the link expires after 24 hours.
4. **Post-claim:**
   - confirm the status `claimed` (`GET /api/board-claim/<token>` is the only check that needs the token, so the Board Operator does it);
   - after a successful claim, handle the log lines according to the retention decision (for example rotate and delete the log, or keep it restricted).
   - Whether a used claim token has any further value is **unverified**. Until it is known, treat used tokens as sensitive.
5. **Retention:** the Board chooses a retention period for logs containing claim URLs.
6. **Upstream:** consider reporting SF-1 to Paperclip.

**Dependencies:** none for the procedure. Its execution happens inside an authorized migration window.

**Required authorization:** needs approval: the retention choice, and any log rotation or deletion.

**Acceptance criteria:** the procedure is part of the migration runbook, and the Board has chosen a retention period.

**Rollback:** not applicable. Logs are never edited in place.

**Stop conditions:** the claim link is found anywhere outside the console and the restricted log; claim the link immediately and record it.

### WS-5 — Explicit membership roles (SF-3, D-AUTH-14)

**Objective:** no script or runbook relies on the `operator` default.

**Current evidence:**
- **Verified (runtime):** `PUT /api/admin/users/:id/company-access` created an `operator` membership. `PATCH /api/companies/:id/members/:memberId` changed it to `viewer` (A4 VA-7).
- **Verified (source):** company invites accept an explicit `humanRole` (`createCompanyInviteSchema`, `humanRole` optional). Role changes are limited by role rank (`routes/access.js` `humanRoleRank` around line 978).
- **Unverified:** whether joining through an invite with `humanRole: viewer` produces a `viewer` membership with **no `operator` window**.

**Proposed least-privilege role selection:**

| Role | Use |
|---|---|
| `viewer` | Read-only humans and any read-only automation |
| `operator` | Only for a user who must wake agents or edit company issues, with every grant reviewed |
| `admin`, `owner` | The Board Operator only |
| Instance admin | The claimed Board user only (WS-2) |

**Proposed provisioning rule:**
- prefer an invite with an explicit `humanRole`;
- if `company-access` must be used, follow it **in the same runbook step** with an explicit role change;
- then verify with `GET /api/companies/:id/members` (or `/admin/users/:id/company-access`);
- record the brief `operator` window as a known exposure.

**Dependencies:** an isolated test of the invite path.

**Required authorization:** needs approval: any provisioning on the live instance; the isolated test of the invite path.

**Acceptance criteria:**
- every provisioning step in scripts and runbooks names a role and a verification;
- the invite path is verified in isolation, or the `operator` window is accepted in writing.

**Stop conditions:** the verified role differs from the intended role.

### WS-6 — R8 workspace ACL remediation (E12, D-AUTH-15)

**Objective:** stop other local Windows accounts from reading or changing the production repositories.

**Current evidence:**
- **Verified (runtime, read-only, 2026-11-20):** the workspace folder grants `Authenticated Users: Modify` and `Users: ReadAndExecute`, inherited from the drive root (A2 §4). Not re-checked in A.5.

**Proposed actions:**
1. Inventory every account and service that needs the folder, for example scheduled tasks, IDE helpers or a container engine. Read-only check.
2. Save the current ACL (`icacls <folder> /save <file> /t`) as the rollback point.
3. **Remediation option A:** on the workspace folder, disable inheritance and keep SYSTEM, Administrators and the Board Operator with Full Control; remove `Authenticated Users` and `Users`.
4. **Remediation option B:** move the repositories into the Board Operator's profile, which is already private.
5. Verify with `Get-Acl`, and with an access test from a standard account. That needs a test account, which is itself a separate decision.

**Dependencies:** none technical; the account inventory first.

**Required authorization:** needs approval: the option choice, and the ACL change itself.

**Acceptance criteria:** no broad Allow entry for `Authenticated Users` or `Users` on the workspace, with evidence. R8 is then closed, or explicitly accepted by the Board.

**Rollback:** `icacls … /restore` from the saved ACL file.

**Stop conditions:** a service or tool loses needed access; restore and stop.

### WS-7 — G-14 mitigation evidence (E12, D-AUTH-15)

**Objective:** evidence that no agent can act as the Board through keyless loopback requests.

**Current evidence:**
- **Verified (runtime, live, D-STEP2-01):** `Bash(curl *)` removed from the six Claude agents.
- **Verified (runtime, sandbox):** `authenticated` mode refuses every keyless request (A4 VA-1).
- **Not verified:** agent exploitability from a real run; Cursor agents, which have no allowlist.

**Proposed actions:**
1. The primary mitigation is the switch to `authenticated` (Phase B and Phase E), which is expected to close the keyless path for every process. **The switch does not close G-14 by itself.**
2. Until then, the Board decides the Cursor agent policy, for example no Cursor runs on the studio instance, or moving those roles to Claude.
3. **Evidence required before closing G-14 is even considered:**
   - keyless requests refused **on the live instance** after the switch (a read-only check). The sandbox result (A4 VA-1) is not enough;
   - an assessment of every agent execution path: Claude agents (allowlists, helper scripts, MCP) and **Cursor agents** (no allowlist, full shell). It must show that none of them can obtain Board rights by another route, for example by reading a Board credential that is available to the same Windows user;
   - VR-9, if WS-3's runs are authorized.

**Dependencies:** Phase B and Phase E for the main mitigation; WS-3 for the run evidence.

**Required authorization:** needs approval: the Cursor policy, the live switch, VR-9.

**Acceptance criteria:** G-14 stays **open** until:
- the live instance runs `authenticated` **and** keyless refusal is evidenced on it, **and** the agent execution path assessment (Claude and Cursor) is done; or
- another mitigation is evidenced to the same standard.

Meeting these makes G-14 eligible for a closure decision by the Board; it does not close G-14 automatically. D-AUTH-06's acceptance of the Claude Code credential risk does not count.

**Stop conditions:** not applicable to planning.

## 4. Dependencies and sequencing (proposed)

1. **Documentation now, no execution:** WS-3 plan, WS-4 procedure, WS-5 rule, WS-6 inventory method.
2. **Isolated runs, one authorization covering several:**
   - WS-1 restore;
   - WS-2 demotion sequence;
   - WS-5 invite path.
   These need a new isolated environment; A.4's environment was torn down.
3. **Board decisions:**
   - WS-1 method acceptance if it is not Paperclip-supported;
   - WS-4 retention;
   - WS-6 option;
   - WS-7 Cursor policy;
   - WS-3 identity prerequisite.
4. **Live, read-only:** the WS-6 account inventory.
5. **Live changes, each separately authorized:** the WS-6 ACL change; later, Phase B and Phase E.

## 5. Readiness impact (A2 §5 criteria)

| # | Before A.5 (A4 §7) | After the A.5 decisions |
|---|---|---|
| E1 | Unclear, not recorded | Unchanged. A Board review of the A.2 package and the A.4 report is still not recorded as such |
| E2, E3, E4 | Met | Unchanged |
| E5, E6, E7, E9 | Evidence meets the condition; Board review pending | Unchanged. D-AUTH-11 does not accept the VA-8 dual-admin state, so E9's residual state now needs WS-2 |
| E8 | Not met | **Not met.** D-AUTH-10 keeps it unmet until WS-1 succeeds |
| E10 | Met | Unchanged; this A.5 set still needs to be committed |
| E11 | Not met | **Not met.** WS-3 is planning only |
| E12 | Not met (partial) | **Not met.** WS-6 and WS-7 are planned, not done. D-AUTH-06 is not counted for G-14 |

## 6. Risks, prerequisites and stop conditions (cross-cutting)

**Risks:**
- Demoting the last instance admin (WS-2).
- A restore method that Paperclip does not support (WS-1).
- An ACL change that breaks a tool (WS-6).
- Claim links passing through chat or tickets (WS-4).
- Cursor agents with a full shell (WS-3, WS-7).

**Prerequisites for any execution:** a separate authorization per workstream, as listed above.

**Global stop conditions:**
- any step that would touch the live instance, credentials, users, roles, logs or ACLs without its own authorization;
- any unexpected write;
- any finding that contradicts A.4 evidence.

## 7. Planning vs implementation

- **Approved:** the six decisions (D-AUTH-10 to D-AUTH-15) and this planning work.
- **Not authorized:** every "Proposed action" and every item marked "needs approval".
- **Phase B:** not authorized.
