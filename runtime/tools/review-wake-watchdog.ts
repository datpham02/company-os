/**
 * Review-wake watchdog (Stage 2 gap filler, ADR-011; OQ-033).
 *
 * Paperclip 2026.1023.0 does not wake the next execution-stage participant when the
 * previous agent hands an issue to review from inside its own run: the hand-off cancels
 * that run (`issue_reassigned`) and the reviewer's wakeup never becomes a run. This
 * watchdog finds issues stuck in `in_review` whose current participant is an agent
 * with no run since the stage started, and wakes that agent through Paperclip's public
 * API (`POST /api/agents/{id}/wakeup`). It never changes issue state.
 *
 * Run with Node 24+ (native TypeScript type stripping), next to Paperclip:
 *   node runtime/tools/review-wake-watchdog.ts            # loop, every 60 s
 *   node runtime/tools/review-wake-watchdog.ts --once     # single sweep
 * Options: --api <url> (default http://127.0.0.1:3100/api), --company <id> (default: all),
 *          --interval <s> (default 60), --grace <s> (default 90).
 * Requires Paperclip in local_trusted mode on loopback (Board context without login).
 */

type Participant = { type: "agent" | "user"; agentId?: string | null; userId?: string | null };
type ExecutionState = { status?: string; currentStageId?: string | null; currentParticipant?: Participant | null };
type Issue = { id: string; identifier: string; status: string; updatedAt: string; executionState?: ExecutionState | null };
type Run = { agentId: string; status: string; createdAt: string };

function option(name: string, fallback: string): string {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
}

const api = option("api", "http://127.0.0.1:3100/api").replace(/\/$/, "");
const onlyCompany = option("company", "");
const intervalSec = Number(option("interval", "60"));
const graceSec = Number(option("grace", "90"));
const once = process.argv.includes("--once");
const ACTIVE = new Set(["queued", "starting", "running"]);

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

async function sweepCompany(companyId: string): Promise<void> {
  const inReview = await request<Issue[]>("GET", `/companies/${companyId}/issues?status=in_review`);
  for (const summary of inReview) {
    // The list endpoint omits executionState, so read each issue.
    const issue = await request<Issue>("GET", `/issues/${summary.id}`);
    const state = issue.executionState;
    const participant = state?.currentParticipant;
    if (issue.status !== "in_review" || state?.status !== "pending" || participant?.type !== "agent" || !participant.agentId) continue;

    const stageStarted = Date.parse(issue.updatedAt);
    if (Date.now() - stageStarted < graceSec * 1000) continue;

    const runs = await request<Run[]>("GET", `/issues/${issue.id}/runs`);
    const reviewerRuns = runs.filter((r) => r.agentId === participant.agentId);
    if (reviewerRuns.some((r) => ACTIVE.has(r.status) || Date.parse(r.createdAt) >= stageStarted)) continue;

    await request("POST", `/agents/${participant.agentId}/wakeup?companyId=${companyId}`, {
      source: "assignment",
      triggerDetail: "system",
      reason: "review_stage_wake_watchdog",
      payload: { issueId: issue.id },
      // One wake per stage entry; Paperclip deduplicates on this key.
      idempotencyKey: `review-wake:${issue.id}:${state.currentStageId ?? "stage"}:${issue.updatedAt}`,
    });
    log(`woke reviewer ${participant.agentId} for ${issue.identifier} (in review since ${issue.updatedAt})`);
  }
}

async function sweep(): Promise<void> {
  const companyIds = onlyCompany
    ? [onlyCompany]
    : (await request<{ id: string; status: string }[]>("GET", "/companies")).filter((c) => c.status === "active").map((c) => c.id);
  for (const id of companyIds) {
    try {
      await sweepCompany(id);
    } catch (err) {
      log(`sweep failed for company ${id}: ${(err as Error).message}`);
    }
  }
}

log(`review-wake watchdog: api=${api} interval=${intervalSec}s grace=${graceSec}s${once ? " (once)" : ""}`);
await sweep();
if (!once) setInterval(() => void sweep(), intervalSec * 1000);
