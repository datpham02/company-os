---
name: paperclip
description: Operate the Game Studio's Paperclip instance for the Board Operator from chat. Use it to see what agents and issues are doing, read issue comments and run logs, release backlog tasks, approve or send back work awaiting the Board, create and assign tasks, wake agents and cancel runs. Use it whenever the user mentions Paperclip, an issue key such as GAM-12, an agent role (game-director, qa, …), a milestone, approving, releasing, or "what is the studio doing".
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
| `show GAM-8 [--comments N] [--description]` | One issue: status, assignee, current stage, blockers, branch, latest comments, runs |
| `log <run-id> [--tail N]` | Output of one run; take run ids from `show` |
| `release GAM-8 [GAM-9 …]` | `backlog` → `todo`. **The assignee starts working immediately and spends usage.** |
| `approve GAM-8 "comment"` | Board approval: sets `done` with the comment. Only works while the issue waits on the Board |
| `request-changes GAM-8 "comment"` | Board sends the work back to the implementer with the comment |
| `comment GAM-8 "text"` | Board comment without a decision |
| `assign GAM-8 game-designer [--status backlog]` | Reassign; agents match by name, url key or id |
| `create --title … --assignee … [--project …] [--desc … / --desc-file …] [--review qa] [--no-approval] [--status todo]` | New issue. Defaults: `backlog`, then a Board approval stage. Each `--review` adds an agent review stage before it |
| `wake qa-engineer [--issue GAM-8]` | Start an agent run now |
| `cancel-run <run-id>` | Stop a queued or running run |

## Rules

- **Board decisions need the user's words.** Run `approve`, `request-changes`, `release` and `create --status todo` only when the user has clearly asked for that action on that issue in chat. Quote their decision in the comment, for example "Approved by the Board Operator: …".
- **Releasing spends money and quota.** Before releasing several tasks, say which agents will start. `show` lists an issue's blockers ("blocked by"). Release an issue only after its blockers are `done`; whether Paperclip itself holds back a released issue with open blockers is unverified.
- **Approving in Paperclip does not merge on GitHub.** ADR-009 requires both. Game repository PRs are authored by the same account, so merging needs the owner's admin bypass. Claude must not run it. Give the user the command instead: `gh pr merge <n> --repo datpham02/<game> --merge --admin`. After the user merges, update the game repo's local `main` (`git -C ~/game-studio-workspace/repos/<game> pull --ff-only origin main`). New task worktrees branch from it.
- **A comment is not a decision.** In Paperclip, the Board approves by setting `done` with a comment (`approve`). Comments alone leave the issue waiting.
- Never change agent permissions, adapters, secrets or company settings through this skill. Those are configuration changes. Discuss them first and record them in the docs (security-architecture.md §4).

## Known behaviour (see docs/architecture/stage1-gap-analysis.md)

- **G-1 / OQ-035:** a reviewer is not woken after an in-run hand-off. The watchdog (`runtime/tools/review-wake-watchdog.ts`) wakes it after about 90 s. If an issue sits `in_review` on an agent with no run, check the watchdog is running, or `wake` the reviewer.
- **G-8:** agents cannot read other issues or the agent list. Put source-of-truth text in the game repository (`docs/concept.md`, `docs/vision.md`), or paste it into the issue description or a Board comment.
- **G-9:** issues created by agents through the MCP `create_task` tool start as `todo` and run at once. After an agent plans tasks, check them with `overview` and move any of them back with `assign <KEY> <agent> --status backlog`.
- A run that ends with `scheduled_retry` and keeps retrying usually means the agent could not report. Read `log`, then `cancel-run` the retry if it is looping.
- Issue keys use the company prefix (`GAM`). Task branches are `<KEY>-<slug>`, in worktrees under `<game repo>/.paperclip/worktrees/`.
