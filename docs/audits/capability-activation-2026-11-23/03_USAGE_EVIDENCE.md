# 3. Actual Usage Evidence Report

Rule: **usedBy ≠ INVOKED ≠ EFFECTIVELY USED.**

## Confirmed EFFECTIVELY USED (cited)

| Capability | Who / where | Evidence source | Ladder |
|---|---|---|---|
| comfy-draft | game-artist / Board tools | Catalog: SOU-66, SOU-68, SOU-71 | E |
| comfy-edit img2img | installed copy | G7(c) 2026-11-22 | E (smoke/runtime verified) |
| comfy-edit inpaint SDXL | | SOU-64 run 2 remove; insert 0/10 fail | E (limited) |
| comfy-edit matte BiRefNet | | G7(d) 11/11 SOU-81 | E |
| art-ops (subset) | | G7(a), SOU-66 grade, Board compose/trim/diff | E partial |
| Claude Code | most roles + Board | adapters + studio CLI | E |
| GitHub CLI | PR workflows | registry + allow rules | E (ops) |
| Godot headless import/quit/write-movie | Agents / spikes | security-architecture SOU-49; S2 spike offline | E offline / V agents (catalog) |
| Paperclip skill (Board chat) | Board Operator | company-os project skill `paperclip` | E operator |
| ui-ux-pro-max | ui-designer allow | skill + allow rule present | A→?V (no SOU run cited this audit) |
| ReferenceLatent / Klein R&D | Board/Claude offline spikes S6–P3 | local locked evidence (untracked) | E **R&D only**, not Agent-permitted |
| Sealwarden V2 docs | Board pack | workspace R&D art-construction V2 tree | E documentation; **no generation** |

## REGISTERED / INSTALLED but weak or no Agent usage

| Capability | Gap |
|---|---|
| pixelfx | Integrated + allowlisted; catalog: **no agent run in SOU logs** |
| codex | Installed; usedBy []; OQ-010 deferred |
| openspec | usedBy three roles; **not installed** |
| playwright-mcp / hoppscotch-mcp | Registry “configured 2026-11-03”; **absent from Claude MCP config today** |
| All 14 candidates (except config claims) | Not cloned under audited trees |
| Cursor agents | Profiles exist; **paused**; sandbox disabled |
| Paperclip company Agents heartbeats | Many `enabled: false`; API unreachable → no live V this audit |
| Knowledge Delivery package | Generated; **not deployed** (P1–P4) |
| studio-art skill | In repo; assignment/sync not approved |

## Operator-only (Cursor IDE session) — not Company Agent inventory

Figma / Postman / Canva / GitHub MCP / Google Drive / X / browser / computer-use / ElevenLabs — available to the **Board Cursor operator**, not in `agents.json` allowlists and mostly **not** in `registry.yaml`. Treat as unregistered operator tooling unless Board registers + gates them.

## Negative evidence (important)

| Claim | Finding |
|---|---|
| “Agents use openspec” | openspec CLI absent |
| “playwright MCP ready for qa” | no playwright entry in Claude MCP config |
| “Paperclip Agents running” | Paperclip API unreachable |
| “KD activates art skill” | docs: P1–P4 not approved |
| “pixelfx production-used” | installed; not agent-invoked in SOU evidence |
| “candidate usedBy means active” | false — aspirational routing only |
