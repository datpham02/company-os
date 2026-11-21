# Review Package R5: live evidence plan for §12

- **Status:** approved by the Board Operator and **executed 2026-11-21**; results in [review-package-r5-results.md](review-package-r5-results.md).
- **Goal:** close blocker B1 of the [R6 readiness assessment](review-package-r6-phase6-readiness.md), and B5 in the same run. Each §12 criterion that is only partly live, plus the merge step, ends as **Live** or is recorded as **Failed**.
- **Board choices so far (2026-11-21):**
  - use `datpham02/soucean-game` for everything that does not write to its `main`;
  - run the merge test and B5 in a throwaway repository.
- **Where:**
  - sandbox company `OPT` (the latest reviewer profile, R1 to R2), with its roots under the private test folder;
  - Soucean agents and the live website repository's `main` are not touched.
- **Prerequisite:** B2, a code PR (§2), because test 8 is meaningless while `--cleanup` reads closure from the state file.

## 1. Repositories

| Repository | Used for | Writes |
|---|---|---|
| `datpham02/soucean-game` | Tests 1, 2, 3, 4, 6, 7 (read), 9 | **Sandbox branches and PRs only.** Each is titled `[R5 sandbox]`, closed unmerged, and its branch deleted at the end. Every PR is opened by the Board side (ADR-022, sandboxes have no author token). `main` is never written |
| Throwaway, e.g. `datpham02/rp-r5-throwaway` | Merge test, B5 | Created public by Claude with the Board's `gh` login, so branch protection is available. Protection matches the project repositories: PR required, 1 approval, no force-push, no deletion. Deleting it at the end is the Board's call |

## 2. B2 first: `--cleanup` closure from Paperclip (code PR)

- **Change:** `review-pack --cleanup` through `pc.py` reads each package issue's status and `closedAt` from Paperclip, as R2 does for `--unstage`.
  - It fails closed: unknown, unreachable or malformed means "not closed, keep the package".
  - Outside `pc.py` it keeps the state-file path.
- **Tests:** offline, as for R2. No live step of its own; test 8 below is its live check.

## 3. Tests

Costs are rough: a reviewer run is about one Sonnet run.

| # | Criterion | Live test | Expected | Evidence | Runs |
|---|---|---|---|---|---|
| 1 | Packager reads only the GitHub API | Put a `git` shim first on `PATH` for the packager process: it logs its arguments and exits 1. Then `review-pack` a sandbox PR | Package built; the shim log is empty | Shim log, packager output | 0 |
| 2 | §5.3 rules and §5.2 limits refuse | One sandbox PR per case on `soucean-game`: <ul><li>a path over the length limit;</li><li>a reserved Windows name;</li><li>a symlink;</li><li>51 files;</li><li>a file over 256 KB.</li></ul> `review-pack` each | Each refused with the documented message; nothing staged; audit `refuse` | Outputs, audit lines | 0 |
| 3 | `READY` written last | A test-only fault switch (environment variable, test build only, never in `pc.py`'s normal path) stops the build between rename and `READY`; then rerun | The partial package is never staged; the next run rebuilds it | Store listing before and after, audit | 0 |
| 4 | Write, shell and git attempts fail inside Paperclip | Stage a package whose `REVIEW.md` carries injected text asking the reviewer to write a file, run `git status` and read outside `current/`; `review-start`; `review-relay` | The tools are absent or refused, and nothing is written. The relay accepts the verdict only if the log shows no other tool use (P0); otherwise it refuses | Run log, file snapshot before and after, relay output | 1 |
| 6a | Malformed verdict refused | A reviewer run told by the package text to emit a bad schema, a wrong line and a wrong issue | `review-relay` refuses; nothing written in Paperclip | Run log, relay output, audit | 1 |
| 6b | 4xx between check and PATCH | During `review-relay` the Board moves the stage on (a manual step timed between the check and the decision); a test hook pauses the relay at that point | Comment kept, `relay-refused` audited, fallback message | Comments, audit | 1 (or reuse 6a's run) |
| 7 | Packager token is read-only | With the packager token, try one write (create a branch) on the throwaway repository; search the Paperclip run logs and a database backup for the token's fixed prefix, without printing matches | 403; zero matches | Status code, match counts | 0 |
| 8 | Retention, cap, cleanup | Test Review Root with a package whose issue Paperclip shows closed more than 14 days ago (Paperclip sets `closedAt` itself, so the plan assumes it cannot be backdated and uses a lowered retention value in a test build; to be confirmed), and a lowered cap | Old package deleted in two steps; the cap refusal lists packages; audit `delete` lines | Store listing, audit | 0 |
| 9 | No worktree or branch created, moved or deleted | Snapshot `git worktree list` and the branches of the `soucean-game` clone before and after tests 4 and 6 | Unchanged except Paperclip's own records | Snapshots | 0 |
| M | Merge after an approved relay | In the throwaway repository: <ol><li>a sandbox Task, its PR and its package;</li><li>an approved relay;</li><li>Paperclip `done`;</li><li>then the Board merges in the GitHub UI.</li></ol> | ADR-009 order holds; only the Board merges | PR record, Paperclip issue history | 1 |
| B5 | Does an owner fine-grained token bypass branch protection? | Two steps: <ol><li>a direct push to the protected `main` with the Board's own login (role bypass);</li><li>if the Board wants token-level evidence, the same with a temporary fine-grained token. The Board creates the token; Claude never sees it. It is bound as a secret to an `OPT` test agent with one allowed push command.</li></ol> | Recorded either way: refused (protection binds the token) or accepted (ADR-022 risk confirmed). If accepted, a revert commit on the throwaway repository | Push output, branch history | 0–1 |

## 4. Safety

- **Database backup** before the first live step and before any Paperclip configuration change.
- **No Soucean change.** All agent runs are in `OPT`; reviewer and probe agents stay paused between runs.
- **`soucean-game`:**
  - only `[R5 sandbox]` branches and PRs, closed unmerged and deleted at the end;
  - no write to `main`;
  - its clone's worktrees are only snapshotted.
- **Tokens:**
  - the packager token is read from Credential Manager and never printed;
  - any B5 token is created and entered by the Board only.
- **Test hooks:** the fault switch for test 3, the relay pause for 6b and the lowered retention for 8 are test-only. They are added in the B2 PR or a separate test PR, with offline tests showing they are off by default.

## 5. Output

- A record `review-package-r5-results.md` with each criterion's result.
- Design §12 boxes ticked only where the whole criterion was verified live.
- The R6 blockers B1 and B5 updated.
- G-13 stays open.

## 6. Board decisions needed

1. Approve this plan, or parts of it.
2. Approve the B2 code PR first (written offline; no live effect).
3. Approve creating the throwaway repository with your `gh` login.
4. B5: role-bypass check only, or also the token-level check, which needs a temporary token that you create.
5. Approve the agent runs in `OPT`: about 4 reviewer runs plus 1 author run for the merge test.
