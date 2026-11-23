# Pull Request Delivery & Review

Status: `APPROVED` (Board policy, 2026-11-23). Describes **how** repository-change delivery MUST look once commit/push is authorized.

Related: root [AGENTS.md](../../../AGENTS.md) §3 rule 8 · [rules.md](rules.md) R1–R3 · [code-review-and-merge.md](../workflows/code-review-and-merge.md) · [ADR-009](../../../docs/decisions/ADR-009-approval-before-merge.md) · [ADR-010](../../../docs/decisions/ADR-010-runtime-data-outside-repository.md)

## 0. Precedence and authorization trigger

| Layer | Role |
|---|---|
| Root `AGENTS.md` §3 rule 8 | **Wins on commit/push.** No commit or push unless the human (Board Operator) **explicitly asks** for that delivery. |
| This policy | Defines the **mandatory shape** of delivery after that ask: dedicated feature branch, write-set only, Draft PR, no merge. |
| Task write set / R1–R2 | Still bound every change. Board approval of investigation alone does **not** authorize commits. |

**Authorization trigger (exact):** the Board or human must explicitly request repository delivery for the task — for example “open a Draft PR”, “commit and push on a feature branch”, or “file these docs under pull-request-delivery”. Citing this policy in a Board task that names Draft PR delivery counts as that ask **for the named write set and feature branch only**.

Mere Board approval of a read-only audit, pilot, or research task does **not** authorize commit/push. Exploratory work with no repository deliverable reports findings without commits ([§4](#4-audit-and-research-tasks)).

## 1. Mandatory delivery workflow (when authorized)

When §0 authorizes repository delivery for a task that produces repository changes, finish with a GitHub Pull Request:

1. Identify the correct target repository.
2. Create a dedicated feature branch (never the Default Branch).
3. Complete only the authorized write-set work.
4. Run relevant validations and tests.
5. Commit changes to the feature branch.
6. Push the branch.
7. Open a **Draft** Pull Request against the appropriate base branch.
8. Return the PR URL to the Board.

Do **not** merge automatically ([ADR-009](../../../docs/decisions/ADR-009-approval-before-merge.md)).

## 2. Pull Request requirements

Every PR MUST contain:

### Summary

- Objective and scope.
- Changes implemented.
- Important decisions.

### Evidence

- Tests executed and their results (or “manual only — no CI on this head”).
- Relevant logs or review artifacts.
- Screenshots or animation previews where appropriate.
- Exact limitations and unverified claims.
- Versioned docs MUST use logical identifiers only ([ADR-010](../../../docs/decisions/ADR-010-runtime-data-outside-repository.md)); machine paths, ports, PIDs and local config stay in untracked local evidence.

### Dependencies

- Skills, tools and knowledge used.
- Any new dependencies proposed.
- Required approvals.

### Board Review

- What the Board should inspect.
- Open questions.
- Explicit GO / NO-GO decision points.

## 3. Repository boundaries

**Company OS**

- Organization policies.
- Knowledge Delivery.
- Agent roles and skills.
- Dependency management.
- Capability routing.
- Integration design and documentation.

**Game repositories**

- Game code.
- Art assets.
- Animation assets.
- Godot scenes.
- Game-specific experiments.

Do not commit secrets, credentials, machine-specific private information, Runtime Data, or unrelated local files ([rules.md](rules.md) R4; [ADR-010](../../../docs/decisions/ADR-010-runtime-data-outside-repository.md)).

## 4. Audit and research tasks

For read-only audits that produce documentation intended to become part of the repository:

1. Perform the investigation without altering production.
2. Obtain an explicit §0 delivery ask before committing.
3. Place sanitised deliverable reports on an appropriate documentation branch (logical IDs only).
4. Open a Draft PR for Board review.

Creating documentation PRs does **not** authorize deployment or implementation of the recommendations.

For purely exploratory tasks with no repository deliverable, report findings without forcing meaningless commits.

## 5. Approval boundaries

When §0 authorizes Draft PR delivery, that ask covers: creating a feature branch, committing the named write set, pushing that branch, and opening a **Draft** PR.

It does **not** authorize:

- Merging (Board only, ADR-009).
- Production deployment.
- Installing new dependencies.
- Changing runtime permissions.
- Executing previously restricted workflows.
- Commits outside the Task write set.
- Force-push or Default Branch writes.

If GitHub access or repository permissions block PR creation, report the exact blocker rather than claiming completion.

## 6. Final response format

Always finish authorized repository-change tasks with:

- Repository
- Branch
- PR URL
- Changed files
- Test / validation results
- Board decision required

Delivery is not complete until the PR exists or a verified blocker is reported.
