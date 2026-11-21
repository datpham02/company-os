# ADR-023: Watchdog Board-Queue Notices and Board-Pre-Approved Auto-Release

- **Status:** Accepted
- **Date:** 2026-11-21
- **Deciders:** Board Operator
- **Related:** ADR-011 (Stage 2 gap fillers), OQ-035, OQ-048; [task-contract.md](../../knowledge/company/standards/task-contract.md) §2, [runtime-management.md](../operations/runtime-management.md) §1.1, [Paperclip skill](../../.claude/skills/paperclip/SKILL.md)

## Context
The Board Operator does not watch the Paperclip dashboard. On 2026-11-21, during Deckbound initialization, two gaps showed:

1. **Nobody tells the Board when work waits on it.** An issue that reaches the Board's review or approval stage just sits there. The watchdog notified the Board only for stuck issues, not for normal approval waits.
2. **Release is a manual step for every Task.** Milestone M1 has 25 Tasks linked by blocker relations, and the Board approved the whole plan at once. Releasing each Task by hand as its dependencies merge meant the work stalled whenever the Board was away.

A session-only check-in loop in one Claude session covered both gaps for a day, but it died with the session and lived outside the framework.

Paperclip 2026.1023.0 does not wake a `backlog` dependent when its blockers resolve (checked in the server's `listWakeableBlockedDependents`), so blocker relations alone start nothing.

## Decision
The studio watchdog (`runtime/tools/review-wake-watchdog.ts`, started by `start-studio.cmd`) gains two features. Both are on by default and have off switches.

**1. Board-queue notices (`--no-board-queue` to turn off).**
- An issue counts as waiting for the Board when its status is `in_review`, its execution stage is `pending`, and the current participant is a user.
- The watchdog writes a `BOARD` console line and shows one Windows toast per waiting episode. A new episode starts when the issue leaves that state and later comes back.
- It only notifies; it never decides.

**2. Board-pre-approved auto-release (`--no-auto-release` to turn off).**
- The Board pre-approves the start of a backlog Task by making the **first line** of its description:
  `Auto-release: approved by the Board <date> (<reason>)`.
  Only the Board Operator, or Claude acting on the Board's request in chat, adds this line.
- The watchdog releases a marked Task only when all of these hold: it is in `backlog`, it has an agent assignee, and every blocker is `done`.
- It releases by running `pc.py release <KEY>`, so **every release guard still applies**: the WIP limit, the read-only assignee guard, Write Set conflicts (which also wait for the merge on GitHub), stages and blockers. It never passes `--force`.
- A refusal is logged once until its reason changes. The watchdog retries on the next sweep.
- A release shows a Windows toast.

**Unchanged.**
- Unmarked Tasks start only through a Board `release`.
- Approvals, requests for changes and merges stay with the Board. The watchdog never approves, comments, merges or cancels.

## Consequences
- The task-contract start gate now reads: only `release` starts a Task, run by the Board or, for marked Tasks, by the watchdog on the Board's behalf.
- A marked Task can start while the Board is away and spend usage. The Board controls this by choosing which Tasks to mark, and it can stop it by deleting the marker line or by running the watchdog with `--no-auto-release`.
- The watchdog now depends on Python and the Paperclip skill script (`pc.py`) in the same repository checkout.
- Notifications are Windows toasts on the studio machine (Board's choice, 2026-11-21). Nothing is sent off the machine.
- What the watchdog already notified is kept in memory (ADR-010). A restart may notify again for an issue that is still waiting.
