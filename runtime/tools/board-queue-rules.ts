/**
 * Board-queue and auto-release rules for the studio watchdog (pure functions, no I/O;
 * tested by board-queue-rules.test.ts). ADR-023.
 *
 * 1. Board queue. An issue whose current execution stage waits on a user (the Board's
 *    review or approval stage) needs the Board Operator, who does not watch the Paperclip
 *    dashboard. The watchdog shows one Windows toast per waiting episode.
 * 2. Auto-release. The Board may pre-approve the start of a backlog Task by putting the
 *    marker line `Auto-release: approved by the Board <date>` at the top of its
 *    description. When all its blockers are done, the watchdog runs the Paperclip skill's
 *    `pc.py release <KEY>`, which keeps every hard guard (WIP, read-only assignee, Write
 *    Set conflicts, stages). Unmarked Tasks are never released by the watchdog.
 */

export type Participant = { type: "agent" | "user"; agentId?: string | null; userId?: string | null };
export type BoardIssue = {
  id: string;
  identifier: string;
  title?: string;
  status: string;
  description?: string | null;
  assigneeAgentId?: string | null;
  executionState?: { status?: string; currentStageId?: string | null; currentStageType?: string | null; currentParticipant?: Participant | null } | null;
  blockedBy?: { identifier?: string | null; status?: string | null }[] | null;
};

/** The marker must be the description's first non-empty line, so the truncated issue list still shows it. */
export const AUTO_RELEASE_MARKER = /^\s*Auto-release: approved by the Board\b/i;

export type BoardWait = { key: string; message: string };

/** The issue waits on a user participant (the Board) at its current execution stage. */
export function classifyBoardWait(issue: BoardIssue): BoardWait | null {
  const state = issue.executionState;
  const participant = state?.currentParticipant;
  if (issue.status !== "in_review" || state?.status !== "pending" || participant?.type !== "user") return null;
  const stage = state.currentStageType ?? "review";
  return {
    key: `board_wait:${issue.id}:${state.currentStageId ?? "stage"}`,
    message: `${issue.identifier} waits for the Board's ${stage === "approval" ? "approval" : "review"}${issue.title ? `: ${issue.title}` : ""}`,
  };
}

/** Keys notified earlier whose episode has ended (the issue no longer waits), so a later re-entry notifies again. */
export function endedWaits(notified: Iterable<string>, current: Set<string>): string[] {
  return [...notified].filter((k) => !current.has(k));
}

export function hasAutoReleaseMarker(description: string | null | undefined): boolean {
  const first = (description ?? "").split(/\r?\n/).find((l) => l.trim() !== "");
  return first !== undefined && AUTO_RELEASE_MARKER.test(first);
}

export type ReleaseCheck = { eligible: true } | { eligible: false; reason: string };

/** Whether the watchdog may ask `pc.py release` to start this issue. pc.py still runs every hard guard. */
export function autoReleaseCheck(issue: BoardIssue): ReleaseCheck {
  if (issue.status !== "backlog") return { eligible: false, reason: `status ${issue.status}` };
  if (!hasAutoReleaseMarker(issue.description)) return { eligible: false, reason: "no auto-release marker" };
  if (!issue.assigneeAgentId) return { eligible: false, reason: "no agent assignee" };
  const open = (issue.blockedBy ?? []).filter((b) => b.status !== "done");
  if (open.length) return { eligible: false, reason: `blockers not done: ${open.map((b) => b.identifier ?? "?").join(", ")}` };
  return { eligible: true };
}

/** Outcome of one `pc.py release <KEY>` call, from its output. */
export function parseReleaseOutput(key: string, output: string): { released: boolean; detail: string } {
  const lines = output.split(/\r?\n/).filter((l) => l.trim() !== "");
  const released = lines.some((l) => l.startsWith(`${key}: released`));
  const detail = (lines.find((l) => l.startsWith(`${key}:`)) ?? lines[lines.length - 1] ?? "no output").trim();
  return { released, detail };
}
