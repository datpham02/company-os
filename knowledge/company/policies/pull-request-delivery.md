# Pull Request Delivery & Review

Status: `APPROVED` (Board policy, 2026-11-23). Applies to every Board-approved task that produces repository changes.

Related: [rules.md](rules.md) R1–R3 · [code-review-and-merge.md](../workflows/code-review-and-merge.md) · [ADR-009](../../../docs/decisions/ADR-009-approval-before-merge.md)

## 1. Mandatory delivery workflow

Every Board-approved task that produces repository changes MUST finish with a GitHub Pull Request.

1. Identify the correct target repository.
2. Create a dedicated feature branch.
3. Complete the authorized work.
4. Run relevant validations and tests.
5. Commit changes to the feature branch.
6. Push the branch.
7. Open a **Draft** Pull Request against the appropriate base branch.
8. Return the PR URL to the Board.

Do **not** merge automatically.

## 2. Pull Request requirements

Every PR MUST contain:

### Summary

- Objective and scope.
- Changes implemented.
- Important decisions.

### Evidence

- Tests executed and their results.
- Relevant logs or review artifacts.
- Screenshots or animation previews where appropriate.
- Exact limitations and unverified claims.

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

Do not commit secrets, credentials, machine-specific private information, or unrelated local files ([rules.md](rules.md) R4; [ADR-010](../../../docs/decisions/ADR-010-runtime-data-outside-repository.md)).

## 4. Audit and research tasks

For read-only audits that produce documentation intended to become part of the repository:

1. Perform the investigation without altering production.
2. Place the deliverable reports in an appropriate documentation branch.
3. Include reproducible evidence and source references.
4. Open a Draft PR for Board review.

Creating documentation PRs does **not** authorize deployment or implementation of the recommendations.

For purely exploratory tasks with no repository deliverable, report findings without forcing meaningless commits.

## 5. Approval boundaries

Board authorization to create a PR includes creating a branch, committing and pushing the authorized changes.

It does **not** authorize:

- Merging.
- Production deployment.
- Installing new dependencies.
- Changing runtime permissions.
- Executing previously restricted workflows.

If GitHub access or repository permissions block PR creation, report the exact blocker rather than claiming completion.

## 6. Final response format

Always finish repository-change tasks with:

- Repository
- Branch
- PR URL
- Changed files
- Test / validation results
- Board decision required

Delivery is not complete until the PR exists or a verified blocker is reported.
