# 1. Complete Dependency & Capability Inventory

Audit date: 2026-11-23 · Mode: read-only · Source: `dependencies/registry.yaml` (verifiedOn 2026-11-03, with later notes) + local machine spot-checks · Snapshots: `registry_snapshot.json`, `agents_snapshot.json`, `skills_snapshot.json`

Legend (activation ladder):
**R** REGISTERED · **I** INSTALLED · **D** DISCOVERABLE · **A** ACCESSIBLE · **V** INVOKED · **E** EFFECTIVELY USED

Recommendation: Keep | Activate | Evaluate | Defer | Reject

---

## 1.1 Registry (all 36)

### Approved (6)

| id | Verified version (registry) | Local 2026-11-23 | Ladder | Evidence | Rec |
|---|---|---|---|---|---|
| paperclip | 2026.1023.0 | CLI present via npx history; **API :3100 NOT listening** | R→I→D→A; V/E interrupted | Production Paperclip stopped (Board standing constraint). Skill `.claude/skills/paperclip` present. | Keep; Activate only when Board restarts Paperclip |
| claude-code | 2.1.329 | `claude.exe` on PATH | R→E (Board/operator + role adapters) | Primary adapter for most roles | Keep |
| codex | 0.166.0 | `codex.ps1` on PATH | R→I; **not A for Agents** (`usedBy: []`, OQ-010) | Approved install, Board deferred account/use | Defer |
| cursor-cli | 2026.10.22-27dcf5f | `agent` / `cursor-agent` on PATH | R→I→A declared; Cursor sandbox disabled; agents **paused** (KD-BD-4) | gameplay-programmer, web-engineer profiles | Keep (paused); no Activate until Cursor gate |
| rea | approved | skill `reverse-engineer-anything` under `~/.claude/skills` | R→I→D (Claude); Agent access task-gated | Used as technical reference skill | Keep |
| docker-desktop | approved | not re-probed this audit | R; conflict with ADR-013 for v1 | qa allow rule mentions `docker compose run` | Defer / policy conflict — do not Expand |

### Integrated (9)

| id | Local | Ladder | Evidence | Rec |
|---|---|---|---|---|
| comfyui | `~/game-studio-workspace/tools/ComfyUI_windows_portable`; **:8188 LISTENING (PID 17660)** | R→E (via wrappers) | SOU art pilots; Board tools | Keep |
| comfyui-embedded-python | present (art-ops host) | R→E | art-ops.py | Keep |
| sd-xl-base-1-0 | production models | R→E | draft/edit/inpaint | Keep |
| flux1-schnell-fp8 | production models | R→E (draft/img2img; **not** inpaint) | catalog + security-architecture | Keep |
| birefnet | integrated model | R→E (matte) | G7(d) 11/11 SOU-81 | Keep |
| pixelfx | `~/tools/pixelfx` True; allowlisted | R→I→A; **V/E weak** | catalog: no SOU agent run evidence | Activate (routing) |
| github-cli | `gh.exe` | R→E | PR workflows | Keep |
| ui-ux-pro-max-skill | `~/.claude/skills/ui-ux-pro-max` | R→I→A for ui-designer | `extraAllowedTools` search.py | Keep / Activate |
| google-design-md | integrated (registry) | R→I?; Agent discovery unclear | ui-designer `design.md *` allow | Evaluate discovery path |

### Evaluating (6) — R&D only

| id | Local | Ladder | Rec |
|---|---|---|---|
| comfyui-rnd | `~/game-studio-workspace/rnd/ComfyUI_rnd` True; **:8189 NOT listening** | R→I (offline) | Defer production; Keep R&D |
| flux2-klein-4b | R&D models (prior spikes) | I offline; not Agent-permitted | Defer until Board production decision |
| qwen3-4b-text-encoder | R&D | same | Defer |
| toonout | R&D; spike preferred BiRefNet | not taken further | Defer / likely Reject later |
| fooocus-inpaint-patch | R&D | evaluating | Evaluate |
| comfyui-inpaint-nodes | R&D | evaluating | Evaluate |

### Candidate (14) — mostly not installed

| id | Cloned locally? | usedBy claim | Ladder | Rec |
|---|---|---|---|---|
| openspec | **MISSING** (`openspec` not on PATH) | game-designer, PM, gameplay-programmer | R only | Evaluate then install-or-drop |
| claude-code-game-studios | **not found** under workspace/SourceGame | [] | R only; overlaps Company OS roles | Evaluate (overlap risk) → likely Defer |
| awesome-gamedev-agent-skills | not found | gameplay-programmer, ui, designer | R only | Evaluate subset (Godot skills) |
| playwright-mcp | registry claims Claude config 2026-11-03; **0 hits in ~/.claude.json today** | qa, ui-designer | R; config drift | Evaluate / re-verify |
| hoppscotch-mcp | same; 0 hits | [] | R | Defer (needs backend games) |
| awesome-design-md | not found | ui, web | R | Evaluate |
| open-design | not found | ui | R | Evaluate |
| taste-skill | not found | [] | R | Defer |
| react-bits | not found | ui, web | R | Evaluate for web |
| emil-design-eng-skills | not found | ui, web | R | Evaluate |
| hallmark | not found | web | R | Defer |
| gsap-skills | not found | ui, web | R | Evaluate for motion web |
| scroll-world | not found | ui | R | Defer |
| canvas-ui | not found | web | R | Defer |

### Rejected (1)

| id | Status | Rec |
|---|---|---|
| impeccable | rejected | **BLOCKED** — cannot reactivate for convenience |

---

## 1.2 Unregistered / local capabilities (discovered, not in registry)

| Capability | Where | Status note |
|---|---|---|
| Godot 4.6.3 | WinGet link `godot.exe`; Agent allow rules | **Gap:** used in Agents + catalog; **no registry id** |
| `studio-art-identity-and-refinement` | `knowledge/departments/game/skills/...` | Generated KD skill; not a registry dep |
| Knowledge Delivery packages | `config/paperclip/generated/{game-artist,catalog}` | Generated; P1–P4 **not approved** |
| Company paperclip skill | `.claude/skills/paperclip` | Project-level; Board Operator |
| Cursor user skills (~29) | `~/.cursor/skills-cursor` | Personal/IDE; not Company Agent delivery |
| Claude synced skills (docs/docx/pdf/…) | `~/.claude/skills/synced/...` | User Claude; not SOU Agents |
| Cursor MCP: elevenlabs | `~/.cursor/mcp.json` | Unregistered for Company Agents |
| Cursor session MCP plugins | figma, postman, canva, github, google-drive, x, browser, computer-use (this IDE session) | **Operator/Cursor only**; not Paperclip Agent allowlists |
| my-game MCP: pixellab, elevenlabs | `~/.claude.json` project C:/WorkSpace/my-game | Outside Company OS Agents |
| R&D art construction / Sealwarden V2 docs | sandbox + `rnd/art-construction/v2` | Offline Board work; not Agent-activated |
| S2 Godot JSON→Skeleton2D spike | `rnd/godot-spikes` (scripts; images cleaned) | Proven mechanics; K5 animation skill deferred |
| package-game-artist | `~/game-studio-workspace/package-game-artist` | Present; KD deployment not live |

---

## 1.3 CLI / service spot-check (2026-11-23)

| Tool | Present |
|---|---|
| claude, codex, agent, cursor-agent, gh, godot, node, npx | YES |
| openspec | **NO** |
| Paperclip :3100 | **DOWN** |
| ComfyUI prod :8188 | **UP** (PID 17660) |
| ComfyUI R&D :8189 | **DOWN** |

---

## 1.4 Departments & projects covered

- Departments: **company**, **game**, **web** (`knowledge/departments/`)
- Roles in `agents.json`: director, producer, project-manager, game-designer, ui-designer, qa-engineer, gameplay-programmer, game-artist, web-engineer, code-reviewer
- Projects: lamplight-vigil (game), soucean-game (web); Deckbound/Sealwarden work is art-pipeline / R&D under game department knowledge, not a separate registry project id in this audit slice
