# Game Platform Contract

**Status:** `PLANNED`. This is a placeholder. **Owner of the design:** `director`, in Paperclip issue **GAM-16**. **Adopted by:** a future ADR that supersedes or amends [ADR-014](../../../docs/decisions/ADR-014-platform-project-type.md) §3.

This document will define how a game and a platform project (for example the studio website) work together. Every game and every platform follows it. Do not design it anywhere else while GAM-16 is open.

## What GAM-16 fills in

| Section | Content GAM-16 delivers |
|---|---|
| 1. Platform adapter interface | The `Platform` interface a game calls, for example `getPlayer()`, `submitScore()`, `getLeaderboard()` and `onPause` / `onResume`. Also the local-only fallback when no platform is present. |
| 2. Mount and destroy | The mount function's signature and config object. `destroy()` guarantees: no leftover listeners, audio or timers. |
| 3. Embedding | iframe with `postMessage`, or ES module import. The recommendation and its trade-offs: isolation versus shared login. The message schema, if iframe. |
| 4. Game manifest | Fields, for example `game_id`, title, version, thumbnail, controls and leaderboard types. Also the file name and location in the build output. |
| 5. Build rules | Relative asset paths, a configurable base path, `localStorage` keys namespaced by `game_id`, and no globals except the mount function. |
| 6. Host behaviour | Pause on blur, keyboard capture only while focused, audio only after a user gesture, and letterboxing inside the container. |
| 7. Optional capabilities | How a game declares capabilities, for example `rewardedAd` and `purchases`. Shapes such as `showRewardedAd(placement)`, `purchase(sku)` and `getEntitlements()`. Lamplight Vigil declares none. |
| 8. Server authority | Score plausibility checks, rate limits, the submitted fields (seed, week, duration, game version) and server-only granting of rewards and purchases. |
| 9. Versioning | The contract version, how games and platforms declare which version they support, and the compatibility rules. |

## Rules already fixed by the Board (2026-11-04)

These are inputs to GAM-16, not design choices:
- Ads appear **only on platform pages**, around the game frame. A game that declares no ad capability contains no ad SDK and no ad hook.
- A game never calls a backend directly. It talks only to the platform adapter.
- Rewards and purchases are granted **only by the platform server**, after it verifies the ad completion or payment. A purchase requires a linked real account.
- Players get an anonymous identity by default, with optional account linking.
- Minimal data: player id, display name, game id, week, score, time survived, seed, game version and timestamps. No email unless the player links an account, and no analytics inside games.
- The game must stay playable offline or when the platform is down.

## Related documents
- [../../../docs/decisions/ADR-014-platform-project-type.md](../../../docs/decisions/ADR-014-platform-project-type.md) · [project-system.md](../../../docs/design/project-system.md) · [../../../docs/architecture/security-architecture.md](../../../docs/architecture/security-architecture.md)
