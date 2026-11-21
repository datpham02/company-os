/**
 * Stuck-issue rules for the watchdog (pure functions, no I/O; tested by stuck-rules.test.ts).
 *
 * Paperclip 2026.1023.0 hands a stuck issue to the Board (a recovery action with
 * ownerType "board", or status `blocked`) but tells no one, and company heartbeats are
 * off, so no role notices either. These rules decide which open issues need attention.
 * The watchdog acts on the result: it notifies the Board, and for an idle assignee it
 * first wakes that agent once.
 */

export type Participant = { type: "agent" | "user"; agentId?: string | null; userId?: string | null };
export type ExecutionState = { status?: string; currentStageId?: string | null; currentParticipant?: Participant | null };
export type RecoveryAction = {
  id: string;
  status: string;
  ownerType: string;
  cause?: string | null;
  nextAction?: string | null;
  updatedAt?: string | null;
};
export type Issue = {
  id: string;
  identifier: string;
  title?: string;
  status: string;
  updatedAt: string;
  assigneeAgentId?: string | null;
  executionState?: ExecutionState | null;
  activeRecoveryAction?: RecoveryAction | null;
  scheduledRetry?: unknown;
  blockedBy?: { status?: string | null }[] | null;
};
export type Run = { agentId: string; status: string; createdAt: string; finishedAt?: string | null };

export type StuckKind = "board_recovery" | "retry_loop" | "blocked" | "idle";
export type Finding = {
  kind: StuckKind;
  /** Stable for one stuck episode; the watchdog acts once per key. */
  key: string;
  message: string;
  /** Set only for `idle`: the agent to wake once before the Board is told. */
  wakeAgentId?: string;
};
export type Options = { idleSec: number; blockedGraceSec: number; retryLoopCount: number; wakeCooldownSec: number };

/** Run statuses that mean the issue is being worked on or will be retried by Paperclip. */
export const ACTIVE_RUN = new Set(["queued", "starting", "running", "scheduled_retry"]);
/** Run statuses that count towards a retry loop (UNVERIFIED: the full status list is not documented). */
const FAILED_RUN = new Set(["failed", "timed_out", "error", "scheduled_retry"]);
const OPEN_RECOVERY = new Set(["active", "escalated"]);
const CLOSED_ISSUE = new Set(["done", "cancelled"]);
/** Agent statuses for which a wake is pointless or unwanted. */
const NO_WAKE_AGENT = new Set(["paused", "terminated", "running"]);

function ms(value: string | null | undefined): number {
  const t = value ? Date.parse(value) : NaN;
  return Number.isFinite(t) ? t : 0;
}

/**
 * Classify one open issue. Returns null when nothing needs attention.
 * `runs` are the issue's runs (any order); `agentStatus` is the assignee's status, if any.
 */
export function classifyStuck(issue: Issue, runs: Run[], agentStatus: string | null, nowMs: number, opts: Options): Finding | null {
  if (CLOSED_ISSUE.has(issue.status) || issue.status === "backlog") return null;
  const label = `${issue.identifier}${issue.title ? ` "${issue.title}"` : ""}`;

  // 1. Paperclip gave up and made the Board the recovery owner.
  const rec = issue.activeRecoveryAction;
  if (rec && OPEN_RECOVERY.has(rec.status) && rec.ownerType === "board") {
    return {
      kind: "board_recovery",
      key: `board_recovery:${rec.id}:${rec.updatedAt ?? ""}`,
      message: `${label}: Paperclip recovery is waiting on the Board (${rec.cause ?? "no cause given"}). Next action: ${rec.nextAction ?? "inspect the issue"}`,
    };
  }

  const sorted = [...runs].sort((a, b) => ms(b.createdAt) - ms(a.createdAt));

  // 2. The assignee's last runs all failed or keep retrying.
  if (issue.assigneeAgentId && opts.retryLoopCount > 0) {
    const own = sorted.filter((r) => r.agentId === issue.assigneeAgentId).slice(0, opts.retryLoopCount);
    if (own.length === opts.retryLoopCount && own.every((r) => FAILED_RUN.has(r.status))) {
      return {
        kind: "retry_loop",
        key: `retry_loop:${issue.id}:${own[0].createdAt}`,
        message: `${label}: the assignee's last ${own.length} runs failed or are retrying (${own.map((r) => r.status).join(", ")}). Read the run log; cancel the retry if it loops`,
      };
    }
  }

  if (sorted.some((r) => ACTIVE_RUN.has(r.status))) return null;
  const lastActivity = Math.max(ms(issue.updatedAt), ...sorted.slice(0, 1).map((r) => ms(r.finishedAt) || ms(r.createdAt)));

  // 3. Blocked with no open blocker issue: someone (usually the Board) has to act.
  if (issue.status === "blocked") {
    const openBlocker = (issue.blockedBy ?? []).some((b) => !CLOSED_ISSUE.has(b.status ?? ""));
    if (openBlocker || nowMs - lastActivity < opts.blockedGraceSec * 1000) return null;
    return {
      kind: "blocked",
      key: `blocked:${issue.id}:${issue.updatedAt}`,
      message: `${label}: blocked with no open blocker issue and no run. Read its latest comments for the ask`,
    };
  }

  // 4. Started work whose assignee has gone quiet.
  if ((issue.status === "todo" || issue.status === "in_progress") && issue.assigneeAgentId) {
    if (issue.scheduledRetry) return null;
    if (agentStatus && NO_WAKE_AGENT.has(agentStatus)) return null;
    if (nowMs - lastActivity < opts.idleSec * 1000) return null;
    return {
      kind: "idle",
      key: `idle:${issue.id}:${issue.updatedAt}`,
      message: `${label}: ${issue.status} with no run for ${Math.round((nowMs - lastActivity) / 60000)} min`,
      wakeAgentId: issue.assigneeAgentId,
    };
  }
  return null;
}

export type Action = { type: "wake"; agentId: string } | { type: "notify" } | { type: "none" };

/**
 * Decide what to do for a finding.
 * - `notified`: the Board was already told about this key (one notice per stuck episode).
 * - `lastWakeAt`: when the watchdog last woke this issue's assignee, in any episode.
 * An idle issue gets one wake per `wakeCooldownSec`; if it is idle again `idleSec` after that
 * wake, the Board is told instead. This stops an agent that only bumps the issue (new key)
 * from being woken over and over. Every other kind notifies the Board once per key.
 */
export function decide(finding: Finding, notified: boolean, lastWakeAt: number | undefined, nowMs: number, opts: Options): Action {
  if (notified) return { type: "none" };
  if (finding.kind !== "idle" || !finding.wakeAgentId) return { type: "notify" };
  if (lastWakeAt === undefined || nowMs - lastWakeAt >= opts.wakeCooldownSec * 1000) return { type: "wake", agentId: finding.wakeAgentId };
  return nowMs - lastWakeAt >= opts.idleSec * 1000 ? { type: "notify" } : { type: "none" };
}
