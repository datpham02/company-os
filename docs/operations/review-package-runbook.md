# Review Package runbook (Phase 6 pilot)

- **Status:** `PROPOSED`. Written in P6-A (work item W5) of the [Phase 6 proposal](../design/review-package-phase6-proposal.md). Nothing here has been done in Soucean yet: P6-B (create the reviewer), P6-C and P6-D each need their own Board approval.
- **Scope:** Soucean, project `soucean-game`, code Tasks created with `pc.py create --review-package`, the first five Tasks (pilot). Design and document Tasks keep their current reviewer.
- **G-13 stays open.** The pipeline gives evidence of binding and access, not of understanding. The Board's approval and merge remain the gate (ADR-009).

## 0. What is verified, and where

| Behaviour | Status |
|---|---|
| Packager reads only the GitHub API; rules and limits refuse; `READY` last; packager token read-only | **Sandbox-validated** (R5 tests 1, 2, 3, 7) |
| Reviewer has only Read, Grep, Glob; ignores and reports injected instructions; writes nothing | **Sandbox-validated** (R1, P0, R5 test 4) |
| Relay checks; F1 re-check; Board merge after an approved relay | **Sandbox-validated** (R5, 6b re-run, test M) |
| `--cleanup` reads closure from Paperclip (`completedAt` / `cancelledAt`) | **Sandbox-validated** (R5 test 8) |
| W1: task read from the Paperclip issue (task-contract §2 sections), no state or task file | Offline tests only. **Not yet run against a live issue** |
| W3: `create --review-package` stages `review` then `approval`, both `local-board` | Offline tests; Paperclip source read. **Two consecutive `local-board` stages not yet run live** (checked in P6-B on an `OPT` issue) |
| W4: `review-run` (resume, start, wait, pause) | Offline tests only. **Not yet run live** |
| Reviewer created in Soucean from `claude-reviewer-strict` | **Not done** (P6-B) |
| No worktree or branch changed during a production review (§12 criterion 9) | **Not yet verified in production** (P6-C) |

These are tool-surface limits of Claude Code. The reviewer's process is **not** isolated from the operating system or the network, and G-14 (`local_trusted`) still lets any same-user process act as the Board.

## 1. Setup (P6-B, needs approval)

1. **Roots.** Create a Review Root and a Staging Root in a private folder. It must be outside every repository, every worktree, the agents' workspace and every agent's working directory. Set them for the Board's shell:
   - `COMPANY_OS_REVIEW_ROOT`
   - `COMPANY_OS_STAGING_ROOT`
2. **Reviewer working folder.** An empty folder, outside the roots and every repository.
3. **Packager token** (the Board does this; Claude never sees it):
   - **Create:** a fine-grained token, **read-only**: Metadata, Contents, Pull requests: read. Repository: `soucean-game`. Expiry at most 90 days.
   - **Store** it in your own terminal (the command asks for the value):
     ```powershell
     cmdkey /generic:company-os/review-packager /user:review-packager /pass
     ```
   - **Track the expiry:** record the expiry date in your calendar with a reminder 14 days before. The previous token lapsed silently (R5 F4); GitHub then answers 401 and nothing is packaged.
4. **Reviewer agent** (`code-reviewer`, profile `claude-reviewer-strict`):
   - **Build:** `python -I scripts/setup/build-package.py --prefix SOU --with-reviewer --staging-root <Staging Root> --reviewer-cwd <reviewer folder> --out <dir>`. The build refuses a reviewer configuration that fails `check_reviewer_config`.
   - **Create** the agent in Soucean with exactly that configuration, **paused**. How to add one agent to the existing company (UI or API) is decided and recorded in P6-B; importing a single agent into an existing company is `UNVERIFIED`.
   - **Never resume it by hand** except through `review-run`. `post-import.py --resume` leaves it paused.
5. **Checks:**
   - `pc.py review-run --check` says paused with no active run;
   - `pc.py review-pack --status` says the staging is empty and `verified`;
   - in `OPT`, an issue with the two `local-board` stages behaves as the proposal §4 says.

## 2. Per Task (each step started by the Board)

The author (`web-engineer`) pushes its Task Branch, opens the PR with its own token (ADR-022) and moves the Task to `in_review`. Paperclip hands the `review` stage to `local-board`. Then:

| # | Board step | Command |
|---|---|---|
| 1 | Check the Task and the PR (number, head, write set). Only one review at a time: staging must be empty | `pc.py show <KEY>` · `pc.py review-pack --status` |
| 2 | Package the PR. The task comes from the issue's `## Acceptance criteria` and `## Write set`; the project must be configured for the repository | `pc.py review-pack <KEY> --github-pr <N> --github-repo datpham02/soucean-game --allow-repo datpham02/soucean-game` |
| 3 | Run the review: resumes `code-reviewer`, `review-start`, waits (default 30 min), pauses it again | `pc.py review-run <KEY>` |
| 4 | Relay the verdict. It posts the findings and records `approved` or `changes_requested` on the `review` stage | `pc.py review-relay <KEY> --run-id <R>` |
| 5 | Unstage | `pc.py review-pack --unstage` |
| 6 | **Approval stage and merge, by the Board:** read the PR and the findings; approve the approval stage in Paperclip; merge in GitHub. The PR author is your own account (ADR-022), so the merge uses admin bypass | `pc.py approve <KEY>` · GitHub UI |

- `changes_requested` returns the Task to the author. A new head means a new package (step 2).
- If any step refuses, see §4. The Board can always decide by hand: `pc.py approve <KEY>` / `pc.py request-changes <KEY>`.

## 3. Status

- `pc.py review-pack --status`: the staging lock (challenge hidden), the reviewer's runs from Paperclip, `verified`.
- `pc.py review-run --check`: whether `code-reviewer` is paused, running, or **left resumed**.
- `pc.py show <KEY>`: stages, comments, runs (hand-overs show as `handed over`).
- The audit log in the Review Root records every build, stage, start, relay, refusal and cleanup.

## 4. Refusals and what to do

| Refusal (message family) | Do this |
|---|---|
| Package rule or limit ("split the Task", reserved name, path too long, file too large) | Split the Task, or review by hand |
| Task contract ("no '## Acceptance criteria' section", "not a list item", "exactly one is required") | Fix the issue description, then package again. Requirements are never guessed |
| "is not in_review", "another issue", "configured for repository" | Check the Task's status, key and project |
| GitHub 401 or 403 | The packager token expired or lacks access: the Board renews it (§1.3) |
| "staging holds …" | Finish or unstage the other review first |
| `review-run`: "not paused" or "active runs" | `review-run --check`; wait, or cancel the run, then pause the reviewer |
| `review-run`: "ambiguous" or "recorded no reviewer run" | Nothing is retried. `review-pack --status`, then `review-start` again; it recovers or stops with instructions |
| `review-run`: timeout | The reviewer is paused, which can cancel the run. Check the run; start again or decide by hand |
| Relay: tool surface, log hash, verdict format, `reviewId` or challenge, head moved | The Board decides by hand. If the reviewer used a forbidden tool, follow §6 |
| Relay: "changed while the relay ran" (F1) | A decision was made meanwhile; it stands. Check it with `pc.py show <KEY>` |
| Any Paperclip error | Nothing was recorded unless the message says so; the Board decides by hand |

## 5. Cleanup and retention

- Weekly, by hand: `pc.py review-pack --cleanup`.
  - A package is deleted 14 days after its issue closed, by the Paperclip closure time: `completedAt` for `done`, `cancelledAt` for `cancelled`.
  - Anything Paperclip does not confirm is kept and audited `cleanup-skipped`.
  - The staged package is never deleted.
- Cap 2 GB: a build over the cap cleans up first, then refuses and lists the largest open packages.
- The audit log is never deleted by cleanup.

## 6. Incidents

| Incident | Response |
|---|---|
| The reviewer used a tool other than Read, Grep or Glob, or a permission denial appears in its log | The relay refuses. Pause the reviewer (`review-run --check`), `review-pack --unstage --abandon`, review by hand, record the run id and log, and stop the pilot until the Board decides |
| Anything was written by the reviewer (unexpected file in its folder, the staging or the roots) | As above; also compare the staging with the package (`review-pack --status`, the relay's package verification) and keep the evidence |
| A token or secret appears in a run log | Rotate it at once (packager: §1.3; author token: ADR-022, security-operations §2) |
| The reviewer is left resumed (killed `review-run`, crash, shutdown) | `pc.py review-run --check` reports "LEFT RESUMED". Pause it in the Paperclip UI (Agents › code-reviewer › Pause), then check again. Run this check after any interrupted review and before every review |

## 7. Paperclip upgrades

Before the first review on a new Paperclip version, go through the re-check list in [R6 §8](../design/review-package-r6-phase6-readiness.md) and run the offline suites:
- `.claude/skills/paperclip/scripts/test_review_pack.py`
- `test_review_github.py`
- `test_review_relay.py`
- `test_pc.py`
- `scripts/setup/test_build_package.py`

Any changed behaviour stops live reviews until it is handled.

## 8. Rollback and manual fallback

- **Manual fallback, any time:** the Board decides the stage by hand (`pc.py approve` / `request-changes`); nothing in the pipeline is needed for that.
- **Stop the pilot:**
  - pause or delete `code-reviewer`;
  - `pc.py review-pack --unstage --abandon`;
  - create new Tasks without `--review-package`;
  - revoke the packager token if it is no longer needed.
