// Tests for board-queue-rules.ts. Run: node --test runtime/tools/board-queue-rules.test.ts
import { test } from "node:test";
import assert from "node:assert/strict";
import { autoReleaseCheck, classifyBoardWait, endedWaits, hasAutoReleaseMarker, parseReleaseOutput, type BoardIssue } from "./board-queue-rules.ts";

const MARK = "Auto-release: approved by the Board 2026-11-21 (M1 plan).";

function issue(over: Partial<BoardIssue> = {}): BoardIssue {
  return { id: "i1", identifier: "SOU-40", title: "Task", status: "backlog", assigneeAgentId: "ag-1", description: `${MARK}\n\n## Goal\nx`, blockedBy: [], ...over };
}

test("an approval stage waiting on a user is a Board wait", () => {
  const w = classifyBoardWait(issue({
    status: "in_review",
    executionState: { status: "pending", currentStageId: "s2", currentStageType: "approval", currentParticipant: { type: "user", userId: "local-board" } },
  }));
  assert.equal(w?.key, "board_wait:i1:s2");
  assert.match(w!.message, /SOU-40 waits for the Board's approval: Task/);
});

test("agent reviews, decided stages and other statuses are not Board waits", () => {
  const agentStage = { status: "pending", currentStageId: "s1", currentParticipant: { type: "agent" as const, agentId: "qa" } };
  const decided = { status: "changes_requested", currentStageId: "s2", currentParticipant: { type: "user" as const, userId: "b" } };
  const userPending = { status: "pending", currentStageId: "s2", currentParticipant: { type: "user" as const, userId: "b" } };
  assert.equal(classifyBoardWait(issue({ status: "in_review", executionState: agentStage })), null);
  assert.equal(classifyBoardWait(issue({ status: "in_review", executionState: decided })), null);
  assert.equal(classifyBoardWait(issue({ status: "in_progress", executionState: userPending })), null);
  assert.equal(classifyBoardWait(issue({ status: "in_review", executionState: null })), null);
});

test("an ended wait is forgotten so a re-entry notifies again", () => {
  assert.deepEqual(endedWaits(new Set(["board_wait:a:s", "board_wait:b:s"]), new Set(["board_wait:b:s"])), ["board_wait:a:s"]);
});

test("the marker counts only as the first non-empty line", () => {
  assert.equal(hasAutoReleaseMarker(`\n\n${MARK}\nrest`), true);
  assert.equal(hasAutoReleaseMarker(`## Goal\n${MARK}`), false);
  assert.equal(hasAutoReleaseMarker("Auto-release: approved by someone"), false);
  assert.equal(hasAutoReleaseMarker(null), false);
});

test("a marked backlog task with done blockers is eligible", () => {
  assert.deepEqual(autoReleaseCheck(issue({ blockedBy: [{ identifier: "SOU-39", status: "done" }] })), { eligible: true });
  assert.deepEqual(autoReleaseCheck(issue()), { eligible: true });
});

test("unmarked, started, unassigned or blocked tasks are not eligible", () => {
  const cases: [Partial<BoardIssue>, RegExp][] = [
    [{ description: "## Goal\nx" }, /no auto-release marker/],
    [{ status: "todo" }, /status todo/],
    [{ assigneeAgentId: null }, /no agent assignee/],
    [{ blockedBy: [{ identifier: "SOU-39", status: "in_review" }, { identifier: "SOU-38", status: "done" }] }, /blockers not done: SOU-39$/],
    [{ blockedBy: [{ identifier: "SOU-16", status: "cancelled" }] }, /SOU-16/],
  ];
  for (const [over, want] of cases) {
    const r = autoReleaseCheck(issue(over));
    assert.equal(r.eligible, false);
    assert.match((r as { reason: string }).reason, want);
  }
});

test("pc.py release output is parsed", () => {
  assert.deepEqual(parseReleaseOutput("SOU-40", "SOU-40: released -> todo (the assignee is woken now)\n"), { released: true, detail: "SOU-40: released -> todo (the assignee is woken now)" });
  const refused = parseReleaseOutput("SOU-41", "SOU-41: not released: assignee already has SOU-40 in progress (WIP limit 1, all projects); --force does not override this check. Nothing was changed.\n");
  assert.equal(refused.released, false);
  assert.match(refused.detail, /WIP limit/);
  assert.equal(parseReleaseOutput("SOU-42", "").detail, "no output");
});
