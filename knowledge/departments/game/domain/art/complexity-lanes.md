# Art Complexity Lanes

- **Status:** `PROPOSED` (2026-11-22). Defaults for the Phase 1 pilot; the Board calibrates them after the pilot ([asset-production.md](../../workflows/asset-production.md#pilot-and-measurement)).
- **Copied into:** the `game-artist` role file (summary) and every art Task description (the chosen lane and its reason).

The lane sets how much exploration and evidence an asset needs. It never changes review, approval, ownership or permissions. The Task author proposes a lane; `game-artist` confirms it, or argues for another, in its plan comment. A disagreement goes to `project-manager`; a lane that would change art direction goes to the design authority in [game-rules.md §2](../game-rules.md#2-design-authority).

| | L0 — fix or variant | L1 — new asset | L2 — new visual direction |
|---|---|---|---|
| Examples | Recolour, extra frame, size fix, one more icon in an approved set, a QA defect | A new enemy, prop, tile set or effect within the approved direction | Visual identity, a main character, a new environment family, a new UI or VFX language, the first asset of a project |
| Exploration | None: reuse the proven pattern of the family | 2–3 distinct candidates, compared at target size | 3–4 directions that differ in silhouette, shape language or value structure, compared at target size and in a representative scene |
| Selection | — | Selected candidate and one line on why each other one fails | Selection proposed by `game-artist`, decided by the design authority (`game-designer`; `director` when it changes vision or pillars) |
| Refinement | One visual inspection | Critique and targeted refinement, iteration budget (default 2 rounds) | As L1, plus a golden reference that later assets are checked against |
| Evidence | Before/after at target size | Contact sheet of candidates at target size, selected asset, before/after of each round | As L1, plus the representative scene or composition and the decision record |
| Task shape | Part of a family Task | One Task per asset family that fits one PR | A separate direction Task **only** when an approval decision gates later work; production then runs as L1 Tasks blocked by it |

Rules:
1. Do not split the internal phases (research, explore, select, produce, critique, preflight) into separate issues. Split only for a different write set, an approval decision that gates other work, an independent integration Task, or a real blocker ([task-contract.md §3](../../../../company/standards/task-contract.md#3-splitting-work)).
2. Batch a coherent asset family into one Task when it fits the size limit (about 10 files or 400 changed lines unless the project sets its own).
3. A lane rises when the work turns out bigger: an L0 that needs a new look is L1; an L1 that changes the approved direction stops and becomes an L2 decision. Say so in a comment; do not continue on the old lane.
4. The iteration budget is the number of critique-and-refine rounds after the first full version. The Task may set another number. When the budget is spent with defects left, hand off with the defects listed (they are not hidden), or set the Task `blocked` (type `decision`, owner `project-manager`) when a defect fails a hard gate.

## L2 decision handoff
The design authority's choice uses only existing Paperclip mechanics: review stages, blocker relations and the blocker protocol ([task-contract.md](../../../../company/standards/task-contract.md)). No new status.

**A. Direction Task (default when later Tasks depend on the direction).**
1. The Board creates an art Task with lane L2 whose deliverable is the direction, not production art: the direction sheet (3–4 directions at target size and in a representative scene, as committed review evidence) and the project's direction record (the file the project's `AGENTS.md` names for it, for example `docs/art/directions/<family>.md`) in its write set.
2. Its execution policy has a `review` stage for `game-designer` (plus `director` when the direction changes vision or pillars), then `qa`, then Board approval. The `game-designer` verdict **is** the decision: `approved` names the chosen direction in the verdict comment, which must match the direction record; `changes_requested` says what none of the directions achieves, and the Task returns to `game-artist` on the same branch.
3. The production Tasks (L1, one per asset family) are created in `backlog` with a Paperclip blocker relation on the direction Task. Paperclip wakes them (`issue_blockers_resolved`) only when the direction Task is `done`, after the Board merges it. If the direction Task is cancelled, its blocker relations are first pointed at the replacement Task (task-contract §6), or the dependants never wake.

**B. Inside one Task (only when nothing else waits on the direction).**
1. `game-artist` commits and pushes the direction sheet as review evidence, then sets the Task `blocked` with the blocker lines: `Type: decision`, `Unblock owner: game-designer` (or `director`), `Ask: choose direction A, B, C or D, or reject all with the reason`, and @-mentions the owner.
2. The owner's answer comment wakes the assignee (Paperclip wakes the assignee on a comment by anyone else). `game-artist` records the decision and its author in the direction record on the branch, moves the Task back to `in_progress` and continues as L1.
3. No answer: the liveness rules apply (a wake after 4 h, escalation after 1 working day, task-contract §7). Whether an @-mentioned owner's run can open the branch's evidence files is `UNVERIFIED` ([OQ-049](../../../../../docs/roadmap/open-questions.md#oq-049--art-production-v2-delivery-and-tooling)); prefer A when in doubt.
