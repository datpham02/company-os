# Board Decision Record — Authentication Migration, Phase A.5

**Date:** 2026-11-20
**Status:** Six decisions approved by the Board Operator, in chat, on 2026-11-20. **Every implementation authorization is Pending.**
**Scope:** the six open points of the Phase A.4 report, [auth-migration-phase-a4-verification.md](../architecture/auth-migration-phase-a4-verification.md) §8.
**Authority:** Board Operator
**Plan:** [auth-migration-phase-a5-plan.md](../architecture/auth-migration-phase-a5-plan.md), cited as "A5-P".

**Earlier decisions stay as recorded:**
- D-AUTH-01 to D-AUTH-05: [auth-migration-board-decisions.md](auth-migration-board-decisions.md).
- D-AUTH-03R and D-AUTH-06 to D-AUTH-09: [auth-migration-phase-a3-board-decisions.md](auth-migration-phase-a3-board-decisions.md).

This record adds D-AUTH-10 to D-AUTH-15 and changes none of the earlier decisions.

**Rule:** an approval here decides a direction or a requirement. Nothing in this record authorizes:
- a change to the live Paperclip instance;
- a credential, user, role, ACL or log change;
- a sandbox, an agent run or a restore attempt;
- Phase B.

## Summary

| ID | Topic (A.4 §8) | Decision | Approval | Implementation authorization |
|---|---|---|---|---|
| D-AUTH-10 | E8, backup and restore | A backup does not establish recoverability. E8 stays unmet until a restore has been verified. No improvised restore against the live instance | Approved | Pending |
| D-AUTH-11 | VA-8, dual instance admins | Two instance admins are not an acceptable final state. A controlled demotion plan is required. No demotion now | Approved | Pending |
| D-AUTH-12 | E11, agent verification | A separate **planning** workstream for agent verification is approved. Running agent or VR tests needs a separate, explicit authorization | Approved | Pending (planning only) |
| D-AUTH-13 | SF-1, claim URL in logs | Claim URLs and tokens in server logs are sensitive. Access restriction, retention and post-claim handling must be documented. Live logs are not touched now | Approved | Pending |
| D-AUTH-14 | SF-3, company-access default role | Scripts and runbooks must set the intended role explicitly and never rely on the API's `operator` default. Least-privilege selection and verification must be defined | Approved | Pending |
| D-AUTH-15 | E12, R8 and G-14 | A remediation plan for R8 is required. G-14 stays open until its risk is mitigated and the mitigation is evidenced. D-AUTH-06's acceptance of the Claude Code credential risk does **not** accept G-14. No ACL, permission or mode change now | Approved | Pending |

## D-AUTH-10 — Backup and restore (E8)

**Decision:**
- A successful backup does not establish recoverability.
- E8 stays **unmet** until a restore has been verified successfully.
- No restore is to be improvised against the live instance.

**Evidence:** A.4 VA-9. Backup creation works; Paperclip 2026.1023.0 has no supported restore procedure; the restore was not attempted.

**Plan:** A5-P workstream WS-1.

**Implementation authorization:** Pending. Any restore attempt, even in an isolated environment, needs its own authorization.

## D-AUTH-11 — Dual instance administrators (VA-8)

**Decision:**
- Two instance admins (`local-board` and the claimant) are **not** accepted as a final operating state.
- A controlled demotion plan for the unnecessary admin must be documented.
- Nobody is demoted in this phase.

**Evidence:** A.4 VA-8, rollback to `local_trusted` leaving both admins.

**Source finding** (A5-P WS-2): the demotion route does not prevent removing the last instance admin. A wrong demotion can therefore lock the instance out of administration.

**Plan:** A5-P WS-2.

**Implementation authorization:** Pending.

## D-AUTH-12 — Agent verification planning (E11)

**Decision:**
- A separate workstream to **plan** agent verification is approved: scope, prerequisites, test cases, evidence requirements and stop conditions.
- **Agent and VR tests are not authorized.** Running them needs a separate, explicit Board authorization.
- D-AUTH-07c (deferral of the VR cases) stays in force until then.

**Plan:** A5-P WS-3.

**Implementation authorization:** Pending. This decision authorizes planning documents only.

## D-AUTH-13 — Claim URL in server logs (SF-1)

**Decision:**
- Board-claim URLs, tokens and codes in server logs are sensitive information.
- Access restriction, retention and post-claim handling must be documented.
- Live logs are not modified or deleted in this phase.

**Evidence:** A.4 VA-2 and SF-1, sandbox log only. The live log was not inspected.

**Plan:** A5-P WS-4.

**Implementation authorization:** Pending.

## D-AUTH-14 — Company-access default role (SF-3)

**Decision:**
- Future scripts and runbooks must state the intended membership role explicitly. They must not rely on the `operator` default of `PUT /api/admin/users/:id/company-access`.
- Least-privilege role selection and its verification must be defined.

**Evidence:** A.4 VA-7 setup and SF-3, one sandbox call.

**Plan:** A5-P WS-5.

**Implementation authorization:** Pending. No user, role or membership is changed.

## D-AUTH-15 — R8 and G-14 (E12)

**Decision:**
- A remediation plan for **R8** (the workspace folder grants Modify to all Authenticated Users) is required.
- **G-14** stays open until its risk is mitigated and the mitigation is supported by evidence.
- D-AUTH-06 accepted the residual risk that a Claude Code session can use the Board credential. That acceptance does **not** accept G-14.
- No ACL, agent permission or authentication mode is changed now.

**Plan:** A5-P WS-6 (R8) and WS-7 (G-14).

**Implementation authorization:** Pending.

## Readiness after these decisions

**E8, E11 and E12 stay unmet.** The decisions define the work needed to meet them; they do not meet them.

Phase B remains **not authorized** (A5-P §5).
