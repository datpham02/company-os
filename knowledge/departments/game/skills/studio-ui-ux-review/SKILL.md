---
name: studio-ui-ux-review
description: "Read-only review of a game UX spec, HUD design or interaction-pattern specification against the Task acceptance criteria, project GDD, input/platform constraints and accessibility requirements. Reports supported findings and explicit NOT ASSESSED gaps."
allowed-tools: Read, Glob, Grep
---

# Studio Skill: UI/UX design review (candidate)

**Status:** PROPOSED — not installed, assigned, delivered, or runtime-verified.  
**Intended primary role:** `ui-designer`; independent review must still follow the Task's actual reviewer assignment (often `qa`).  
**Scope:** Read-only review of Task-supplied, accessible project documents.  
**Authority:** Company OS Task Contract, Board decisions, project requirements and runtime permissions override this procedure. This skill grants no access or approval.

## Trigger and boundaries

Use when the **Task explicitly requests** an evaluation of a UX specification, combat HUD layout, game menu/flow or interaction-pattern library. It supports both first reviews and re-reviews after a revised document is supplied. It is not a general UI redesign or code-writing instruction.

- **Never** edit a specification, game file or Task, run a shell script, install a package, spawn subagents, generate assets, invoke an image model, or approve/merge a PR as part of this skill.
- **Never** interpret this skill's `APPROVED` as a Paperclip review-stage decision or Board approval; those use the existing independent reviewer and approval workflow.
- Only inspect files provided inside the assigned Task Workspace or via a separately verified read mechanism. Company OS links that are inaccessible are **not** evidence of reading.
- Project art direction, game design, platform constraints, accessibility commitments and explicit acceptance criteria take precedence. Do not invent missing standards or silently borrow upstream CCGS defaults.
- Respect the Task's read set. If a required source is inaccessible, report it as **NOT ASSESSED** with the missing input and unblock owner; do not bypass a permission refusal.

## Inputs: establish an evidence baseline first

Read and record the accessible source and version/section for each item below; if absent, record the gap.

1. The Task goal, acceptance criteria, intended user/player, **read set**, exact review scope and target platforms/resolutions.
2. The UX/HUD/pattern specification that is being reviewed, including its states and variants.
3. The approved GDD/gameplay requirements applicable to the feature, and the player's journey or interaction context where documented.
4. The project's current art direction/design tokens, existing UI components/pattern library and applicable input/navigation conventions.
5. The **committed** accessibility target (where one exists), relevant project licensing constraints, and any platform/touch/gamepad requirements.
6. Screenshots, recordings or runnable artifacts **only if already supplied or accessible without executing unapproved tools**. A design-doc review does not imply visual or interactive runtime verification.

**Do not treat a spec's own statement as independent proof of its correctness.** If no authoritative GDD, platform input definition, or committed accessibility target is available, mark that comparison dimension **NOT ASSESSED**. A spec-provided value may be cited as an assumption, never as a verified project commitment.

Select the review lens explicitly from the Task: `ux-spec`, `hud`, or `interaction-patterns`. A different structure may be reviewed using the nearest checklist, but state the assumed lens and limits. A `ui-review` Task type or a Router preview is a discovery hint, **not delivery or activation** of this skill.

## Review lens A — Screen / UX flow specification

- **Purpose and player context:** player goal, arrival state, navigation position, entry/exit routes and relation to gameplay flow.
- **States and transitions:** loading, empty, populated, selected, disabled, error, pause/interrupt, and applicable animation or timing rules. Explain why a state is not applicable rather than demanding boilerplate.
- **Layout and data:** element inventory, visual priority, safe zones, source/owner for displayed data, null/latency behavior and real-time refresh triggers.
- **Interaction and inputs:** touch hit areas where relevant; keyboard focus and gamepad mapping where relevant; cancel/back semantics; selection feedback and recovery from errors.
- **Content and localization:** text growth, overflow, language changes, dynamic text and small-screen readability; check against the project's own platform targets.
- **Acceptance:** observable and testable outcomes, including states and platform-specific resolution/input scenarios.

## Review lens B — Combat HUD / in-game overlay

- **Information hierarchy:** which gameplay signals are mandatory, optional, contextual or hidden; GDD-to-HUD coverage and any intentionally omitted information.
- **Readability under play:** occlusion of action/grid/target, contrast against actual game backgrounds, signal-to-noise balance, priority of warnings and cooldown feedback.
- **Layout adaptability:** target aspect ratios, safe areas, notches, scaling, display density and controller/touch variants as required by the Task.
- **States:** exploration, combat, targeting/casting, paused, disabled, damage/telegraph overlays and other Task-specific modes.
- **Accessibility:** color-independent meaning, legible sizes and distinct selected/focused/error states; compare against the committed project tier where available.
- **Runtime evidence boundary:** screenshots can support observed visual readability; a textual mockup alone cannot prove layout, timing, tap accuracy or frame-rate behavior.

## Review lens C — Interaction-pattern specification

- **Coverage:** controls actually needed by this game (buttons, menus, modal/dialog, notification, navigation, focus, selection, tooltip or item list as applicable).
- **Behavioral consistency:** standard input/Back semantics, empty/error/disabled/hover/focus/pressed states and transitions.
- **Usability and accessibility:** feedback, input device parity and alternatives to color-only indicators, where committed requirements demand them.
- **Integration:** each reused pattern names its intended screens; new/changed patterns record impact on existing flows and implementation acceptance criteria.
- **Conflicts:** identify duplicate definitions or contradictions with existing project patterns and gameplay controls rather than creating a parallel authority.

## Evaluate each dimension with evidence

For each dimension that applies to the selected lens, produce one of:

- **PASS:** supported by a specific accessible source and location; not merely asserted by the document under review when independent comparison is needed.
- **FINDING:** an observable omission, contradiction or failure; include severity, document location, source-of-truth criterion and an actionable correction.
- **NOT ASSESSED:** needed source, access, design decision, screenshot, test or committed criterion is missing. State precisely what would make it assessable and who can provide it.
- **N/A:** dimension genuinely does not apply to this scope; provide the reason. Do not use N/A to hide a missing mandatory source.

Core dimensions: (1) specification completeness, (2) gameplay/GDD alignment, (3) platform input and interaction coverage, (4) accessibility and state legibility, and (5) design/pattern consistency. Treat the visual/runtime dimension separately: it is **NOT ASSESSED** unless actual visual/runtime evidence was inspected.

Never claim to have opened images or run a UI when that did not occur.

## Verdict selection (skill-only, advisory)

Use one of these verdicts, in this exact precedence:

1. **MAJOR REVISION NEEDED** — fundamental contradiction with gameplay/player need, unusable information hierarchy or an unimplementable core flow established from the evidence.
2. **NEEDS REVISION** — any actionable, blocking deficiency in an applicable checked dimension.
3. **NOT ASSESSED** — no known blocking deficiency, but one or more required applicable dimensions cannot be checked. This is **not** an approval.
4. **APPROVED** — all required, applicable dimensions pass with sufficient evidence; only non-blocking advisories may remain.

A real discovered defect is not erased by missing evidence elsewhere. If a dimension cannot be checked and another contains a blocking defect, return the corresponding revision verdict and list both the finding **and** the NOT ASSESSED gap. A retrospective re-review must state what changed in the input; do not upgrade a verdict without new evidence.

## Required result (one read-only report)

Start with the verdict token and include the following fields:

```markdown
UX-REVIEW: APPROVED | NOT ASSESSED | NEEDS REVISION | MAJOR REVISION NEEDED
Review lens: ux-spec | hud | interaction-patterns
Task: <id> | Document: <accessible path / revision>
Reviewed inputs: <each exact source path and section, or UNAVAILABLE>
Assumptions: <each assumption, or none>

Dimension results:
- Completeness: PASS / FINDING / NOT ASSESSED / N/A — <evidence location>
- GDD alignment: ...
- Input and interaction: ...
- Accessibility and legibility: ...
- Pattern/design consistency: ...
- Visual/runtime observation: ...

Blocking findings:
- [UX-001] <severity>, <document location>, <observed issue>,
  <required criterion/source>, <specific requested fix>
Advisories: <non-blocking recommendations>
Not assessed: <dimension>, <missing source/evidence>, <unblock owner>
Next action: <author change, owner supply input, or independent review handoff>
Execution performed: NONE (read-only; no command, edits or generation)
```

If the Task's own reviewer or Board has additional stage-specific verdict vocabulary, map these findings in that **separate** workflow; do not claim this skill's advisory token is the recorded stage decision.

## Provenance, non-overlap and limitations

This candidate is a Company OS-specific, shorter adaptation of the review method in Donchitos **Claude-Code-Game-Studios** MIT-licensed `ux-review` skill (pinned upstream commit `abc0de79d6ceb0b5d7aa693945849b3937afbe6a`). See `UPSTREAM-NOTICE.md` for license attribution. Its source is a **method reference**, not a runtime dependency.

Unlike UI/UX Pro Max (style/UX reference discovery) and DESIGN.md (design token linting), this skill is a **read-only specification quality review**. It does not import CCGS `project.yaml`, hooks, Claude subagents, `AskUserQuestion`, `/team-ui`, scripts, or path assumptions. No automated delivery, skill assignment, Paperclip integration or effectiveness claim has been validated.
