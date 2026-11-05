# Game Platform Contract

- **Status:** `APPROVED`, contract version **1** ([ADR-020](../../../docs/decisions/ADR-020-game-platform-contract.md)).
- **Source:** designed by `director` (then `game-director`) in Paperclip issue GAM-16 (sections 3 and 4) and approved by the Board on 2026-11-04. GAM-16 is in the archived company "Game Studio Soucean"; this file is now the source of truth.
- **Pending:** D4, the choice of backend and hosting provider. Provider names below (Supabase, Cloudflare) are the recommended candidates, not decisions. Nothing may depend on a specific provider until the Board decides D4.
- **Owners:** design `director`; Game side the Game department, platform side the Web department ([shared contract](../../departments/README.md#placement-rules)).
- **Applies to:** every game and every platform project. Amends [ADR-014](../../../docs/decisions/ADR-014-platform-project-type.md) §3, which pointed here.

## 1. Platform adapter

A game never imports a backend SDK. It talks to one injected interface, `Platform`:

```text
capabilities                 a read-only set: leaderboard, rewardedAd, purchases
getPlayer()                  resolves to a player: id and displayName
submitScore(entry)
getLeaderboard(query)
onPause(cb) / onResume(cb)   each returns an unsubscribe function
```

- A game declares only the capabilities it uses, and never calls a capability that is absent from `capabilities`. Lamplight Vigil declares `leaderboard` only.
- **With no platform injected, the game falls back to `LocalPlatform`**: `localStorage` only, zero network, full gameplay. The same path keeps the game alive when the backend is down.
- **Review rule:** gameplay code (for a Phaser game: `src/beam`, `src/enemies`, `src/hud`, `src/scenes`) imports nothing backend-related. A grep for the provider name outside the single adapter file fails review.

**Optional capabilities, named now and implemented nowhere yet:**

```text
showRewardedAd(placement)    resolves to granted true or false
purchase(sku)                resolves to a receipt
getEntitlements()            resolves to the entitlement list
```

- A later game adds a capability flag instead of changing the interface.
- **The server grants rewards and entitlements only after it verifies the ad or the payment. The client never grants them.**
- Anonymous players may play and rank, but must link a real account before buying.
- **Fairness:** a run that consumed any entitlement goes to a separate, unranked board. The server decides this from the entitlements it granted, never from a client flag.

## 2. Mount and destroy

```text
mount(element, config)       returns a handle
handle.destroy()             stops everything: listeners, timers, audio, the engine instance
```

- The standalone page is just another caller of `mount()`; a game never assumes it owns the page.
- **Acceptance test:** mount two instances into two elements, destroy one, confirm the other keeps running with no leaked listeners, timers or audio nodes; then destroy and re-mount in a loop and confirm nothing grows.

## 3. Embedding

Default: **iframe with `postMessage`**. ES module import stays possible, but the website does not use it by default.

| | iframe + postMessage | ES module import |
|---|---|---|
| Isolation | Full: a game crash or CSS collision cannot take the page down | None |
| Ad safety | The game cannot draw over an ad slot | Depends on every game |
| Login | Not shared by default | Shared |
| Versioning | Per game | Coupled to the site build |

Login across the frame: the parent posts a **short-lived token** through a `postMessage` handshake and the game hands it to its `Platform`. Cookies and `localStorage` are never shared across origins. The message schema is fixed in contract version 2, together with the website's first implementation.

## 4. Build and host behaviour

- Relative asset paths with a configurable base path.
- `localStorage` keys namespaced by game id (for example `lamplight-vigil.best-score`).
- One global export: the mount function.
- **Pause on blur and on visibility change.** A pause stops the run clock, so it can never earn score.
- **Keyboard capture scoped to the container**, not the window.
- **Audio only after a user gesture** (browser autoplay rules inside an iframe).
- Fill the container and letterbox, bound to the parent element, not the window.

## 5. Game manifest

Each game ships a `game.json` that the website lists: game id, title, version, thumbnail, controls, leaderboard types, required capabilities, and the contract version it implements.

## 6. Identity and display names

- **Identity is anonymous and created lazily**, on the first score submission, not on first visit. The player id is kept in the browser under a game-namespaced key.
- Linking a real account (for example Google or email) **migrates the existing player id**; it never creates a second one.
- **Display names:** 3 to 12 characters (A–Z, a–z, 0–9, single internal spaces); a server-side deny-list applied after normalising (lowercase, strip spaces and digits, collapse leetspeak); one rename per player per week; set on the title screen only, with a generated default such as `Vigil 7421`.
- **Board-only hide:** replaces a displayed name with the generated default without deleting the score. No in-game chat or reporting; a report link belongs to the website.

## 7. Server authority and score validation

Each submission carries `player_id`, `game_id`, `week`, `score`, `duration_ms`, `banished` (or the game's equivalent counter), `seed`, `game_version`.

- **The server derives `week` from its own clock** and ignores the client's value.
- **Per-game plausibility model.** Each game documents the maximum reachable score for a given duration, seed and version, and the server rejects anything above it (with a small tolerance). Lamplight Vigil's model is exact, because its spawn timing is deterministic: `S_max(t) = floor(t × SCORE_PER_SECOND_SURVIVED) + N(t) × SCORE_PER_BANISH`, tolerance 1 % + 1 point.
- Further checks: counters within the model, minimum duration 1 s, a seed that matches the week.
- **Rate limits** per player per hour and per IP per hour, generous enough that a real player never meets them.
- **Database access:** the public (anon) role may read the leaderboard view and execute one validating `submit_score` function. It has no direct insert, update or delete on the scores table. All checks live inside that function.
- **Flag, do not reject,** runs that are plausible but statistically unusual; a human looks at them.
- No replay verification. A patched client can still submit a plausible false score; this is accepted and published: implausible entries are removed without notice.

## 8. Weekly boards

- Unlimited attempts; the best score of the week counts.
- The week resets **Monday 00:00 UTC+7**. All timestamps are stored in UTC; the week key is the ISO week of `timestamp + 7h`, computed in one pure function with `+7` as a single named constant.
- The server derives the week; the client computes it for display only. The screen shows a countdown, never a time zone.

## 9. Data and privacy

| Field | Why |
|---|---|
| `player_id` (uuid) | identity |
| `display_name` | readable board |
| `game_id` | multi-game site |
| `week` | weekly board |
| `score`, `duration_ms`, counter | the entry and its plausibility check |
| `seed`, `game_version` | plausibility check |
| `created_at` | ordering and rate limits |

- No email unless the player links an account. No analytics. No IP column; the privacy note states that the provider processes IP addresses for rate limits and keeps request logs.
- The leaderboard view exposes display name, score, duration, week and rank only, never `player_id`, an auth id or an email.
- **Retention:** weekly score rows 12 months, then deleted. Deletion on request by `player_id`; the delete control lives in the game or on the website. A player who cleared their site data can no longer be identified, and the privacy note says so.
- A short privacy note is required **before** the build is public. Consent banner, full policy, Decree 13/2023 and GDPR work are website-level (OQ-039).
- Every new column is a privacy decision for the Board, not a schema decision.

## 10. Credentials and agent limits

| Credential | Secret? | Held by | May appear |
|---|---|---|---|
| Backend public (anon / publishable) key | No, public by design | Board account, injected at build time | The browser bundle and a build-time environment variable; never a literal in a repository (ADR-010) |
| Backend admin (`service_role`) key | Yes, bypasses row-level security | Board only | Nowhere in a repository, CI, agent environment, issue or comment |
| Backend account and database password | Yes | Board only | Provider console only |
| Hosting account and CI deploy token | Yes | Board only | CI secret store, scoped to deploying one project |

**The public key protects nothing; row-level security plus `submit_score` are the boundary.** A review that accepts a weaker policy "because the key is secret" has the model backwards.

Agents **may**: write migrations, row-level-security policies and `submit_score` as code for Board review; write client code that reads the public key from a build-time variable; document the backend.

Agents **may not**: create or own provider accounts; hold, read, request, print or store the admin key, the database password or a deploy token (if one appears anywhere, report it, do not use or echo it, and ask the Board to rotate it); apply migrations to a live project or edit the database by hand; run admin-key operations; add a third-party SDK to a game, in particular **no ad SDK and no analytics SDK**; weaken a policy to make a test pass.

Migrations live in the repository and are reviewed like code; the database is never edited by hand in a console. Production rules for the website: [production-environments.md](../../departments/web/domain/production-environments.md).

## 11. Risks and required tests

| Risk | Required mitigation |
|---|---|
| A writable public database | No direct write grant; every migration reviewed; a QA test that tries a direct insert, update and delete with the public key and requires all three to be denied |
| Name abuse on a public board | §6 rules and the Board-only hide |
| A free-tier backend pausing when traffic is low | Decided with D4, before building on a free tier |
| Personal data creep | §9: every new column goes to the Board |

## 12. Versioning

- This is contract version **1**. A game's manifest and a platform's `docs/game-platform-contract.md` name the version they implement.
- Additive changes (a new optional capability, a new manifest field) raise the minor version and keep old games working. Changing or removing anything raises the major version and needs a new ADR.
- Version 2 is expected to add the iframe message schema and any D4 provider specifics.

## Related documents
[ADR-020](../../../docs/decisions/ADR-020-game-platform-contract.md) · [ADR-014](../../../docs/decisions/ADR-014-platform-project-type.md) · [Game charter](../../departments/game/README.md) · [Web charter](../../departments/web/README.md) · [security-architecture.md](../../../docs/architecture/security-architecture.md)
