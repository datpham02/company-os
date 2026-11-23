# 4. Missing or Broken Activation Paths

## Root causes (prefer fixing architecture, not a second orchestrator)

1. **No task→skill router.** Agents rely on ambient skill folders + AGENTS.md prose. Registry `usedBy` is documentation, not wiring.
2. **Knowledge Delivery generated but not approved for deployment.** Catalog + game-artist package exist; P1–P4 blocked; Agents may refuse Company OS paths outside Task Workspace (SOU-88).
3. **Heartbeat / live Agent policy.** Several `heartbeat.enabled: false`; Cursor paused; Paperclip stopped → even correct wiring cannot INVOKED.
4. **Permission ≠ instruction ≠ installation.** Catalog already separates these columns; operators still conflate them.
5. **Registry drift vs machine.** verifiedOn 2026-11-03; MCP “configured” claims stale; openspec still candidate/uninstalled; Godot used but unregistered.
6. **Workspace isolation.** Mandatory policy in optional skills fails; KD ADR-024 correctly keeps policy in packages — but packages aren’t delivered.
7. **Overlap without selection.** Candidate skill mega-packs (Claude-Code-Game-Studios, awesome-gamedev, design packs) would compete with Company OS roles if naively installed.
8. **R&D vs production bleed.** Klein/ReferenceLatent proven offline; production Agent path still SDXL/FLUX wrappers only — correct, but docs don’t auto-route artists away from inventing R&D calls.

## Broken / incomplete paths (concrete)

| Path | Break point | Ladder stop |
|---|---|---|
| Registry usedBy → Agent skill load | No sync from registry to Paperclip skills.assigned | R |
| KD package → game-artist runtime | P1–P4 not approved; auth local_trusted caveat | I (artifacts) → not A |
| studio-art skill → invoked on art Tasks | No desiredSkills assignment verified | D? → not A |
| openspec → designer/PM/programmer | Not installed | R |
| playwright → qa | Config missing locally | R (stale note) |
| pixelfx → VFX Tasks | Allow present; no routing/evidence of use | A |
| Cursor role → enforced tools | Sandbox disabled; agents paused | I → not A (enforced) |
| Paperclip issue loop | :3100 down | I → not V |
| Candidate design repos → ui/web | Never cloned | R |
| Godot → registry discoverability | Used but no dependency id | I→E without R |
| Company OS docs → Agent read | Outside workspace refused | D blocked |
| Catalog role views → Agent brief | Human/Board docs only | R/D for operators |

## Why docs/skills aren’t consistently incorporated

- Task contracts don’t require a **capability citation** (skill id / catalog operation).
- Review gates don’t check “did assignee use the approved tool for this failure class?”
- Optional skill discovery loses to model improvisation when allowlisted CLIs exist without a skill checklist.
- Duplicate personal Cursor skills create a parallel universe the Paperclip Agent never sees.
