# Art Handoff and Review Templates

- **Status:** `PROPOSED` (2026-11-22).
- **Copied into:** the `game-artist` role file (plan and handoff headings), the `gameplay-programmer` role file (integration evidence), and the art Task template (review format).

## Review evidence: where it lives and how reviewers open it
Paperclip runs every review stage in the author's Task Workspace ([security-architecture.md §4](../../../../../docs/architecture/security-architecture.md#4-agent-permissions-provider-level), reviewer isolation), so a reviewer can open files in that workspace; it cannot rely on the staging folder, another machine or a description. The Board reads committed evidence on GitHub and workspace evidence on the studio machine. Each role uses only the tools it already has:

| Task | Author | Capture with | Evidence folder | In the write set | Delivered by |
|---|---|---|---|---|---|
| Art | `game-artist` | `art-ops.py` (contact sheets, `--bg` previews, before/after); Godot frames where the asset already loads | `art_src/review/<TASK-KEY>/` | Yes | `art-ops.py` writes there directly; commit and push |
| Integration | `gameplay-programmer` | The allowed Godot commands or the project's screenshot tool, at every state and resolution the Task lists | `art_src/review/<TASK-KEY>/` | Yes | Copy the captured frames there (its own workspace write access); commit and push |
| Game UI | `ui-designer` | The allowed Godot commands only: `.godot/<name>*.png` and, in Deckbound, `.godot/qa/` | `.godot/` in the Task Workspace | **No** (generated, ignored by Git) | Left in the Task Workspace and listed by path; its allowlist cannot copy binary files elsewhere, and no new permission is added. `qa` recaptures the same states with the same commands for its verdict. A committed copy needs a Board decision ([OQ-049](../../../../../docs/roadmap/open-questions.md#oq-049--art-production-v2-delivery-and-tooling)) |

A project may name another evidence folder in its `AGENTS.md`; it then replaces `art_src/review/<TASK-KEY>/` in the write set.
1. Every image a reviewer must see (candidate contact sheet, target-background preview, before/after, representative scene, direction sheet, in-engine frames) is in the evidence folder above.
2. The handoff cites each image by its path relative to the Task Workspace. Raw generator candidates stay in the staging folder; only the review sheets built from them are committed.
3. Target-background preview: `art-ops.py contact --bg R G B --cell W H` with the background colour the brief names, at target size (`--filter nearest` for pixel art). A textured or in-scene background needs an in-engine screenshot (the integration Task, or a Godot frame where the asset can already be loaded); until compositing exists it is `UNVERIFIED`.
4. A path in the staging folder, a path outside the Task Workspace, a file the reviewer cannot open, an uncommitted file where the table says committed, or a written description is **not evidence**: the reviewer marks the claim `UNVERIFIED`, which fails the evidence hard gate.

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
Stage: art-ready (in-context checks deferred; not production-accepted until verified)
Deferred: <UNVERIFIED — deferred to <integration Task key>: <in-context check>>, or none
UNVERIFIED (other): <check — why>, or none — any of these fails a hard gate
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
Evidence (committed): <art_src/review/KEY/<state>-<W>x<H>.png per state and resolution>
Performance: <measurement against the budget>
Deferred checks validated: <art Task key · asset · check — pass | fail — evidence path>, one line each
Verified assets: <list>; not verified: <asset — open check>
Art change requests sent to game-artist: <comment link, or none>
UNVERIFIED: <check — why>, or none
```

## 4. Review verdict (`qa` or another review stage)
```md
Verdict: <approved | changes requested>
Stage judged: <art-ready | integration-ready>
CI: <statusCheckRollup result at the head commit> | verified by qa at <head commit> (read-only reviewers) | UNVERIFIED (no GitHub access)
Hard gates: licence/provenance <pass|fail|UNVERIFIED> · originality <…> · technical contract <…> · readability at target size <…> · evidence <…> · write set <…>
Scores (0–2, with observation): readability <n — …> · art direction <n — …> · craft <n — …> · coherence <n — …> · production <n — …> · evidence <n — …>
Deferred (art-ready only): <UNVERIFIED — deferred to <integration Task key>: <check>>, or none · Verified (integration-ready only): <assets>; not verified: <asset — open check>
Findings:
1. <file, frame, region> — expected <…> — actual <…> — severity <blocker|major|minor> — evidence <path> — owner <role>
```
The decision is recorded in Paperclip; the comment alone leaves the Task stuck. The reviewer never edits, commits or pushes the author's branch.
