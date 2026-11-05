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
| `show SOU-8 [--comments N] [--description]` | One issue: status, assignee, current stage, blockers, branch, latest comments, runs |
| `log <run-id> [--tail N]` | Output of one run; take run ids from `show` |
| `triage` | Read-only daily sweep (knowledge/company/workflows/daily-triage.md): what needs the Board, blocked issues and whether they name an unblock owner, stalled reviews, quiet tasks, ready backlog, agents over WIP 1 |
| `release SOU-8 [SOU-9 …] [--force]` | `backlog` → `todo`. **The assignee starts working immediately and spends usage.** Refuses an issue with no write set, no review/approval stage, open blockers, or a busy assignee; `--force` only on the user's explicit word |
| `approve SOU-8 "comment"` | Board approval: sets `done` with the comment. Only works while the issue waits on the Board |
| `request-changes SOU-8 "comment"` | Board sends the work back to the implementer with the comment |
| `comment SOU-8 "text"` | Board comment without a decision |
| `cancel SOU-8 "reason"` | Cancel an issue that is no longer needed (duplicate, obsolete); also stops its pending runs |
| `assign SOU-8 game-designer [--status backlog]` | Reassign; agents match by name, url key or id |
| `create --title … --assignee … [--project …] [--desc … / --desc-file …] [--review qa] [--no-approval] [--status todo]` | New issue. Defaults: `backlog`, then a Board approval stage. Each `--review` adds an agent review stage before it |
| `wake qa-engineer [--issue SOU-8]` | Start an agent run now |
| `cancel-run <run-id>` | Stop a queued or running run |

## Rules

- **Board decisions need the user's words.** Run `approve`, `request-changes`, `release`, `cancel` and `create --status todo` only when the user has clearly asked for that action on that issue in chat. Quote their decision in the comment, for example "Approved by the Board Operator: …".
- **Releasing spends money and quota.** Before releasing several tasks, say which agents will start. `show` lists an issue's blockers ("blocked by"). Release an issue only after its blockers are `done`; whether Paperclip itself holds back a released issue with open blockers is unverified.
- **Approving in Paperclip does not merge on GitHub.** ADR-009 requires both. Game repository PRs are authored by the same account, so merging needs the owner's admin bypass: `gh pr merge <n> --repo datpham02/<game> --merge --admin`. Since 2026-11-04 the Board Operator allows Claude to run it for `datpham02/lamplight-vigil` (allow rule in the gitignored `.claude/settings.local.json`). Run it only when all of these hold: the issue is approved in Paperclip; the user asked in chat to merge that PR; and `gh pr view` shows it mergeable. Merge one PR per command, then confirm with `gh pr view <n> --json state`. For any other repository, give the user the command instead. After the user merges, update the game repo's local `main` (`git -C ~/game-studio-workspace/repos/<game> pull --ff-only origin main`). New task worktrees branch from it.
- **A comment is not a decision.** In Paperclip, the Board approves by setting `done` with a comment (`approve`). Comments alone leave the issue waiting.
- Never change agent permissions, adapters, secrets or company settings through this skill. Those are configuration changes. Discuss them first and record them in the docs (security-architecture.md §4).

- **Daily triage.** When the user asks what is stuck or what needs them, run `triage` first and lead with "Needs the Board". Suggest it once per working day.

## Known behaviour (see docs/architecture/stage1-gap-analysis.md)

- **G-1 / OQ-035:** a reviewer is not woken after an in-run hand-off. The watchdog (`runtime/tools/review-wake-watchdog.ts`) wakes it after about 90 s. If an issue sits `in_review` on an agent with no run, check the watchdog is running, or `wake` the reviewer.
- **G-8:** agents cannot read other issues or the agent list. Put source-of-truth text in the game repository (`docs/concept.md`, `docs/vision.md`), or paste it into the issue description or a Board comment.
- **G-9:** issues created by agents through the MCP `create_task` tool start as `todo` and run at once. After an agent plans tasks, check them with `overview` and move any of them back with `assign <KEY> <agent> --status backlog`.
- **G-10:** an issue created inside another issue's run inherits that run's worktree and branch, so two tasks can end up sharing one worktree. `release` detects this and switches the issue to its own isolated worktree first. Agent-created tasks also have **no review or approval stages**; add them before releasing (QA review for code, Director for design, then Board approval).
- **`assign` clears a Board (user) assignee.** Paperclip allows only one assignee, so an issue parked on the Board after a stuck review can be handed back with `assign <KEY> <agent> --status todo`.
- An agent may park a released task again if an older Board comment says "not released". Post a fresh Board comment that it is released.
- **A Board `comment` wakes the assignee, even on a `backlog` issue**, and the agent starts the task. Comment only on issues that may start now, and treat such a comment as a release.
- **Cursor QA often posts a verdict without recording the decision**, and Paperclip then moves the issue to `blocked` at the review stage. `approve` refuses there. When the user accepts QA's written verdict, record it as a manual resolution: PATCH the issue to `done` with a comment that quotes the user and names the QA verdict. When QA requested changes, reassign the issue to its implementer with status `todo` and a Board comment; the review stages stay in place.
- A reviewer must not edit, rebase or push the implementer's branch. If one does, discard that local work and send the task back to the implementer.
- A run that ends with `scheduled_retry` and keeps retrying usually means the agent could not report. Read `log`, then `cancel-run` the retry if it is looping.
- The live company is **Soucean**, issue prefix `SOU` (since 2026-11-05, ADR-018). The former company "Game Studio Soucean" (`GAM`) is archived (2026-11-05); its open work was recreated as SOU-1 to SOU-10, and a full export is in `~/game-studio-workspace/archive/`. `pc.py` picks Soucean by default; pass `--company GAM` for the archive. Task branches are `<KEY>-<slug>`, in worktrees under `<project repo>/.paperclip/worktrees/`.
