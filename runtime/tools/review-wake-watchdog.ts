/**
 * Studio watchdog (Stage 2 gap filler, ADR-011): review wakes (OQ-035) and stuck-issue alerts (OQ-048).
 *
 * 1. Review wakes. Paperclip 2026.1023.0 does not wake the next execution-stage participant
 *    when the previous agent hands an issue to review from inside its own run: the hand-off
 *    cancels that run (`issue_reassigned`) and the reviewer's wakeup never becomes a run. The
 *    watchdog finds issues stuck in `in_review` whose current participant is an agent with no
 *    run since the stage started, and wakes that agent.
 * 2. Stuck issues. Paperclip hands a stuck issue to the Board (a recovery action owned by
 *    "board", or `blocked`) without telling anyone, and company heartbeats are off, so no role
 *    notices. Each sweep classifies open issues with stuck-rules.ts:
 *      - recovery owned by the Board, a run retry loop, or `blocked` with no open blocker:
 *        notify the Board once per episode;
 *      - `todo`/`in_progress` with an assignee that has had no run for --idle seconds: wake the
 *        assignee once (at most once per --wake-cooldown per issue); if it is idle again after
 *        that, notify the Board.
 *    A notice is a console line starting with "ATTENTION" plus a Windows toast.
 *
 * It only reads issues and calls `POST /api/agents/{id}/wakeup`; it never changes issue state
 * or posts comments. What it already did is kept in memory, so a restart may notify again.
 *
 * Run with Node 24+ (native TypeScript type stripping), next to Paperclip:
 *   node runtime/tools/review-wake-watchdog.ts            # loop, every 60 s
 *   node runtime/tools/review-wake-watchdog.ts --once     # single sweep
 * Options: --api <url> (default http://127.0.0.1:3100/api), --company <id> (default: all),
 *          --interval <s> (60), --grace <s> (90, review wakes),
 *          --idle <s> (900), --blocked-grace <s> (600), --retry-loop <n> (3), --wake-cooldown <s> (21600),
 *          --no-stuck (review wakes only), --no-toast (console only), --dry-run (log, do not wake or toast).
 * Requires Paperclip in local_trusted mode on loopback (Board context without login).
 */

import { spawn } from "node:child_process";
import { classifyStuck, decide, type Issue, type Options, type Run } from "./stuck-rules.ts";

function option(name: string, fallback: string): string {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
}
const flag = (name: string) => process.argv.includes(`--${name}`);

const api = option("api", "http://127.0.0.1:3100/api").replace(/\/$/, "");
const onlyCompany = option("company", "");
const intervalSec = Number(option("interval", "60"));
const graceSec = Number(option("grace", "90"));
const once = flag("once");
const stuckEnabled = !flag("no-stuck");
const toastEnabled = !flag("no-toast");
const dryRun = flag("dry-run");
const stuckOpts: Options = {
  idleSec: Number(option("idle", "900")),
  blockedGraceSec: Number(option("blocked-grace", "600")),
  retryLoopCount: Number(option("retry-loop", "3")),
  wakeCooldownSec: Number(option("wake-cooldown", "21600")),
};
const REVIEW_ACTIVE = new Set(["queued", "starting", "running"]);

// What the watchdog already did, in memory only (ADR-010: no run state in the repository).
const notifiedKeys = new Set<string>();
const lastWakeByIssue = new Map<string, number>();

function log(message: string): void {
  console.log(`${new Date().toISOString()} ${message}`);
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(api + path, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${method} ${path} -> ${res.status} ${(await res.text()).slice(0, 200)}`);
  return (await res.json()) as T;
}

/** Windows toast through Windows PowerShell 5.1; text goes through environment variables, never the command line. */
function toast(title: string, body: string): void {
  if (!toastEnabled || dryRun || process.platform !== "win32") return;
  const script = [
    "$ErrorActionPreference = 'Stop'",
    "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null",
    "$x = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)",
    "$t = $x.GetElementsByTagName('text')",
    "$t.Item(0).AppendChild($x.CreateTextNode($env:WATCHDOG_TOAST_TITLE)) > $null",
    "$t.Item(1).AppendChild($x.CreateTextNode($env:WATCHDOG_TOAST_BODY)) > $null",
    "$app = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe'",
    "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app).Show([Windows.UI.Notifications.ToastNotification]::new($x))",
  ].join("; ");
  const child = spawn("powershell.exe", ["-NoProfile", "-NonInteractive", "-EncodedCommand", Buffer.from(script, "utf16le").toString("base64")], {
    env: { ...process.env, WATCHDOG_TOAST_TITLE: title.slice(0, 120), WATCHDOG_TOAST_BODY: body.slice(0, 400) },
    windowsHide: true,
    stdio: "ignore",
  });
  child.on("error", (err) => log(`toast failed: ${err.message}`));
  child.on("exit", (code) => code && log(`toast failed: powershell exit ${code}`));
}

async function wake(agentId: string, companyId: string, issueId: string, reason: string, idempotencyKey: string): Promise<void> {
  if (dryRun) return;
  await request("POST", `/agents/${agentId}/wakeup?companyId=${companyId}`, {
    source: "assignment",
    triggerDetail: "system",
    reason,
    payload: { issueId },
    idempotencyKey, // Paperclip deduplicates on this key.
  });
}

async function listIssues(companyId: string, statuses: string): Promise<Issue[]> {
  const rows: Issue[] = [];
  let after = "";
  for (;;) {
    const q = new URLSearchParams({ status: statuses, limit: "1000", sortField: "id", sortDir: "asc" });
    if (after) q.set("afterId", after);
    const page = await request<Issue[]>("GET", `/companies/${companyId}/issues?${q}`);
    if (!Array.isArray(page) || page.length === 0) return rows;
    if (after && page[0].id <= after) throw new Error("issue list did not advance");
    rows.push(...page);
    after = page[page.length - 1].id;
  }
}

async function reviewWakes(companyId: string, issues: Issue[], runsOf: (id: string) => Promise<Run[]>): Promise<void> {
  for (const issue of issues) {
    const state = issue.executionState;
    const participant = state?.currentParticipant;
    if (issue.status !== "in_review" || state?.status !== "pending" || participant?.type !== "agent" || !participant.agentId) continue;

    const stageStarted = Date.parse(issue.updatedAt);
    if (Date.now() - stageStarted < graceSec * 1000) continue;

    const reviewerRuns = (await runsOf(issue.id)).filter((r) => r.agentId === participant.agentId);
    if (reviewerRuns.some((r) => REVIEW_ACTIVE.has(r.status) || Date.parse(r.createdAt) >= stageStarted)) continue;

    // One wake per stage entry.
    await wake(participant.agentId, companyId, issue.id, "review_stage_wake_watchdog", `review-wake:${issue.id}:${state.currentStageId ?? "stage"}:${issue.updatedAt}`);
    log(`${dryRun ? "[dry-run] would wake" : "woke"} reviewer ${participant.agentId} for ${issue.identifier} (in review since ${issue.updatedAt})`);
  }
}

async function stuckSweep(companyId: string, companyName: string, issues: Issue[], runsOf: (id: string) => Promise<Run[]>): Promise<void> {
  const agents = await request<{ id: string; name: string; status: string }[]>("GET", `/companies/${companyId}/agents`);
  const agentById = new Map(agents.map((a) => [a.id, a]));
  const now = Date.now();
  for (const issue of issues) {
    const agentStatus = issue.assigneeAgentId ? agentById.get(issue.assigneeAgentId)?.status ?? null : null;
    const finding = classifyStuck(issue, await runsOf(issue.id), agentStatus, now, stuckOpts);
    if (!finding) continue;
    const action = decide(finding, notifiedKeys.has(finding.key), lastWakeByIssue.get(issue.id), now, stuckOpts);
    if (action.type === "wake") {
      await wake(action.agentId, companyId, issue.id, "stuck_issue_watchdog", `stuck-wake:${finding.key}`);
      lastWakeByIssue.set(issue.id, now);
      log(`${dryRun ? "[dry-run] would wake" : "woke"} ${agentById.get(action.agentId)?.name ?? action.agentId}: ${finding.message}`);
    } else if (action.type === "notify") {
      notifiedKeys.add(finding.key);
      const extra = finding.kind === "idle" ? " (already woken once; still idle)" : "";
      log(`ATTENTION [${finding.kind}] ${companyName}: ${finding.message}${extra}`);
      toast(`${companyName}: ${issue.identifier} needs the Board`, finding.message + extra);
    }
  }
}

async function sweepCompany(companyId: string, companyName: string): Promise<void> {
  const statuses = stuckEnabled ? "todo,in_progress,in_review,blocked" : "in_review";
  // The list endpoint omits executionState, recovery and blockers, so read each issue.
  const issues = await Promise.all((await listIssues(companyId, statuses)).map((s) => request<Issue>("GET", `/issues/${s.id}`)));
  const runCache = new Map<string, Promise<Run[]>>();
  const runsOf = (id: string) => {
    if (!runCache.has(id)) runCache.set(id, request<Run[]>("GET", `/issues/${id}/runs`));
    return runCache.get(id)!;
  };
  await reviewWakes(companyId, issues, runsOf);
  if (stuckEnabled) await stuckSweep(companyId, companyName, issues, runsOf);
}

async function sweep(): Promise<void> {
  let companies: { id: string; name: string; status: string }[];
  try {
    companies = (await request<{ id: string; name: string; status: string }[]>("GET", "/companies")).filter((c) =>
      onlyCompany ? c.id === onlyCompany : c.status === "active",
    );
  } catch (err) {
    log(`cannot reach Paperclip: ${(err as Error).message}`);
    return;
  }
  for (const c of companies) {
    try {
      await sweepCompany(c.id, c.name);
    } catch (err) {
      log(`sweep failed for company ${c.name} (${c.id}): ${(err as Error).message}`);
    }
  }
}

log(
  `studio watchdog: api=${api} interval=${intervalSec}s grace=${graceSec}s` +
    (stuckEnabled ? ` stuck(idle=${stuckOpts.idleSec}s blocked=${stuckOpts.blockedGraceSec}s retry-loop=${stuckOpts.retryLoopCount} cooldown=${stuckOpts.wakeCooldownSec}s toast=${toastEnabled})` : " stuck=off") +
    (dryRun ? " (dry-run)" : "") +
    (once ? " (once)" : ""),
);
await sweep();
if (!once) setInterval(() => void sweep(), intervalSec * 1000);
