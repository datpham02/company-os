// Tests for stuck-rules.ts. Run: node --test runtime/tools/stuck-rules.test.ts
import { test } from "node:test";
import assert from "node:assert/strict";
import { classifyDeadRun, classifyStuck, decide, type Issue, type Run } from "./stuck-rules.ts";

const opts = { idleSec: 900, blockedGraceSec: 600, retryLoopCount: 3, wakeCooldownSec: 21600, deadSilenceSec: 1200 };
const T0 = Date.parse("2026-11-21T10:00:00Z");
const at = (min: number) => new Date(T0 + min * 60000).toISOString();
const AGENT = "agent-gp";

function issue(over: Partial<Issue> = {}): Issue {
  return { id: "i1", identifier: "SOU-31", status: "todo", updatedAt: at(0), assigneeAgentId: AGENT, ...over };
}
const run = (status: string, min: number, agentId = AGENT): Run => ({ agentId, status, createdAt: at(min), finishedAt: at(min + 1) });
const now = (min: number) => T0 + min * 60000;

test("closed and backlog issues are never stuck", () => {
  for (const status of ["done", "cancelled", "backlog"]) assert.equal(classifyStuck(issue({ status }), [], "idle", now(999), opts), null);
});

test("recovery owned by the Board notifies, even with an active run", () => {
  const rec = { id: "r1", status: "active", ownerType: "board", cause: "unchanged_source_state_exhausted", nextAction: "repair", updatedAt: at(1) };
  const f = classifyStuck(issue({ status: "in_progress", activeRecoveryAction: rec }), [run("running", 2)], "running", now(3), opts);
  assert.equal(f?.kind, "board_recovery");
  assert.equal(f?.key, `board_recovery:r1:${at(1)}`);
  assert.match(f!.message, /unchanged_source_state_exhausted/);
  assert.equal(f?.wakeAgentId, undefined);
  assert.deepEqual(decide(f!, false, undefined, now(3), opts), { type: "notify" });
});

test("recovery owned by an agent, or resolved, is not a Board finding", () => {
  const agentRec = { id: "r1", status: "active", ownerType: "agent", updatedAt: at(1) };
  assert.equal(classifyStuck(issue({ activeRecoveryAction: agentRec }), [run("running", 2)], "running", now(3), opts), null);
  const resolved = { id: "r1", status: "resolved", ownerType: "board", updatedAt: at(1) };
  assert.equal(classifyStuck(issue({ activeRecoveryAction: resolved }), [run("running", 2)], "running", now(3), opts), null);
});

test("three failed or retrying runs of the assignee are a retry loop", () => {
  const runs = [run("failed", 1), run("scheduled_retry", 5), run("timed_out", 3), run("succeeded", 0)];
  const f = classifyStuck(issue({ status: "in_progress" }), runs, "idle", now(6), opts);
  assert.equal(f?.kind, "retry_loop");
  assert.equal(f?.key, `retry_loop:i1:${at(5)}`);
});

test("a success among the last runs, or another agent's failures, is no retry loop", () => {
  const mixed = [run("failed", 1), run("succeeded", 2), run("failed", 3)];
  assert.equal(classifyStuck(issue({ status: "in_progress" }), mixed, "idle", now(4), opts), null);
  const other = [run("failed", 1, "qa"), run("failed", 2, "qa"), run("failed", 3, "qa")];
  assert.equal(classifyStuck(issue({ status: "in_progress" }), other, "idle", now(4), opts), null);
});

test("an active run means the issue is being worked on", () => {
  assert.equal(classifyStuck(issue(), [run("queued", 0)], "idle", now(999), opts), null);
  assert.equal(classifyStuck(issue({ status: "blocked" }), [run("running", 0)], "idle", now(999), opts), null);
});

test("blocked with no open blocker notifies after the grace period", () => {
  const b = issue({ status: "blocked", updatedAt: at(0) });
  assert.equal(classifyStuck(b, [], "idle", now(9), opts), null);
  const f = classifyStuck(b, [], "idle", now(11), opts);
  assert.equal(f?.kind, "blocked");
  assert.deepEqual(decide(f!, false, undefined, now(11), opts), { type: "notify" });
});

test("blocked on an open blocker issue is waiting, not stuck; a done blocker no longer counts", () => {
  assert.equal(classifyStuck(issue({ status: "blocked", blockedBy: [{ status: "in_progress" }] }), [], "idle", now(999), opts), null);
  assert.equal(classifyStuck(issue({ status: "blocked", blockedBy: [{ status: "done" }] }), [], "idle", now(999), opts)?.kind, "blocked");
});

test("the grace period counts from the last run, not only the issue update", () => {
  const b = issue({ status: "blocked", updatedAt: at(0) });
  assert.equal(classifyStuck(b, [run("succeeded", 5)], "idle", now(12), opts), null); // run finished at 6 min
  assert.equal(classifyStuck(b, [run("succeeded", 5)], "idle", now(17), opts)?.kind, "blocked");
});

test("todo or in_progress with no run for idleSec is idle and wakes the assignee", () => {
  assert.equal(classifyStuck(issue(), [], "idle", now(14), opts), null);
  const f = classifyStuck(issue({ status: "in_progress" }), [], "idle", now(16), opts);
  assert.equal(f?.kind, "idle");
  assert.equal(f?.wakeAgentId, AGENT);
});

test("idle is skipped for a paused or busy agent, a scheduled retry, or no agent assignee", () => {
  for (const s of ["paused", "terminated", "running"]) assert.equal(classifyStuck(issue(), [], s, now(999), opts), null);
  assert.equal(classifyStuck(issue({ scheduledRetry: { at: at(20) } }), [], "idle", now(999), opts), null);
  assert.equal(classifyStuck(issue({ assigneeAgentId: null }), [], null, now(999), opts), null);
  assert.equal(classifyStuck(issue({ status: "in_review" }), [], "idle", now(999), opts), null);
});

test("decide: one wake, then the Board if still idle, then silence", () => {
  const f = classifyStuck(issue(), [], "idle", now(16), opts)!;
  assert.deepEqual(decide(f, false, undefined, now(16), opts), { type: "wake", agentId: AGENT });
  // Woken at 16 min: give it idleSec before telling the Board.
  assert.deepEqual(decide(f, false, now(16), now(20), opts), { type: "none" });
  assert.deepEqual(decide(f, false, now(16), now(31), opts), { type: "notify" });
  assert.deepEqual(decide(f, true, now(16), now(60), opts), { type: "none" });
});

test("decide: a new idle episode within the cooldown goes to the Board, not another wake", () => {
  const f = classifyStuck(issue({ updatedAt: at(40) }), [], "idle", now(60), opts)!;
  assert.deepEqual(decide(f, false, now(16), now(60), opts), { type: "notify" });
  // After the cooldown, a fresh wake is allowed.
  assert.deepEqual(decide(f, false, now(16), now(16 + 361), opts), { type: "wake", agentId: AGENT });
});

test("a recorded notice is never repeated for the same key", () => {
  const f = classifyStuck(issue({ status: "blocked" }), [], "idle", now(11), opts)!;
  assert.deepEqual(decide(f, true, undefined, now(11), opts), { type: "none" });
});

test("a running run whose process is gone is a dead run, after a short grace", () => {
  const detail = { status: "running", processPid: 24976, startedAt: at(0), lastOutputAt: at(10) };
  assert.equal(classifyDeadRun(issue(), "run-1", detail, false, now(11), opts), null);
  const f = classifyDeadRun(issue(), "run-1", detail, false, now(13), opts);
  assert.equal(f?.kind, "dead_run");
  assert.equal(f?.key, "dead_run:run-1");
  assert.match(f!.message, /process 24976 is gone/);
  assert.match(f!.message, /cancel-run run-1/);
  assert.equal(f?.wakeAgentId, undefined);
  assert.deepEqual(decide(f!, false, undefined, now(13), opts), { type: "notify" });
  assert.deepEqual(decide(f!, true, undefined, now(14), opts), { type: "none" });
});

test("a live process is dead only after the silence limit", () => {
  const detail = { status: "running", processPid: 1, startedAt: at(0), lastOutputAt: at(10), execution: { lastConfirmedActivityAt: at(12) } };
  assert.equal(classifyDeadRun(issue(), "run-1", detail, true, now(31), opts), null);
  const f = classifyDeadRun(issue(), "run-1", detail, true, now(32), opts);
  assert.match(f!.message, /no output for 20 min/);
  assert.equal(classifyDeadRun(issue(), "run-1", detail, null, now(32), opts)?.kind, "dead_run");
  assert.equal(classifyDeadRun(issue(), "run-1", detail, true, now(999), { ...opts, deadSilenceSec: 0 }), null);
});

test("only starting or running runs can be dead", () => {
  for (const status of ["queued", "scheduled_retry", "succeeded", "cancelled", "failed"]) {
    assert.equal(classifyDeadRun(issue(), "run-1", { status, processPid: 1, startedAt: at(0) }, false, now(999), opts), null);
  }
  assert.equal(classifyDeadRun(issue(), "run-1", { status: "starting" }, false, now(999), opts), null);
});
