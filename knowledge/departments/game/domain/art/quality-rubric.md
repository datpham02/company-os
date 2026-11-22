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
| Evidence | The handoff has the evidence the lane requires ([complexity-lanes.md](complexity-lanes.md)), in the evidence folder for its Task type (committed for art and integration Tasks; in the Task Workspace for game-UI Tasks) and openable by the reviewer ([handoff-templates.md](handoff-templates.md#review-evidence-where-it-lives-and-how-reviewers-open-it)); staging paths, paths outside the workspace and written descriptions are not visual evidence |
| Scope | Only files in the write set changed; no application code, import settings, shaders or shared pipeline code (reusable across Tasks, workflows or projects) by `game-artist`; task-local artwork production scripts only inside the write set, any number of outputs |

Missing evidence is `UNVERIFIED`, not a pass.

## Acceptance stages
An asset is accepted in three stages. Each stage has its own hard gates; no stage waives a gate, and only a **verified** asset counts as production-accepted.

| Stage | Reached when | Hard gates that must pass at this stage | May be deferred |
|---|---|---|---|
| **Art-ready** | The art Task's review stages approve and the Board merges it | Licence and provenance · originality · technical contract of the files · scope · evidence for every art-side check · critical readability **at target size on the target background colour** (`art-ops.py contact --bg`) and in every listed state | Only the **in-context checks** below, and only to a **named integration Task** |
| **Integration-ready** | The integration Task's review stages approve and the Board merges it | Technical contract in the engine (import, filtering, pivot, frame timing, loop) · every deferred check of the assets it integrates, with committed in-engine evidence · performance budget · evidence · scope | Nothing |
| **Verified** | `qa`'s verdict on the integration Task records each integrated asset as verified | Every deferred check passed; no open `blocker` finding on the asset | — |

**In-context checks (the only deferrable ones):** readability over the real background or scene; scale against the other in-game assets; animation and VFX timing and loop in context; UI legibility in place at the device resolutions. Nothing else may be deferred: licence and provenance, originality, file-level technical contract, scope, art-side evidence and readability at target size are always checked at art-ready.

**How a deferral is written:** `UNVERIFIED — deferred to <integration Task key>: <check>`, in the art handoff and repeated in the reviewer's verdict. A deferral without an existing integration Task key is not allowed: the reviewer requests changes (or the asset stays art-ready and is never counted as verified). The check stays `UNVERIFIED` until the named integration Task validates it with in-engine evidence; the integration Task's description lists every check deferred to it. A deferred check that fails is routed as a finding to a new art fix Task (L0), which blocks the asset's verification; the integration Task does not redraw the art.

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
