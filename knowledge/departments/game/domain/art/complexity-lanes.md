# Art Complexity Lanes

- **Status:** `PROPOSED` (2026-11-22). Defaults for the Phase 1 pilot; the Board calibrates them after the pilot ([asset-production.md](../../workflows/asset-production.md#pilot-and-measurement)).
- **Copied into:** the `game-artist` role file (summary) and every art Task description (the chosen lane and its reason).

The lane sets how much exploration and evidence an asset needs. It never changes review, approval, ownership or permissions. The Task author proposes a lane; `game-artist` confirms it, or argues for another, in its plan comment. A disagreement goes to `project-manager`; a lane that would change art direction goes to the design authority in [game-rules.md §2](../game-rules.md#2-design-authority).

| | L0 — fix or variant | L1 — new asset | L2 — new visual direction |
|---|---|---|---|
| Examples | Recolour, extra frame, size fix, one more icon in an approved set, a QA defect | A new enemy, prop, tile set or effect within the approved direction | Visual identity, a main character, a new environment family, a new UI or VFX language, the first asset of a project |
| Exploration | None: reuse the proven pattern of the family | 2–3 distinct candidates, compared at target size | 3 or more directions that differ in silhouette, shape language or value structure, compared at target size and in a representative scene |
| Selection | — | Selected candidate and one line on why each other one fails | Selection proposed by `game-artist`, decided by the design authority (`game-designer`; `director` when it changes vision or pillars) |
| Refinement | One visual inspection | Critique and targeted refinement, iteration budget (default 2 rounds) | As L1, plus a golden reference that later assets are checked against |
| Evidence | Before/after at target size | Contact sheet of candidates at target size, selected asset, before/after of each round | As L1, plus the representative scene or composition and the decision record |
| Task shape | Part of a family Task | One Task per asset family that fits one PR | A separate direction Task **only** when an approval decision gates later work; production then runs as L1 Tasks blocked by it |

Rules:
1. Do not split the internal phases (research, explore, select, produce, critique, preflight) into separate issues. Split only for a different write set, an approval decision that gates other work, an independent integration Task, or a real blocker ([task-contract.md §3](../../../../company/standards/task-contract.md#3-splitting-work)).
2. Batch a coherent asset family into one Task when it fits the size limit (about 10 files or 400 changed lines unless the project sets its own).
3. A lane rises when the work turns out bigger: an L0 that needs a new look is L1; an L1 that changes the approved direction stops and becomes an L2 decision. Say so in a comment; do not continue on the old lane.
4. The iteration budget is the number of critique-and-refine rounds after the first full version. The Task may set another number. When the budget is spent with defects left, hand off with the defects listed (they are not hidden), or set the Task `blocked` (type `decision`, owner `project-manager`) when a defect fails a hard gate.
