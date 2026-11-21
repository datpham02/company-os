# Visual Quality Rubric

- **Status:** `PROPOSED` (2026-11-22). Pilot scale; calibrated after the pilot.
- **Used for:** the artist's self-check (never an approval), `qa`'s review, and any extra review stage the Task names (`game-designer` for readability, `director` where the project's art pipeline requires it). The Task description carries a copy, because reviewers cannot read this repository.

## 1. Hard gates
Any failed or unverified hard gate means `changes_requested` (or `blocked` when the author cannot fix it), whatever the scores below.

| Gate | Pass means |
|---|---|
| Licence and provenance | Every new or changed file has a provenance record; its source and licence are allowed by the project's licensing rule; no third-party art, font or traced work |
| Originality | No recreation of an existing game's characters, art or look; no other game, studio or artist named in a prompt ([game-rules.md §1](../game-rules.md#1-originality)) |
| Technical contract | Dimensions, frames, alpha, naming, directory and variants match the Task and the project's asset spec |
| Critical readability | What the player must notice is identifiable at the target size, on the target background, in the required states |
| Evidence | The handoff has the evidence the lane requires ([complexity-lanes.md](complexity-lanes.md)), committed on the Task Branch and openable by the reviewer ([handoff-templates.md](handoff-templates.md#review-evidence-where-it-lives-and-how-reviewers-open-it)); staging paths, uncommitted files and written descriptions are not visual evidence |
| Scope | Only files in the write set changed; no code, import settings or shaders by `game-artist` |

Missing evidence is `UNVERIFIED`, not a pass.

## 2. Scored categories (0–2)
Score each category that applies: **0** fails · **1** partly meets · **2** meets, with evidence. Always write the observation that justifies the score; a number alone is not a review. The total is for comparing pilot runs only and never overrides a hard gate.

**Aesthetic failures block too.** Passing every hard gate is not enough. A **0** in Art direction, Craft or Coherence means `changes_requested`, unless the design authority (`game-designer`; `director` when vision or pillars are involved) records an explicit exception in the Task: which category, what is accepted, and why. A reviewer cannot grant that exception, and `game-artist` cannot grant it for its own work. A **1** in those categories is written as a finding with its severity; the reviewer may approve with it only as a `minor` finding that has a follow-up Task or the same recorded exception.

| Category | What to look at |
|---|---|
| Gameplay readability | Focal point, silhouette, contrast on the target background, telegraphs and timing distinguishable from each other |
| Art direction | Shape language, scale, value, palette, light and material match the named reference traits |
| Craft | Clean edges, no generation artefacts (extra limbs, melted detail, noise, halos), proportion, composition, purposeful detail |
| Coherence | Fits its family and its neighbours (UI, environment, characters); identity and continuity across poses and frames |
| Production | Format, alpha, frames, pivot, loop, naming, performance budget |
| Evidence | Actual previews at target size, provenance, reproducible settings, limitations stated |

## 3. Writing a finding
Each finding has: location (file, frame, region), expected, actual, severity (`blocker` fails a hard gate · `major` · `minor`), evidence (screenshot or contact sheet path, command output), and the owner from the routing:
- look, size, frames, palette, provenance → the art Task, `game-artist`;
- in-game behaviour, import, timing logic, shader, performance → the integration Task, `gameplay-programmer`;
- the requirement itself is unclear or wrong → `game-designer`.

For a question of taste with no named reference trait behind it, consult the design authority ([game-rules.md §2](../game-rules.md#2-design-authority)); do not invent an objective metric.
