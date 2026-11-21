# Review Package Phase 4a: Verdict Relay (offline)

- **Status:** Phase 4a (this record) is the offline implementation: code and tests against a fake Paperclip. The live validation is **Phase 4b**, run on 2026-11-21 on the live instance in a throwaway company, recorded separately in [review-package-phase4b-live.md](review-package-phase4b-live.md). §4 says what 4a left open and where 4b answered it.
- **Phase definition:** [review-package.md](review-package.md) §11, Phase 4 "Paperclip sandbox and relay API"; relay design §3.
- **Why split:** Phase 4 needed a Paperclip instance and a real `code-reviewer` agent run. Agent runs and Paperclip experiments need their own Board approval (§3.1 sandbox rules, D-AUTH-12). So the relay was written and tested first against a fake Paperclip (4a); the live validation followed with the Board's approval (4b; the Board chose the live instance with a throwaway company over a separate sandbox).
- **Code:**
  - `.claude/skills/paperclip/scripts/review_relay.py` (new);
  - `pc.py`: the `review-relay` command.
- **Tests:** `test_review_relay.py`, 55 tests against an in-memory fake Paperclip and a fake PR head at the end of 4a (233 in `test_pc.py`). Phase 4b added the company-scoped run tests (§2, check 2).
- **G-13 stays open.** Nothing here shows reviewer isolation inside Paperclip.

## 1. Command

```text
python -I .claude/skills/paperclip/scripts/pc.py review-relay <KEY> --run-id <run-id> \
  [--identity local-board] --review-root <dir> --staging-root <dir>
```

- `--identity`: the Paperclip user the relay acts as. The default is the Board Operator (`local-board`), as §3.3 proposes.
- The `code-reviewer` agent id is looked up by name in the company.
- The current PR head comes from GitHub with the packager token (Credential Manager, read-only; Phase 3 code). A package built from a fixture has no live PR to compare with, so the relay refuses it.

## 2. What it checks (§3.4, fail closed)

Every failed check stops the relay with a reason. Nothing is written to Paperclip, and the audit log gets a `refuse` line (`relay: …`).

| Check | Implementation | Tests |
|---|---|---|
| 1 Issue and participant | `in_review`, and `executionState.currentParticipant` is `user` with `userId` = the relay identity | `Check1IssueAndParticipant` |
| 2 Run | The run is in `GET /issues/<id>/runs`, or (added in 4b) a company-scoped run read with `GET /heartbeat-runs/<id>` whose `companyId` is the issue's and whose `issueId` is empty or this issue. In both cases its `agentId` is `code-reviewer`, its status is `succeeded`, it was created at or after `stagedAt`, and the lock's `runId`, if set, matches. For what this does and does not establish, see the `_company_run` docstring and [review-package.md](review-package.md) §3.4 | `Check2Run`, `Check2CompanyScopedRun` |
| 3 Staging | The lock names `<KEY>`; the staged copy and the store copy both verify against the lock's manifest SHA-256; the manifest head equals the lock head | `Check3Staging` |
| 4 PR head | GitHub's current PR head equals the lock head | `Check4Head`, `GitHubHead` |
| 5 Verdict | From the run log: the last stream-json `result` event is the final message. It must hold exactly one fenced `json` block, at the end. Schema `review-verdict@1`; `issue` and `headSha` equal the lock; each finding has a manifest path, `side` head or base, a severity, a title, and a line inside that file at that side (counted in the package); `changes_requested` needs a finding | `Check5Verdict` |

## 3. Recording (§3.5)

- **Order:** the findings comment first, then the decision (`PATCH` with `done` for approve, `in_progress` for request changes, each with a comment).
- **Receipt:** the comment ends with `relay-receipt: <run-id> <headSha>`. Success writes a `relay` audit line with the run id, so `review-pack --unstage` accepts the relayed review.
- **Re-run:**
  - receipt found and the issue no longer `in_review`: "already relayed", nothing written;
  - receipt found and still `in_review` (the decision failed earlier): all checks run again, then only the decision is retried;
  - a receipt for the same head from a **different** run, in the comments or the audit log: refused; the Board decides which review stands.
- **Transient errors** (network, 5xx): 3 attempts, backoff 1 s and 2 s. After a failed comment `POST`, the comments are read again before a retry, so a comment the server stored despite the error is not posted twice.
- **Refusal** (4xx, for example 422 "Only the active reviewer…"): no retry. The comment stays, the audit log gets `relay-refused`, and the message names the fallback: `pc.py approve <KEY>` or `pc.py request-changes <KEY>`.

## 4. Not covered offline, and what Phase 4b found

The fake Paperclip follows the shapes recorded in design §3.2 and in `pc.py`. The offline tests could not answer these; Phase 4b ([review-package-phase4b-live.md](review-package-phase4b-live.md)) did, except V3:
- **V1** (user stage participant, relay `PATCH` accepted): **yes**, for one `changes_requested` decision.
- **V2** (a `code-reviewer` woken for an issue it is not assigned to): **no**, Paperclip cancels that run. The reviewer is woken without an issue, and check 2 was extended for that run (§2).
- **V3** (agent processes reaching Board endpoints): **not tested**. G-14 stays open.
- Run log format: the real `claude_local` log matched the shape assumed here (stream-json `result` event inside `chunk` records). The exact 422 refusal text was not seen live.

The Board decided before 4b: the live instance with a throwaway company instead of a separate sandbox, a `code-reviewer` agent with the Phase 2 strict profile, and `datpham02/soucean-game` PR #27 as the source.

## 5. Acceptance against §12

- "The relay accepts only a verdict that passes §3.4. A re-run never duplicates a comment or decision. A refusal leaves the human fallback": **met offline** in 4a. Phase 4b observed it live for one refusal (check 5), one recorded decision and two duplicate attempts; the 4xx fallback path was not triggered live.
- No other §12 item changes.
