---
name: paperclip
description: Operate the company's Paperclip instance for the Board Operator from chat. Use it to see what agents and issues are doing, read issue comments and run logs, release backlog tasks, approve or send back work awaiting the Board, create and assign tasks, wake agents and cancel runs. Use it whenever the user mentions Paperclip, an issue key such as SOU-12, an agent role (director, qa, …), a milestone, approving, releasing, or "what is the studio doing".
---

# Paperclip control (Board Operator)

The studio runs on a local Paperclip in `local_trusted` mode (`http://127.0.0.1:3100`). Every command below is a REST call made as the **Board**, so treat each write as the user's own action.

Run every command from the repository root:

```bash
python -I .claude/skills/paperclip/scripts/pc.py <command> [args]
```

If Paperclip is not reachable, tell the user to double-click **Start Game Studio** (`runtime/tools/start-studio.cmd`). It also starts the review-wake watchdog.

## Commands

| Command | What it does |
|---|---|
| `health` | Paperclip version and mode |
| `overview` | Company, projects, agents and every open issue (review first, then in progress, blocked, todo, backlog) |
| `show SOU-8 [--comments N] [--description]` | One issue: status, assignee, current stage, blockers, branch, latest comments, runs. A run Paperclip cancelled because its agent handed the issue over (confirmed by the run record) shows as `handed over`; other cancellations show their reason, such as `cancelled (agent_paused)` |
| `log <run-id> [--tail N]` | Output of one run; take run ids from `show` |
| `triage` | Read-only daily sweep (knowledge/company/workflows/daily-triage.md): what needs the Board, blocked issues and whether they name an unblock owner, stalled reviews, quiet tasks, ready backlog, and agents with more than one `in_progress` issue across all projects (or "COULD NOT CHECK WIP" when that cannot be read) |
| `release SOU-8 [SOU-9 …] [--force]` | `backlog` → `todo`. **The assignee starts working immediately and spends usage.** First runs two hard guards (below): the WIP limit and the Write Set conflict guard. Then refuses an issue with no review/approval stage or with open blockers. `--force` skips only those last checks, and only on the user's explicit word |
| `approve SOU-8 "comment"` | Board approval: sets `done` with the comment. Only works while the issue waits on the Board |
| `request-changes SOU-8 "comment"` | Board sends the work back to the implementer with the comment |
| `comment SOU-8 "text"` | Board comment without a decision. Refused on a `backlog` issue assigned to an agent, because it would wake the agent and start the task |
| `cancel SOU-8 "reason"` | Cancel an issue that is no longer needed (duplicate, obsolete); also stops its pending runs |
| `assign SOU-8 game-designer [--status backlog]` | Reassign; agents match by name, url key or id. Never starts the task: a `backlog` issue stays `backlog`. An issue that already started (`todo`, `in_progress`, `in_review`, `blocked`) is refused unless `--status backlog` parks it; then `release` it. `--status todo` is refused |
| `create --title … --assignee … [--project …] [--desc … / --desc-file …] [--review qa] [--no-approval]` | New issue, always in `backlog` (`--status todo` is refused), with a Board approval stage. Each `--review` adds an agent review stage before it. Start it with `release` |
| `wake qa-engineer [--issue SOU-8]` | Start an agent run now. Refused with `--issue` on a `backlog` issue |
| `cancel-run <run-id>` | Stop a queued or running run |
| `review-pack <KEY> --source-fixture F --state-file S --allow-repo o/r` · `review-pack <KEY> --github-pr N --github-repo o/r --task-file T --state-file S --allow-repo o/r` · `review-pack --status\|--unstage [--abandon]\|--cleanup --state-file S` | **OQ-042 review packager.** Builds and stages a review package from fixture files (Phase 1) or from a PR over the GitHub API with the packager token (Phase 3, below). Never calls Paperclip or git |
| `review-relay <KEY> --run-id R [--identity local-board]` | **OQ-042 Verdict Relay (Phase 4a).** Checks a finished `code-reviewer` run against the staged package, the issue's stage participant and the live PR head, then posts the findings with a relay receipt and records the decision. Refusals, including a Paperclip error before anything is recorded, are audited and leave the Board fallback (`approve` / `request-changes`). Accepts only the run `review-start` recorded for the staging's review sub-issue, whose log shows exactly the tools Read, Grep and Glob and no other tool use or refused attempt, and a verdict carrying the staging's `reviewId` and `challenge` (Option B). Run it only when the Board asks |
| `review-start <KEY> [--identity local-board]` | **OQ-042 Option B.** For the staged review: creates the review sub-issue (child of `<KEY>`, assigned to `code-reviewer`, backlog, no project) and wakes the reviewer on demand for it; records both in the staging lock. Refuses a non-staged issue or an issue not waiting on the relay identity. Refuses unless `code-reviewer` has the write-free profile (no `env`; `--restricted --tools Read,Grep,Glob --disallowedTools mcp__* --permission-mode dontAsk`, one `--add-dir` = the staging folder, settings allowing exactly Read/Grep/Glob and denying `mcp__*`). Safe to run again after an interruption: it adopts the sub-issue or run an earlier attempt created, never creates a second one or wakes twice, and stops with instructions when it cannot tell (design §3.3). A leftover `staging.op` after a crash is deleted by hand. Not yet run live; run it only when the Board asks |

## Rules

- **Board decisions need the user's words.** Run `approve`, `request-changes`, `release` and `cancel` only when the user has clearly asked for that action on that issue in chat. Quote their decision in the comment, for example "Approved by the Board Operator: …".
- **Releasing spends money and quota.** Before releasing several tasks, say which agents will start. `show` lists an issue's blockers ("blocked by"). Release an issue only after its blockers are `done`; whether Paperclip itself holds back a released issue with open blockers is unverified.
- **Approving in Paperclip does not merge on GitHub.** ADR-009 requires both. Game repository PRs are authored by the same account, so merging needs the owner's admin bypass: `gh pr merge <n> --repo datpham02/<game> --merge --admin`. Since 2026-11-04 the Board Operator allows Claude to run it for `datpham02/lamplight-vigil` (allow rule in the gitignored `.claude/settings.local.json`). Run it only when all of these hold: the issue is approved in Paperclip; the user asked in chat to merge that PR; and `gh pr view` shows it mergeable. Merge one PR per command, then confirm with `gh pr view <n> --json state`. For any other repository, give the user the command instead. After the user merges, update the game repo's local `main` (`git -C ~/game-studio-workspace/repos/<game> pull --ff-only origin main`). New task worktrees branch from it.
- **A comment is not a decision.** In Paperclip, the Board approves by setting `done` with a comment (`approve`). Comments alone leave the issue waiting.
- Never change agent permissions, adapters, secrets or company settings through this skill. Those are configuration changes. Discuss them first and record them in the docs (security-architecture.md §4).

- **Daily triage.** When the user asks what is stuck or what needs them, run `triage` first and lead with "Needs the Board". Suggest it once per working day.

## Review packager, Phase 1 (`review-pack`, OQ-042)

Implements Phase 1 of [docs/design/review-package.md](../../../docs/design/review-package.md) (design still `PROPOSED`). Code: `scripts/review_pack.py`; tests: `scripts/test_review_pack.py`, run as part of `test_pc.py`.

- **Inputs are fixture files only.**
  - `--source-fixture` holds PR data in the `review-source-fixture@1` shape (blobs as base64; each blob's git id is recomputed).
  - `--state-file` holds issue and run state in the `review-state-fixture@1` shape, standing in for Paperclip.
  - Phase 1 never runs git, reads a repository or worktree, calls GitHub or Paperclip, or uses a token.
- **Roots.** `--review-root` and `--staging-root` (or `COMPANY_OS_REVIEW_ROOT` / `COMPANY_OS_STAGING_ROOT`) are required. They must be absolute, separate, not nested, and outside every Git repository. Nothing is written elsewhere.
- **`review-pack <KEY>`** validates everything first (design §5.2 and §5.3) and fails closed:
  - it builds `store/<KEY>/<head>/` atomically, with `READY` last, or reuses an intact one;
  - it then stages a verified copy in `<Staging Root>/current/` under an exclusive `staging.lock`;
  - each staging gets a random `reviewId` and `challenge`, written only to `current/REVIEW-ID.txt` (checked by SHA-256 from the lock);
  - it prints the `pc.py review-start <KEY>` command; it never runs it.
- **One review at a time.** Another issue, or another head, is refused while staging is held.
  - `--status` shows the lock, its runs and whether it is stale (run finished, or no run for 24 h).
  - `--unstage` asks Paperclip (through `pc.py`) for every run of the `code-reviewer` agent and the lock's run by id (R2). An active run (`queued`, `scheduled_retry`, `running`), whenever it started, refuses even with `--abandon`: cancel it first. Since staging, `interrupted`, an unknown status, a mismatched run or any Paperclip error is "unverified" and refuses unless `--abandon` (logged as unverified). It also refuses while the review has not been relayed, unless `--abandon`. It takes `staging.op`, checks twice around an `unstaging` mark, and deletes the lock last. The state file is no longer used by `--unstage`. `--status` through `pc.py` reports the same Paperclip view (`source: paperclip`, `verified`, the reviewer's runs) and hides the staging challenge; only outside `pc.py` does it fall back to the state file (`source: state-file`). When Paperclip does not answer, `--status` through `pc.py` reports `verified: false` with the reason and never falls back to the state file, which cannot see Option B reviewer runs. Refusals of `--unstage`/`--status` are audited with the staged issue.
- **`--cleanup`** removes packages of issues `done` or `cancelled` for 14+ days, oldest first. It never touches an open issue's package or the staged one. Deletion is two-step through `store/.trash`, and failures are logged and retried. A build over the 2 GB cap first cleans up, then refuses. Through `pc.py`, `--cleanup` and the cap cleanup read each issue's status and `closedAt` from Paperclip (B2), not the state file. A package is kept, with an audit `cleanup-skipped` line, when Paperclip does not answer, returns another issue's record, or shows a closed issue without a readable `closedAt`.
- **Audit:** `<Review Root>/audit.log`, append-only JSON lines, rotated by size and never deleted. A damaged line makes `--status` and `--unstage` refuse until it is repaired.
- **Hardening (audit 2026-11-20):**
  - links: a symlink or junction under either root is refused, never followed;
  - one build per issue at a time (`store/<KEY>/.build.lock`; a lock older than 60 minutes is taken over and logged);
  - names shaped like 8.3 short names are refused;
  - manifest paths are re-validated;
  - filesystem errors become logged refusals;
  - `REVIEW.md` quotes Task text after the fixed instructions.
- **Not a security boundary:** every agent runs as the same Windows user and can read or change both roots. G-13 stays open.

### Phase 3: GitHub source (`--github-pr`)

Code: `scripts/review_github.py`; tests: `scripts/test_review_github.py` (an in-memory fake GitHub, run as part of `test_pc.py`).

- **What it reads** (design §4 option A, reads only):
  - the PR (`head.sha`, `base.sha`, `changed_files`);
  - the compare endpoint (merge base);
  - every page of the PR file list (100 per page, until empty; the count must match);
  - the trees at head and at the merge base (refused if GitHub truncates them);
  - each blob by SHA;
  - the PR again at the end. If the head moved, the build is refused.
- **Verification:** every blob's git id is recomputed by the packager, and §5.2/§5.3 apply unchanged.
- **Diff:** `patch.diff` is built from the blobs; GitHub's `patch` field is never used.
- **Refused:** submodule changes, unsupported file statuses, and blobs GitHub does not return.
- **Task data** comes from `--task-file` (`review-task@1`: `issue` and `task`), standing in for Paperclip.
- **Token** (design §6): a fine-grained read-only token in Windows Credential Manager under the generic credential `company-os/review-packager`.
  - It is sent only in the `Authorization` header and redacted from every error.
  - 401/403 refuse with no fallback.
  - A token that expires within 14 days triggers a warning.
  - The Board creates and stores it; the skill never asks for it in chat.
- **Repository:** `--github-repo` must also be an `--allow-repo`.

## Start gate: only `release` starts a task

Creating or assigning a task never starts it; only `release` does, after its hard guards. Safe sequence: `create` (backlog, assignee set, nobody woken) → check its description (Write Set, criteria) and stages with `show --description` → `release`. Paperclip 2026.1023.0 wakes an agent when an issue is created or reassigned outside `backlog`, when it leaves `backlog`, and on any comment by someone other than the assignee (unless done or cancelled). So `create` and `assign` keep or put the issue in `backlog`, and `comment` and `wake --issue` refuse an unreleased issue. `--force` does not apply to these refusals.

Not covered (Paperclip-native, outside this skill): the Paperclip UI; agents' MCP `create_task` (always `todo` or `blocked`, assigned to the calling agent unless it names another, parented to its current issue, and inheriting that run's workspace); agents' `paperclip-issue-update.sh --status` and direct API calls (Cursor profiles have no allowlist). Paperclip has an access-control action `tasks:assign` and plugin events (`issue.created`, observe-only); neither is configured or used here.

## WIP limit (`release`, `triage`)

Each agent holds at most **one `in_progress` issue across all projects of the company** (task-contract.md §5). `release` refuses an issue whose assignee already has one, naming it; `--force` never skips this. Rules:

- Only status `in_progress` counts. `in_review`, `blocked`, `todo` and `backlog` do not, so a reviewer still gets review wakes while it has its own task. Issues assigned to the Board or another user count against no agent.
- In one `release` command, an issue released earlier takes its agent's slot (it is `todo`, not yet `in_progress`), so the next issue for that agent is refused. An issue refused by a guard takes no slot; one released with `--force` does.
- Any failure to read the full in_progress list refuses the release ("WIP could not be verified"); `triage` prints "COULD NOT CHECK WIP" instead of "(none)".
- Issue lists are read page by page with Paperclip's keyset cursor (`sortField=id&sortDir=asc&afterId=…`, 1000 per page) until an empty page, for WIP, the Write Set guard and `triage`.
- Not atomic: two release commands started at the same moment can both pass. `maxConcurrentRuns` is unchanged (still 20); runtime enforcement waits for OQ-041.

## Write Set conflict guard (`release`)

Every `release` compares the issue's `## Write set` with the Write Set of every unmerged issue of the **same project**, and refuses the release on any overlap, listing each conflicting issue and path. `--force` never skips it, and it changes nothing when it refuses. Rules (task-contract.md §4.1; code and comments in `scripts/pc.py`):

- **Format:** list items under `## Write set` (or `## Files owned …`), one path per item in backticks, relative to the project repository; globs `*`, `?`, `[…]`, `**` allowed; a single item `none` means no files. A folder covers everything inside it. Comparison ignores case (Windows). `..`, absolute paths and unclosed backticks are refused.
- **Unmerged:** `todo`, `in_progress`, `in_review`, `blocked` and unknown statuses; `backlog` only once it has its own execution workspace; `done` until Paperclip shows the merge (workspace `deliveryState` `merged_via_pr` / `merged_by_ancestry`, or archived by Paperclip's reaper, `cleanupReason` `issue_terminal`). A `done` issue with no execution workspace is not compared. `cancelled` is ignored.
- **Refused as well:** a candidate with no project or no readable Write Set, an unmerged issue whose Write Set cannot be read, and any failure to read Paperclip.
- **A merged PR still blocks** when Paperclip cannot see the merge: update the project repository's local `main` (`git pull --ff-only origin main`) so `merged_by_ancestry` applies.
- Fix a refusal by narrowing a Write Set or adding a blocker relation and releasing after the merge. The guard never creates blockers or edits other issues.
- Tests: `python -I .claude/skills/paperclip/scripts/test_pc.py` (no Paperclip needed).

## Known behaviour (see docs/architecture/stage1-gap-analysis.md)

- **G-1 / OQ-035:** a reviewer is not woken after an in-run hand-off. The watchdog (`runtime/tools/review-wake-watchdog.ts`) wakes it after about 90 s. If an issue sits `in_review` on an agent with no run, check the watchdog is running, or `wake` the reviewer.
- **G-8:** agents cannot read other issues or the agent list. Put source-of-truth text in the game repository (`docs/concept.md`, `docs/vision.md`), or paste it into the issue description or a Board comment.
- **G-9:** issues created by agents through the MCP `create_task` tool start as `todo` and run at once. After an agent plans tasks, check them with `overview` and move any of them back with `assign <KEY> <agent> --status backlog`.
- **G-10:** an issue created inside another issue's run inherits that run's worktree and branch, so two tasks can end up sharing one worktree. `release` detects this and switches the issue to its own isolated worktree first. Agent-created tasks also have **no review or approval stages**; add them before releasing (QA review for code, Director for design, then Board approval).
- **`assign` clears a Board (user) assignee.** Paperclip allows only one assignee, so an issue parked on the Board after a stuck review is handed back with `assign <KEY> <agent> --status backlog`, then `release <KEY>`. Whether Paperclip allows every status (for example `in_review`) to move to `backlog` is `UNVERIFIED`; an API refusal is shown as an error.
- An agent may park a released task again if an older Board comment says "not released". Post a fresh Board comment that it is released.
- **A Board `comment` wakes the assignee, even on a `backlog` issue** (verified in Paperclip 2026.1023.0; the comment API has no "do not wake" option), and the agent starts the task. `comment` therefore refuses an agent-assigned `backlog` issue; release it first, or put the note in its description.
- **Cursor QA often posts a verdict without recording the decision**, and Paperclip then moves the issue to `blocked` at the review stage. `approve` refuses there. When the user accepts QA's written verdict, record it as a manual resolution: PATCH the issue to `done` with a comment that quotes the user and names the QA verdict. When QA requested changes, hand the issue back with `assign <KEY> <implementer> --status backlog`, then `release <KEY>`, then a Board `comment` with the changes; the review stages stay in place.
- A reviewer must not edit, rebase or push the implementer's branch. If one does, discard that local work and send the task back to the implementer.
- A run that ends with `scheduled_retry` and keeps retrying usually means the agent could not report. Read `log`, then `cancel-run` the retry if it is looping.
- The live company is **Soucean**, issue prefix `SOU` (since 2026-11-05, ADR-018). The former company "Game Studio Soucean" (`GAM`) is archived (2026-11-05); its open work was recreated as SOU-1 to SOU-10, and a full export is in `~/game-studio-workspace/archive/`. `pc.py` picks Soucean by default; pass `--company GAM` for the archive. Task branches are `<KEY>-<slug>`, in worktrees under `<project repo>/.paperclip/worktrees/`.
