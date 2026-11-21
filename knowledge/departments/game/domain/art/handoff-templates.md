# Art Handoff and Review Templates

- **Status:** `PROPOSED` (2026-11-22).
- **Copied into:** the `game-artist` role file (plan and handoff headings), the `gameplay-programmer` role file (integration evidence), and the art Task template (review format).

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
Evidence: <contact sheet at target size: path> · <before/after: path> · <representative scene (L2): path>
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
