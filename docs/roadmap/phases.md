# Implementation Roadmap

**Status:** `PROPOSED`. Ordered so that nothing is built before the facts it depends on are verified, and nothing Paperclip already provides is rebuilt (ADR-002, ADR-011).

## Phase 0: Environment and verification (no Game Studio code)

| # | Action | Closes |
|---|---|---|
| 0.1 | Put the Framework Repository under Git and push to `datpham02/game-studio` (Board). Done 2026-11-03 | OQ-028 |
| 0.2 | Install the standalone Codex CLI; `codex login`; probe `codex exec` | OQ-009, OQ-010 |
| 0.3 | Install Paperclip on the Windows studio machine (`npx paperclipai onboard --yes`, `local_trusted`), pin the version | OQ-008, OQ-024, OQ-031 |
| 0.4 | Create a scratch company + scratch Game Repository (throwaway, private) | — |
| 0.5 | Experiment: `process` agent printing redacted `PAPERCLIP_*` env, `pwd`, branch; note which shell runs it on Windows | OQ-001, OQ-003, OQ-032 |
| 0.6 | Experiment: isolated `git_worktree` execution workspace with 2 concurrent Tasks; record paths, branch names, cleanup | OQ-002, OQ-004, OQ-030 |
| 0.7 | Experiment: Claude Code and Codex headless runs per permission profile, on Windows | OQ-011, OQ-032, C-002 |
| 0.8 | Experiment: execution policy with `qa` review + Board approval stage | OQ-005 |
| 0.9 | Experiment: `company import` preview against this repo / a generated package | OQ-007, ADR-012 |
| 0.10 | Decide ADR-011 and ADR-012 (Board). Done 2026-11-03: both accepted | C-001 |

Exit criteria: results written into [open-questions.md](open-questions.md); ADR-011/012 accepted or revised.

## Phase 1: Stage 1 studio (configuration, not code)

1. Create the real company and its Agent Instances ([agent-onboarding.md](../../knowledge/company/workflows/agent-onboarding.md)). Originally 7; the live company Soucean has 8 (`config/paperclip/agents.json`, 2026-11-21), plus the proposed Review Package `code-reviewer`. Done: see [implementation-plan.md](implementation-plan.md) §3.
2. Configure GitHub token secret and branch protection ([security-operations.md](../operations/security-operations.md)).
3. Create or register the first Game Project ([project-initialization.md](../../knowledge/company/workflows/project-initialization.md)).
4. Run 5–10 real Tasks through [development-cycle.md](../../knowledge/company/workflows/development-cycle.md) and [code-review-and-merge.md](../../knowledge/company/workflows/code-review-and-merge.md).
5. **Gap analysis:** for each MUST in ADR-006, ADR-009, RULES.md, and runtime-architecture.md, record whether Stage 1 satisfies it. Output: `docs/architecture/stage1-gap-analysis.md` (to be created).

## Phase 2: Lightweight tooling (code, low risk)

Only what Phase 1 shows is needed. Candidates:
- `scripts/validate-registries`: validate `knowledge/projects/registry.yaml` against its schema and cross-check dependency IDs.
- `scripts/check-dependencies`: compare installed versions with the registry.
- `scripts/generate-company-package`: produce a Paperclip-importable package if OQ-007 requires one.
- `templates/game-project/`: seed files for new Game Repositories.

## Phase 3: Runtime (Stage 2, only for verified gaps)

Build order, each with tests:
1. Config loader + schema (`schemas/runtime-config.schema.yaml`).
2. Dispatcher with Paperclip client (identity, Task discovery).
3. Provider Adapters (`claude_local`, `codex_local`): invocation building, output parsing, exit classification. Unit-tested with recorded outputs.
4. Workspace Manager + Git Manager (only if Paperclip does not own worktrees).
5. Result Reporter with outbox.
6. Recovery sweep.
7. Wire as a Paperclip `process` agent; run the Phase 1 Task set again.

Language and state store per OQ-013/OQ-014 (TypeScript + JSON files proposed).

## Phase 4: Hardening

Resource limits (OQ-015), stronger isolation (OQ-027), automated merge-approval linkage (OQ-005/OQ-016), multi-provider comparisons.

## Related documents
[implementation-plan.md](implementation-plan.md) (Phase 1–4 plan, `PROPOSED`) · [open-questions.md](open-questions.md) · [../decisions/ADR-011-execution-path-selection.md](../decisions/ADR-011-execution-path-selection.md) · [../architecture/runtime-architecture.md](../architecture/runtime-architecture.md)
