# Stage 1 Gap Analysis

**Status:** living document, started 2026-11-04. ADR-011 Stage 1 runs the studio on Paperclip's own adapters. This file lists the requirements Paperclip did not meet in practice, and what Game Studio does about each one. Stage 2 Runtime code is written **only** for gaps listed here.

| # | Gap | Evidence | Response | Status |
|---|---|---|---|---|
| G-1 | The reviewer is not woken when an agent hands an issue to a review stage from inside its own run | OQ-035 (GAM-3, GAM-4) | [`runtime/tools/review-wake-watchdog.ts`](../../runtime/tools/review-wake-watchdog.ts) wakes the pending agent participant through the public API | `IMPLEMENTED` workaround; report upstream |
| G-2 | `claude_local` on the default ACP engine approves every tool request | OQ-011, C-002 | Configuration only: Claude CLI engine profile with allowlist and reporting rule ([security-architecture.md](security-architecture.md) §4) | Resolved by configuration |
| G-3 | Isolated per-task worktrees sit behind an experimental instance flag | OQ-002 | Configuration only: `enableIsolatedWorkspaces` on; re-check on every Paperclip upgrade | Resolved by configuration |
| G-4 | Paperclip approvals are not linked to GitHub PR review or merge | OQ-005 | Manual two-step approval (ADR-009) | Accepted for v1 |
| G-5 | Task branches are named `<ISSUE-KEY>-<slug>`, not `agent/<agent-id>/<task-key>` | OQ-004 | Accept Paperclip's naming; allowlists use `GAM-*` | Accepted |
| G-6 | Onboarding wizard sign-in needs Python's Unix-only `pty` on Windows | OQ-031 | Import the company instead of using the wizard | Worked around |
| G-7 | `npx`-started server leaks `npm_*` variables into agents | OQ-034 | Global install, `paperclipai run` | Resolved by operation |
| G-8 | Confined agents cannot read Paperclip data beyond their own issue: other issues, the agent list. Every API read needs `$PAPERCLIP_API_KEY`, which the permission layer refuses | GAM-5 (pillars drifted from GAM-1), GAM-7 (tasks created with the wrong assignee) | Keep source-of-truth documents in the Game Repository (`docs/concept.md`, `docs/vision.md`); the Board fixes assignments. Candidate: a read-only helper script for issue and agent lookups, allowlisted like `paperclip-issue-update.sh` | Open |
| G-9 | `create_task` (Paperclip MCP) creates issues as `todo` even when `backlog` is requested, so an assigned task starts at once | GAM-7 (GAM-9 started a run) | Board returns such tasks to `backlog`; planning tasks should create issues unassigned | Open |

## Related documents
[../decisions/ADR-011-execution-path-selection.md](../decisions/ADR-011-execution-path-selection.md) · [open-questions.md](open-questions.md) · [runtime-architecture.md](runtime-architecture.md)
