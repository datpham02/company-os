# Game Website — Plan

- **Status:** `APPROVED` (Board Operator, 2026-11-04). GAM-16 stays sequential: it starts after GAM-15 closes the Playable Vigil milestone. M2 waits for it.
- **Date:** 2026-11-04
- **Project:** `game-website`. The id is a placeholder; the Board picks the name. Type `platform`, status `planned` ([ADR-014](../decisions/ADR-014-platform-project-type.md)).
- **First game:** Lamplight Vigil.
- **Dependency:** the [game platform contract](../design/game-platform-contract.md), designed in **GAM-16**. Everything marked **[GAM-16]** below waits for it.

This plan lives in the framework repository only while the project is `planned`. When the Board creates the website repository, it becomes the seed of that repository's `docs/requirements.md` and `docs/architecture.md`.

## 1. Goals and non-goals

**Goals**
- One website that lists the studio's games and lets anyone play them in the browser, with no sign-up.
- Shared online features for every game: one player identity, weekly leaderboards with a weekly reset, and a personal all-time best.
- Revenue from **ads on the website page only**, never inside a game.
- Private by default: minimal data, consent before ads or non-essential cookies, and a clear privacy policy.

**Non-goals (v1)**
- Payments, top-ups, in-game purchases and rewarded ads. The contract leaves room for them, but they need a payments ADR and legal review first. See §8.
- Chat, friends, comments or other user-generated content beyond a display name.
- Analytics or telemetry inside games. Website analytics, if any, come later, behind consent and with a Board decision.
- A self-run server. Use managed services only.

## 2. Pages

| Page | Route (proposed) | Content | Notes |
|---|---|---|---|
| Home / game list | `/` | A card per game from **each game's manifest** **[GAM-16]**: thumbnail, title, short description, controls, a "Play" button, and this week's top 3 | The list is built from the manifests at build time, so adding a game is adding its manifest and build. |
| Play page | `/games/<game_id>` | The game frame (mounted or iframe **[GAM-16]**), title, controls, a weekly leaderboard beside or below it, and the ad slots (§4) | The game fills its container and letterboxes. The page never overlaps the frame. |
| Leaderboards | `/leaderboards`, `/leaderboards/<game_id>` | This week's board per game, last week's final board, and the player's own rank and personal best | The week starts Monday 00:00 UTC+7, as GAM-16 recommends; GAM-16 confirms. |
| Account and profile | `/account` | Display name (editable, moderated), the anonymous id state, "Link Google or email" to keep scores across devices, sign out, and delete my data | Linking keeps the same player id (OQ-036). Delete removes the scores and the profile. |
| Privacy policy | `/privacy` | What is stored, why, for how long, who processes it (backend, hosting, ad network), the player's rights, and contact | Written with legal input (OQ-039). Covers Decree 13/2023, and GDPR if EU players are expected. |
| Cookie consent | Banner on first visit, plus a `/privacy#cookies` settings link in the footer | Accept / Reject / Settings. **No ad script loads before consent.** Essential storage (session, consent choice) only | Equal-weight "Reject". If ads are shown to EU/UK visitors, a certified consent tool may be required (OQ-038). |
| Footer pages | `/about`, `/terms` | Studio info, terms of use and contact | Ad networks usually expect these (OQ-038). |

## 3. Recommended stack

| Layer | Recommendation | Why | Alternative |
|---|---|---|---|
| Frontend | TypeScript with a static-first framework, for example **Astro** with small interactive islands, or Vite + React | Fast static pages for SEO and ad approval, and simple hosting. The game page needs only one interactive island | Next.js (static export) |
| Identity | **Supabase Auth**: anonymous sign-in on first visit, with optional linking of **Google** or **email (magic link)** | Matches the Board decision: no sign-up to play, and scores survive across devices once linked (`UNVERIFIED`, OQ-036) | Firebase Auth |
| Data | **Supabase Postgres** with **row-level security on every table** | Players can write only their own rows. Reads of the boards are public. Score submission goes only through a server function | Firebase Firestore |
| Server logic | **Supabase Edge Functions** (or Postgres functions) for `submit_score` | Moderate anti-cheat: a maximum score for the time survived, rate limits, and a check of seed, week, duration and game version. No replay verification | — |
| Hosting | **Cloudflare Pages** (static), with preview deploys per branch | Free tier, CDN, custom headers for CSP, and preview URLs for review (`UNVERIFIED`, OQ-037) | GitHub Pages (no previews), Netlify, Vercel |
| Ads | Google AdSense first, evaluated against alternatives | Common and simple. Needs an own domain, content, traffic and policy compliance (`UNVERIFIED`, OQ-038) | Ezoic, Media.net, game-portal ad networks |
| Tests | Vitest (unit), pgTAP or SQL tests for RLS, and Playwright end-to-end | RLS is the main security boundary and needs its own tests | — |

**Data model sketch.** The final version follows GAM-16.
- `players`: id (the auth user id), display_name, created_at.
- `scores`: player_id, game_id, week, score, time_survived_ms, seed, game_version, created_at. Unique on (player_id, game_id, week), keeping the best.
- Views or functions for the weekly board and the personal best.
- Nothing else: no email copy (Auth keeps it only if the player links), no IP logging in tables, and no analytics.

**Environments.** These follow [security-architecture.md §10](../architecture/security-architecture.md#10-production-environments-platform-projects).
- `game-website-dev`: a Supabase project with fake data. Its keys are bound only to `web-engineer` and `qa`.
- Preview deploys: these use the dev project.
- Production: a separate Supabase project. The Board alone holds its keys, applies its migrations and controls its deploys.

## 4. Ad slots and the game frame

```text
┌──────────────────────────── header ───────────────────────────┐
│ [ad: leaderboard banner 728×90, top of page, above the fold]   │
├───────────────────────────────────────────────────────────────┤
│                                    ≥ 24 px     ┌────────────┐ │
│  ┌──────────── game frame ─────────┐  margin   │ ad: 300×250│ │
│  │                                 │◄────────►│ sidebar     │ │
│  │   game (letterboxed 16:9)        │           │ (sticky off)│ │
│  │                                 │           └────────────┘ │
│  └─────────────────────────────────┘           weekly board   │
│        ≥ 24 px margin below                                    │
│  controls · how to play · this week's board                    │
│ [ad: in-content banner, below the game info, never directly    │
│  under the frame]                                              │
└───────────────────────────────────────────────────────────────┘
Mobile: no sidebar. One banner above the frame, one after the game info.
```

Rules:
- **Clear margin:** at least 24 px of empty space, and SHOULD be more, between any ad and the game frame, on every side and at every breakpoint. No ad is directly adjacent to the game's controls area.
- An ad never overlaps, covers or sits inside the frame. No pop-ups, no interstitials and no sticky ad over the game.
- Clicks and keyboard input go to the game only while it has focus. This is a game-side guarantee **[GAM-16]**.
- While a game is playing, the page does not reflow (ads reserve fixed slot sizes), so the frame never jumps.
- Ad scripts load only after consent. With consent rejected, the slots show nothing or a house promotion for another game.
- The ad-network placement policies are checked in OQ-038 before the ads milestone.

## 5. Milestones by role

The roles are `web-engineer` (new), `ui-designer`, `qa`, `project-manager`, `producer`, `game-director` and the Board. Each milestone ends with Board approval.

| Milestone | Content | Roles | Exit criteria |
|---|---|---|---|
| **M0: Setup** (Board-heavy) | Board: approve ADR-014 and this plan, pick the name, create the GitHub repository, the Paperclip project and the agents, and the dev Supabase and hosting accounts (§7). `producer`: answer OQ-036 to OQ-038 from official docs. `web-engineer`: seed the repository (`AGENTS.md`, `docs/`, CI, lint, test skeleton, CODEOWNERS for security-sensitive paths) | Board, producer, web-engineer | The repository builds in CI, preview deploys work, and nothing in the repo points at production. |
| **M1: Static site** | Home with a hard-coded Lamplight Vigil card, the play page embedding the built game, about/terms/privacy drafts, the responsive layout with ad-slot placeholders and margins | ui-designer (layout, design system), web-engineer, qa (e2e, accessibility, layout margins at all breakpoints) | Lamplight Vigil plays on a preview URL, the frame letterboxes, and the margins are verified by tests. |
| **M2: Contract integration** (after GAM-16) | Game list from manifests, mount/destroy or iframe per the contract, the platform adapter on the website side, pause on blur | web-engineer, game-director (contract questions), qa | Two dummy games or one real game mount and unmount with no leaks, per the contract tests. |
| **M3: Identity and leaderboards** (security-sensitive) | Anonymous sign-in, account linking, the display name with moderation, the `scores` schema with RLS, the `submit_score` function with plausibility and rate limits, weekly boards, personal best, and "delete my data" | web-engineer, qa (RLS tests, e2e), **Board human review** | RLS tests prove players cannot write others' rows or forge the week. The Board reviews auth and RLS PRs. The Board applies the prod migration. |
| **M4: Privacy and consent** | The consent banner and settings, the final privacy policy (legal input), and consent-gated script loading | web-engineer, ui-designer, qa, Board (legal) | No third-party request before consent, verified with Playwright. The Board approves the policy text. |
| **M5: Public launch and ads** | Domain, production deploy, ads.txt, the ad-network application, ads switched on behind consent | **Board** (domain, accounts, prod deploy), web-engineer (integration on a branch), qa | The site is live, the ad network is approved, and the ad margins hold in production. |
| Later | More games, rewarded ads or purchases (separate ADR and legal), optional website analytics | — | Board decision |

## 6. Security and review summary
- Production keys are never bound to agents. The Board holds them. Agents use the dev project only.
- Production deploys, production migrations, DNS and ad settings are done by the Board.
- PRs on auth, RLS, `submit_score` or rewards, payments, secrets or CSP are **security-sensitive**. They need a Board review in addition to `qa`.
- Full rules: [security-architecture.md §10](../architecture/security-architecture.md#10-production-environments-platform-projects).

## 7. External accounts and Board decisions

Nothing below is created by an agent. The Board does each step, or says yes in its own words first.

| # | Item | Decision or action | When |
|---|---|---|---|
| 1 | ADR-014 | Accept, change or reject | Now |
| 2 | This plan | Approve or change pages, stack and milestones | Now |
| 3 | GAM-16 timing | Keep it after GAM-15, or pull it forward. M2 waits for it | Now |
| 4 | Website name and id | Becomes the repository name and the domain idea | Before M0 |
| 5 | GitHub repository `datpham02/<id>` | Create it with branch protection (PR, 1 approval, no force-push) | M0 |
| 6 | Paperclip project and the `web-engineer` agent | Create them and bind only dev secrets | M0 |
| 7 | Supabase | Create an account (studio-owned email) and **two** projects: dev (shared with agents) and prod (Board only). Enable anonymous sign-in, and Google OAuth later | M0 / M3 |
| 8 | Google OAuth client | Create it in Google Cloud for account linking | M3 |
| 9 | Hosting | Cloudflare account and a Pages project connected to the repository. Production branch `main`, previews for task branches | M0 |
| 10 | Domain | Buy it and point DNS at the hosting (needed for ads) | Before M5 |
| 11 | Ad network | Apply to AdSense or an alternative after launch, with real content and traffic | M5 |
| 12 | Legal | A lawyer checks Decree 147/2024 for a free game site with ads, Decree 13/2023 for personal data, the privacy policy and the terms (OQ-039) | Before M5 |
| 13 | Payments (deferred) | Any top-up or purchase first needs the Vietnamese online-game licence (Decree 147/2024/ND-CP), a payment provider (VNPay, MoMo, ZaloPay, Stripe), refunds and tax, a lawyer and a payments ADR | Not in v1 |

## 8. Open questions
OQ-036 (Supabase identity and free tier), OQ-037 (hosting), OQ-038 (ads and consent), OQ-039 (legal), all in [open-questions.md](../architecture/open-questions.md). Contract questions belong to GAM-16.
