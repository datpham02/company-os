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

## Related documents
[../decisions/ADR-011-execution-path-selection.md](../decisions/ADR-011-execution-path-selection.md) · [open-questions.md](open-questions.md) · [runtime-architecture.md](runtime-architecture.md)
