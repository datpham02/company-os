# 8. Representative Verification Test Plan

All tests below are **designed**. Runtime Agent A/B runs require Paperclip up + Board authorization.  
This audit executed **only read-only** checks. Prohibited/unavailable runs = **PENDING**.

Scoring dimensions: correctness · quality · completion · cost · evidence trail.

---

## T1 — Art / Sealwarden V2 (docs only; **no artwork generation**)

**Dept:** game / game-artist  
**Fixture:** Sealwarden V2 board pack (`Sealwarden_Character_Design_Spec.md`, `Sealwarden_Layered_Part_Plan.md` v2, Master_to_Parts_Strategy, CLEAN_SLATE, V2-Master-1 prompt text only).

| Arm | Setup | Expected |
|---|---|---|
| A | Agent **without** studio-art skill / KD package; only generic AGENTS.md | May invent ControlNet/LoRA/R&D Klein; weak gate language; may propose generation |
| B | Agent **with** studio-art skill + catalog view + V2 docs in read set | Cites Gates A–D; refuses unapproved models; treats Defect as quality reference not asset; no gen without Board |

**Runnable now (read-only):** static doc checklist — PASS if V2 pack contains articulation-first rules and Master-1 prompt is text-only Klein proposal marked not run.  
**Agent A/B:** PENDING (Paperclip down; no new Agent deploy; no generation).

Static checklist result (this audit): **PASS (docs)**. Generation: **not run** (Board restriction).

---

## T2 — UI design task (lamplight or soucean-game UI brief)

| Arm | Setup |
|---|---|
| A | ui-designer without invoking ui-ux-pro-max search.py |
| B | Must run `search.py` and cite tokens before proposing layout |

**Status:** PENDING (needs live Agent).  
**Proxy:** skill path + allow rule verified installed.

---

## T3 — Gameplay / Godot integration

| Arm | Setup |
|---|---|
| A | Programmer improvises Skeleton2D without S2 JSON contract |
| B | Follows S2 spike contract + Godot allow commands only |

**Status:** PENDING for Agent; offline S2 mechanics evidence already exists (scripts).  
**Do not** reintroduce deleted prototype images.

---

## T4 — QA web/game smoke

| Arm | Setup |
|---|---|
| A | qa without playwright |
| B | qa with pinned playwright MCP headless isolated |

**Status:** PENDING — playwright not present in ~/.claude.json; installing forbidden this audit.

---

## T5 — VFX sheet via pixelfx

| Arm | Setup |
|---|---|
| A | Hand-describe FX or invent frames |
| B | `list.mjs` → `render.mjs --sheet` under allow rule; license note for Lamplight |

**Status:** PENDING Agent run; install path **verified** (`~/tools/pixelfx`).

---

## T6 — Spec / planning (openspec)

| Arm | Setup |
|---|---|
| A | PM writes freeform plan |
| B | openspec change proposal flow |

**Status:** PENDING — openspec **MISSING**; cannot fair-test B until Board install decision.

---

## T7 — Knowledge refusal / delivery

| Check | Expected |
|---|---|
| Agent without KD tries to Read company-os policy outside workspace | Refuse / block (SOU-88 pattern) |
| Agent with delivered package | Has mandatory excerpts in context without ad-hoc Read |

**Status:** PENDING live; historical SOU-88 cited.

---

## Prohibited during this audit (recorded)

- Installs, downloads, upgrades  
- New Agent deployment / Paperclip config changes  
- Permission changes  
- Generation batches / production asset changes  
- Auto dependency activation  
- Git commit / push / merge  
