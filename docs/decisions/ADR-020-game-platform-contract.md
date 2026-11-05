# ADR-020: Game Platform Contract, Version 1

- **Status:** Accepted
- **Date:** 2026-11-05 (Board approval of the design: 2026-11-04)
- **Deciders:** Board Operator
- **Amends:** [ADR-014](ADR-014-platform-project-type.md) §3 (the contract placeholder)
- **Related:** ADR-005, ADR-010, ADR-019, OQ-036 to OQ-039, [game-platform-contract.md](../../knowledge/company/shared/game-platform-contract.md)

## Context
ADR-014 reserved a game–platform contract for every game and platform project and left it to Paperclip issue GAM-16. In GAM-16 the director proposed the contract (adapter, mount, embedding, manifest, host behaviour) together with decisions on identity, name moderation, anti-cheat, privacy and weekly rules (D1 to D6). On 2026-11-04 the Board approved all of it except D4 (backend and hosting provider), which stays pending. GAM-16 then lived only as Paperclip comments in a company that has since been archived. The first implementation (SOU-1, Lamplight Vigil's platform adapter) needs the contract as text.

## Decision
- The contract in [knowledge/company/shared/game-platform-contract.md](../../knowledge/company/shared/game-platform-contract.md) is **version 1** and binding for every game and platform project.
- Its core rules:
  - games reach a backend only through the injected `Platform` adapter, with `LocalPlatform` as an offline fallback;
  - games are mountable and destroyable without leaks;
  - the website embeds games in an iframe by default;
  - rewards and entitlements are granted only by the server;
  - the server derives the week and validates every score against a per-game plausibility model, with row-level security and one validating function as the boundary;
  - data is minimal, there is no ad or analytics SDK inside games, and agents never hold backend admin or deploy credentials.
- The Game Director's suggestion of two ADRs (platform contract and mount contract) is merged into this one: both parts are always adopted together.
- D4 (provider and hosting) is **not** decided by this ADR. Provider names in the contract are candidates only.
- Changes follow the contract's versioning rules: additive changes raise the minor version; breaking changes need a new ADR.

## Alternatives considered
| Alternative | Why not chosen |
|---|---|
| Keep the contract only in Paperclip (GAM-16) | Agents cannot read other issues, and the issue is now in an archived company |
| Put the contract in the Lamplight Vigil repository | It binds every game and the website; it belongs to Company Core as a cross-department contract (ADR-019) |
| Two ADRs (platform, mount) | They are always adopted together; one record is easier to follow |

## Consequences
- SOU-1 and every later game and platform task cite this file instead of GAM-16.
- A game's `game.json` and a platform's `docs/game-platform-contract.md` must name the contract version they implement.
- D4 must be decided before any task calls a real backend; contract version 2 is expected to add the iframe message schema and provider specifics.

## Reconsider when
D4 is decided, the website implements embedding, or a game needs a capability the interface cannot express.
