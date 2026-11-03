# ADR-009: Approval Before Git Merge

- **Status:** Accepted
- **Date:** 2026-11-03
- **Deciders:** Board Operator
- **Related:** ADR-006, [code-review-and-merge.md](../../workflows/code-review-and-merge.md), [security-architecture.md](../architecture/security-architecture.md), OQ-005, OQ-016

## Context
AI agents produce code changes autonomously. Unreviewed merges into a game's Default Branch could introduce defects, security problems, or destructive changes.

## Decision
- No agent and no automated component MAY modify a Game Repository's Default Branch directly.
- Changes reach the Default Branch only through a pull request from a Task Branch.
- A merge MUST NOT happen without an approval by the Board Operator (or a human the Board Operator delegates to) recorded **both**:
  1. in Paperclip, as the approval stage of the Task's execution policy or an approval record, and
  2. on the GitHub pull request, as an approving review or a merge performed by that human.
- Agents MAY review pull requests and request changes; an agent review MUST NOT count as the merge approval.
- Execution logs and the Task ↔ Branch ↔ Pull Request mapping MUST be preserved.
- GitHub branch protection SHOULD enforce this technically on every Game Repository's Default Branch.

## Alternatives considered
| Alternative | Why not chosen |
|---|---|
| Auto-merge when tests pass | Tests do not cover design intent or security. |
| Agent (e.g. `qa`) approval sufficient | Agents share failure modes; human oversight required in v1. |

## Consequences
- The Board Operator is a throughput bottleneck by design.
- Who presses "merge" (human in GitHub UI vs. Runtime after approval) is open (OQ-016). Until resolved, the human merges in GitHub.

## Reconsider when
- Test and review automation is mature enough to allow auto-merge of low-risk change classes, with an explicit policy approved by ADR.
