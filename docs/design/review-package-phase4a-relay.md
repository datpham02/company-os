# Review Package Phase 4a: Verdict Relay (offline)

- **Status:** code and offline tests done. **Phase 4b ran on 2026-11-21** on the live instance in a throwaway company: see [review-package-phase4b-live.md](review-package-phase4b-live.md). §4 below is kept as written before that run.
- **Phase definition:** [review-package.md](review-package.md) §11, Phase 4 "Paperclip sandbox and relay API"; relay design §3.
- **Why split:** Phase 4 needs a separate Paperclip instance and a real `code-reviewer` agent run. Agent runs and Paperclip experiments need their own Board approval (§3.1 sandbox rules, D-AUTH-12). So the relay is written and tested first against a fake Paperclip (4a); the sandbox validation comes after approval (4b).
- **Code:**
  - `.claude/skills/paperclip/scripts/review_relay.py` (new);
  - `pc.py`: the `review-relay` command.
- **Tests:** `test_review_relay.py`, 55 tests against an in-memory fake Paperclip and a fake PR head. `test_pc.py` runs them with the other 178 (233 OK with `-W error`).
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
| 2 Run | The run is in `GET /issues/<id>/runs`, its `agentId` is `code-reviewer`, its status is `succeeded`, it was created at or after `stagedAt`; and the lock's `runId`, if set, matches | `Check2Run` |
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

## 4. Not covered offline (Phase 4b, needs the Board)

The fake Paperclip follows the shapes recorded in §3.2 and in `pc.py`. These remain unverified:
- **V1:** whether a review stage can name a user (the Board Operator or a relay user) while `code-reviewer` is woken without being a participant, and whether Paperclip then accepts the relay's `PATCH`.
- **V2:** whether a `code-reviewer` woken for an issue it is not assigned to runs normally, and in which cwd.
- **V3:** whether an agent's process reaches Board endpoints in `local_trusted` mode.
- The real run log format of a `claude_local` reviewer run (the stream-json `result` event inside `chunk` records), and the exact 422 text.

**Board decisions needed before 4b:**
1. Start a separate sandbox Paperclip instance (separate data folder and port, no production secrets, live Paperclip stopped during HTTP experiments, per the §3.1 sandbox rules).
2. Create a `code-reviewer` agent there with the Phase 2 strict profile (`--restricted --tools Read,Grep,Glob`) and run it on one sandbox issue. This is an agent run, which D-AUTH-12 says needs its own authorization.
3. Which GitHub source the sandbox review uses: `datpham02/soucean-game` PR #27 again (read-only, the stored token), or another PR.

## 5. Acceptance against §12

- "The relay accepts only a verdict that passes §3.4. A re-run never duplicates a comment or decision. A refusal leaves the human fallback": **met offline**, not yet in a sandbox.
- No other §12 item changes.
