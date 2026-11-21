# Art Handoff and Review Templates

- **Status:** `PROPOSED` (2026-11-22).
- **Copied into:** the `game-artist` role file (plan and handoff headings), the `gameplay-programmer` role file (integration evidence), and the art Task template (review format).

## Review evidence: where it lives and how reviewers open it
Reviewers run in the Task Workspace and can open only what is on the Task Branch; they cannot rely on the staging folder, another machine or a description.
1. Every image a reviewer must see (candidate contact sheet, target-background preview, before/after, representative scene, direction sheet) is written with `art-ops.py` to `art_src/review/<TASK-KEY>/` (or the review-evidence folder the project's `AGENTS.md` names), which is in the Task's write set, then committed and pushed.
2. The handoff cites each image by its repository-relative path. Raw generator candidates stay in the staging folder; only the review sheets built from them are committed.
3. Target-background preview: `art-ops.py contact --bg R G B --cell W H` with the background colour the brief names, at target size (`--filter nearest` for pixel art). A textured or in-scene background needs an in-engine screenshot (the integration Task, or a Godot frame where the asset can already be loaded); until compositing exists it is `UNVERIFIED`.
4. A path in the staging folder, an uncommitted file, a path the reviewer cannot open, or a written description is **not evidence**: the reviewer marks the claim `UNVERIFIED`, which fails the evidence hard gate.

## 1. Plan comment (`game-artist`, before any file is written)
```md
Plan — <asset family>
Lane: <L0 | L1 | L2> — <reason>
References read: <paths>
Reference traits to match: <3–5 observable traits>
Constraints: <target size, background, camera, frames, states, budget, licence rule>
Deliverables: <files, sizes, frames, variants>
Method and tools: <generator and model / operations / PixelFX / source files>
Candidates planned: <number, and how they will differ>
Iteration budget: <rounds>
Questions: <for game-designer or project-manager, or none>
```

## 2. Art handoff (`game-artist`, with the PR)
```md
Handoff — <asset family> — <ready for integration | art only>
PR: <link> · Branch: <name>
Files: <path — dimensions — what it shows>
Selected: <file> — why: <reason>. Rejected: <candidate — why it fails>
Evidence (committed, repository-relative): <art_src/review/KEY/candidates.png> · <art_src/review/KEY/on-target-bg.png> · <art_src/review/KEY/before-after-r1.png> · <representative scene (L2)>
Refinement rounds: <n of budget> — issues fixed: <list>
Preflight: dimensions <ok>, frames and order <ok>, alpha and edges <ok>, naming and directory <ok>, variants <ok>, provenance <ok>, write set (`git status --short`) <ok>
UNVERIFIED: <check — why>, or none
Animated: pivot <x,y>, frame timing intent <ms per frame>, loop <yes/no>
Known limitations: <list, or none>
Self-check is not an approval.
```

## 3. Integration handoff (`gameplay-programmer`)
```md
Integration — <asset family> in <scene or system>
PR: <link>
Import and resources: <settings changed>
States wired: <list>
Evidence: <screenshot or frame paths per state and resolution>
Performance: <measurement against the budget>
Art change requests sent to game-artist: <comment link, or none>
UNVERIFIED: <check — why>, or none
```

## 4. Review verdict (`qa` or another review stage)
```md
Verdict: <approved | changes requested>
CI: <statusCheckRollup result>
Hard gates: licence/provenance <pass|fail|UNVERIFIED> · originality <…> · technical contract <…> · readability at target size <…> · evidence <…> · write set <…>
Scores (0–2, with observation): readability <n — …> · art direction <n — …> · craft <n — …> · coherence <n — …> · production <n — …> · evidence <n — …>
Findings:
1. <file, frame, region> — expected <…> — actual <…> — severity <blocker|major|minor> — evidence <path> — owner <role>
```
The decision is recorded in Paperclip; the comment alone leaves the Task stuck. The reviewer never edits, commits or pushes the author's branch.
