# ADR-021: Laravel and MySQL Backend, No Supabase

- **Status:** Accepted
- **Date:** 2026-11-05
- **Deciders:** Board Operator
- **Decides:** the backend part of D4 in the [game platform contract](../../knowledge/company/shared/game-platform-contract.md), and how real-time works. Hosting stays pending (candidate: Vietnix).
- **Amends:** [ADR-013](ADR-013-native-windows-studio-host.md) in part: Docker is allowed as a platform project's local development stack (see Decision). The studio host itself (Paperclip, providers, agents) still runs natively without Docker.
- **Related:** ADR-010, ADR-014, ADR-020, OQ-036 (superseded), OQ-037

## Context
The game platform contract (ADR-020) left D4, the backend and hosting provider, to the Board. The Game Director had recommended Supabase (a hosted backend-as-a-service, where the browser talks to the database directly and row-level security is the boundary) and Cloudflare Pages. The website (Soucean Game) and every game leaderboard need one backend: anonymous identity, score submission with server-side validation, weekly boards, later accounts and an admin view.

## Decision
- The backend for platform projects is a **Laravel (PHP) application with MySQL**. **Supabase is not used.**
- **Security boundary: the Laravel API.** MySQL is never reachable from the internet; only the Laravel application connects to it. Every check in the contract (server-derived week, plausibility model, rate limits, name rules, data minimisation) runs in Laravel code: validation, policies, services.
- **Anonymous identity** is a Laravel-issued token (for example Sanctum personal access tokens). There is no public database key; the client holds only its own player token.
- Migrations live in the platform repository and are reviewed like code. Production migrations are a Board action (production-environments.md §3).
- **Real-time:**
  - Event-driven real-time (live leaderboards, lobbies, presence, chat, turn-based games) uses **Laravel Reverb**, Laravel's own WebSocket server, in the same application.
  - A fast-paced game that needs a server-authoritative simulation loop (for example 20–60 updates per second) gets a **dedicated game server**, decided per game by its own ADR. The leading candidate is Colyseus (Node.js/TypeScript, sharing code with TypeScript games), `UNVERIFIED`. Laravel stays the authority for accounts and scores; a game server reports match results to it.
- **Local first, in Docker.** Until the Board decides hosting, everything runs on the company machine only, with fake data. The platform repository provides a **Docker Compose stack** (Laravel app with PHP-FPM, MySQL, Reverb; later Redis or a queue worker if needed). PHP, Composer and MySQL are not installed on Windows. Nothing is deployed and no hosting account exists.
  - The **Board** starts and stops the long-running stack (`docker compose up -d`, `docker compose down`).
  - **Agents** run tests in a throw-away container from their own task worktree, so each Task tests its own code: `docker compose run --rm test` (SQLite in memory, no shared database). Agents never start long-running containers, never mount paths outside their worktree, and never run `docker` commands other than the ones the platform repository's `AGENTS.md` lists.
  - The same images can run on the hosting server later, which keeps local and production close.
- **Hosting is not decided.** It must run long-lived processes (PHP-FPM, Reverb, later a game server) and MySQL behind HTTPS, so it is a VPS or cloud server, not shared hosting. **Candidate: a Vietnix NVMe VPS** in Vietnam, chosen over AWS for cost, VND billing and data staying in Vietnam (the announcement of AWS's Hanoi Local Zone, available since 2026-06-19, does not list managed MySQL). Tracked in OQ-037.
- **Portability.** No provider-specific service is used: standard Laravel, MySQL, Reverb and versioned deploy scripts, so moving to another host is "new server, restore MySQL, switch DNS".
- Docker Desktop (already on the company machine) is registered in `dependencies/registry.yaml` as approved for platform projects. Its engine must be running for the stack and for agent tests.

## Alternatives considered
| Alternative | Why not chosen |
|---|---|
| Supabase (Director's recommendation) | Board decision. Also: free projects may pause when traffic is low, and the database is exposed to the browser, so a wrong policy makes it writable |
| Another backend-as-a-service | Same exposure model and vendor lock-in |
| Node.js backend | The Board chose PHP/Laravel |
| AWS (EC2, RDS) | More expensive and complex at this size; billed in USD with egress fees; managed MySQL is not listed for the Hanoi Local Zone, so player data would likely leave Vietnam. Reconsider when the company needs managed high availability or scaling |

## Consequences
- The contract's server and credentials sections use "the Laravel API is the only database client" instead of "row-level security plus a database function" (recorded in contract version 1 together with this ADR).
- Once hosted, the company runs a server: operating-system and PHP updates, daily MySQL backups to storage outside the server, uptime monitoring, paid anti-DDoS once a real-time game is public. These become Board or (later) `devops-engineer` duties.
- No free-tier pause risk; full control of data and code; one backend can serve both game leaderboards and the website.
- Roles that test platform code need the platform repository's test command (`docker compose run --rm test*`) in their allowlists. Docker access is powerful (a container can mount host paths), so allowlists name exact commands; `cursor` agents rely on Cursor's classifier for this, a known weaker spot. Dependency additions (`composer require`) still need Board approval (R5).
- The stack itself (Dockerfile, `compose.yaml`, the `test` service) is built in the Soucean Game repository by `web-engineer`, as a Task.
- OQ-036 (Supabase identity and free tier) is superseded.

## Reconsider when
Operating the server costs more than a managed service would, a game needs managed high availability or multi-server scaling, or Reverb cannot carry a game's event volume.
