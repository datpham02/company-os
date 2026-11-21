# Review Package R2: results (R2-B to R2-E)

- **Date:** 2026-11-21. R2-B to R2-D (code and offline tests) in PR #53; **R2-E live check 04:37–04:40 UTC**, after the Board Operator's approval ("Duyệt R2-E").
- **Design:** `review-package-r2-unstage-design.md` (PR #52), with the proposed Board decisions:
  - active runs refuse even with `--abandon`;
  - `interrupted` refuses unless `--abandon`;
  - `review-start` records `companyId` and `reviewerAgentId`;
  - `--status` is a follow-up.
- **Code under test:** branch `feat/review-package-r2-unstage` at `6e3dca9`; `test_pc.py` 330 OK before the live run.
- **After this record:** a self-review found that `reviewer_run_state` ignored active reviewer runs created before the staging time. It was fixed in PR #54: any active run now blocks, whatever its age; `test_pc.py` 331 OK. The live R2-E result is unaffected, because the blocking run there was created after staging.
- **Where:** sandbox `OPT` only. Database backup first (`paperclip-20261121-113805.sql.gz`; not proof of a restore). Soucean not touched.

## 1. Offline (R2-D)

`python -I -W error`: `test_review_pack.py` 89, `test_review_github.py` 25, `test_review_relay.py` 143, `test_pc.py` **330 OK**. The new tests fail on the previous code (2 failures, 44 errors). Cases covered:
- active, `interrupted`, unknown and terminal statuses;
- Paperclip errors, malformed data, no check;
- run missing or of another issue, company or agent;
- runs before staging;
- `staging.op` present;
- `review-start` against `unstage` in both directions;
- a run appearing between the two checks;
- an interrupted unstage;
- state-file runs ignored.

## 2. Live (R2-E, OPT)

**Setup:**
- `OPT-3` was `blocked`, left by Paperclip after the R1 decision. The Board set it to `in_review`; participant `local-board`.
- Staged (package reused, soucean-game PR #27, read-only).
- The OPT reviewer was resumed for one run and paused when it ended.

| Step | Result |
|---|---|
| `review-start OPT-3` | Sub-issue `OPT-8`, run `30593d97` (`queued`, then `running`) |
| `--unstage` while the run was `running` (04:38:41Z) | **Refused**: "the reviewer agent has an active run (30593d97…, running); cancel it first (pc.py cancel-run …); --abandon does not override an active run" |
| `--unstage --abandon` while running (04:38:42Z) | **Refused**, same message |
| State after both attempts | Run still `running`; staging lock SHA-256 unchanged; 12 staged files; `staging.op` released; no `unstaging` mark |
| Run ended (`succeeded`, 04:39Z); reviewer paused | — |
| `--unstage` before a relay | Refused: "has not been relayed" (Paperclip check clear; the relay rule applies) |
| `review-relay` | Refused by design: head `7f22f059666b` was already relayed for `OPT-3` in R1 Phase D (run `021f2cdb`). One decision per head (§3.5); nothing recorded |
| `--unstage --abandon` after the run (04:39:21Z) | **Cleared.** Audit `abandon` with `verified: true`, `reviewerAgentId`, and `reviewerRuns` = `30593d97` `succeeded` and `82260e20` `cancelled` (Paperclip's `issue_disposition_repair`, cancelled because the reviewer was paused) |

**Side effects** (counts before → after):
- **OPT:** 7 → 8 issues (sub-issue `OPT-8`) and 13 → 15 runs (reviewer run `30593d97`; cancelled `issue_disposition_repair` `82260e20`).
- **No author run.**
- `OPT-3` stays `in_review`, with no new decision.
- `OPT-8` stays `in_progress`: the relay did not run, so it did not close it.
- **REV, RPR, Soucean unchanged.** All sandbox agents paused; Soucean idle.

## 3. Acceptance (R2 §4)

| Criterion | Status |
|---|---|
| `--unstage` uses Paperclip as the source of the reviewer's run state | **Done** (code, offline tests, live) |
| No staging deletion while a reviewer run is active | **Done**, live: refused with and without `--abandon` |
| Paperclip errors or unreliable data fail closed | **Done** offline; not provoked live |
| `staging.op` prevents `review-start`/`unstage` races | **Done** offline (threads, both directions); live: released after every command |
| Offline tests and regression suite pass | **Done**: 330 OK |
| Live test: unstage refused while the reviewer runs | **Done** (§2) |
| Audit evidence and report | **Done**: this record and the audit lines quoted |
| No change outside the approved scope | **Done**. The intended changes are listed in §2; Paperclip configuration unchanged |

## 4. Findings

- **The audit `refuse` lines of `unstage` have `issue: null`.** The CLI audits refusals with the command's issue key, and `--unstage` takes none. The lock's issue would be more useful. Small follow-up.
- **Re-reviewing the same head cannot be relayed again** (`OPT-3` at `7f22f059`). This is the intended one-decision-per-head rule (design §3.5), so a sandbox re-test needs a new head or a new parent issue.
- **`OPT-3` had moved to `blocked`** after the R1 `changes_requested` decision returned it to the paused placeholder author. That is Paperclip's handling; it is unrelated to R2.

## 5. Left in place

- `OPT-8` (`in_progress`, assigned to the paused reviewer); close or cancel it when the Board wishes. If the reviewer were resumed, Paperclip could queue another `issue_disposition_repair` run for it.
- `OPT-3` (`in_review`); staging empty; the backups.
- G-13 and G-14 unchanged.
