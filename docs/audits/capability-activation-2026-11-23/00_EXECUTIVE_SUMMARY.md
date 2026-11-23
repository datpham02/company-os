# Company-Wide Capability Activation Audit

Date: 2026-11-23  
Mode: **read-only**  
Scope: entire AI Studio ecosystem (not Art-only)

## Verdict

The Company has **registered more capabilities than it can systematically discover and use**.

Activation breaks at predictable layers:

| Layer | State |
|---|---|
| REGISTERED | Strong — 36 entries in `dependencies/registry.yaml` |
| INSTALLED | Partial — core CLIs + ComfyUI + some skills present; most `candidate` packs **not** cloned |
| DISCOVERABLE | Weak — Agents do not auto-load most registry notes or candidate repos |
| ACCESSIBLE | Constrained — profile allowlists; Cursor sandbox disabled; KD packages generated but **P1–P4 not approved** |
| INVOKED | Sparse — heartbeats off for several roles; Paperclip API not listening on `:3100` during this audit |
| EFFECTIVELY USED | Narrow — Claude Code + Cursor sessions + offline Board/Claude Code art spikes; not a closed Agent loop |

**usedBy in the registry is not runtime usage.**

## Top P0 (approved/useful, not properly activated)

1. **Knowledge Delivery catalog + game-artist role package** — generated under ADR-024 / PR #110, but KD deployment P1–P4 not approved → Agents cannot be assumed to load it.
2. **`studio-art-identity-and-refinement` skill** — exists in knowledge tree; not confirmed as Agent-invoked skill discovery.
3. **Paperclip skill (`.claude/skills/paperclip`)** — installed; Board Operator path works in chat; company Agents’ heartbeat paths not live this audit (`:3100` down; several `heartbeat.enabled: false`).
4. **Godot 4.6.3 + S2 JSON→Skeleton2D pattern** — installed/proven offline; not wired as a reusable Agent skill package (K5 deferred).
5. **Art Ops / comfy-draft / comfy-edit allow rules** — present for `game-artist`; game-artist still “not live” historically (OQ-045) and heartbeat off.

## Do not activate just because available

- 14 `candidate` skill/design repos — mostly uninstalled; evaluate before any GO.
- `impeccable` — **rejected**; cannot reactivate for convenience.
- `docker-desktop` — approved in registry but ADR-013 conflicts for v1 Docker-required paths.
- `codex` — approved install, `usedBy: []`, Board deferred (OQ-010).
- R&D Klein/Fooocus/ToonOut — `evaluating`; not production Agent tools.

## Success gap

The studio cannot yet demonstrate that Agents **systematically** discover and apply the best approved capability per task. Closing that gap is mostly **routing, KD approval, heartbeat/live Agent policy, and skill packaging** — not more repositories.
