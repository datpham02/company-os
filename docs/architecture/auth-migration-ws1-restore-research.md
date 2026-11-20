# WS-1.1: Paperclip restore capability research

- **Status:** `PROPOSED`. Research and documentation only.
- **Date:** 2026-11-20.
- **What was not done:** no restore, backup, upgrade, sandbox, live-database access or configuration change.
- **Decision context:** D-AUTH-10 in [auth-migration-phase-a5-board-decisions.md](../roadmap/auth-migration-phase-a5-board-decisions.md); workstream WS-1 in [auth-migration-phase-a5-plan.md](auth-migration-phase-a5-plan.md).
- **Prior evidence:** VA-9 and SF-2 in [auth-migration-phase-a4-verification.md](auth-migration-phase-a4-verification.md); VA-9 in [auth-migration-verification-plan.md](auth-migration-verification-plan.md); OQ-025 in [open-questions.md](../roadmap/open-questions.md).

**Evidence labels:**
- **[doc]:** official Paperclip documentation, either the repository `docs/` and `doc/` folders or the docs site.
- **[source]:** code that exists in the Paperclip source.
- **[used]:** a code path that a Paperclip command or route actually calls.
- **[issue]:** a GitHub issue or pull request.
- **[local]:** a read-only observation on this machine.
- **[inference]:** a conclusion drawn from the above.

## 1. Executive summary

1. **There is no supported restore method.**
   - No Paperclip version up to v2026.1117.0 (the latest release) or `master` has a user-facing database restore command, API or documented procedure. [source] [doc]
   - The documentation says what a disaster recovery needs: the database, the secrets master key and the object store. It gives no restore steps. [doc]
   - A user request for `db:restore` (#4407) and two community PRs adding one (#8574, #14079) are open, with no maintainer answer or merge. [issue]
2. **A restore routine exists only as internal code.**
   - `runDatabaseRestore` replays a dump into an **empty** database, with `psql` or a JavaScript fallback.
   - Paperclip calls it only when seeding developer worktrees. That flow produces a sanitized clone, not a full restore. [source] [used]
3. **Backups on this machine cannot round-trip faithfully today.**
   - The embedded PostgreSQL ships without `pg_dump` and `psql`, and neither is on `PATH`, so every backup here uses the **JavaScript engine**. [local]
   - Open issue #17854 reports that restoring a JavaScript-engine backup **drops every CHECK constraint**: 159 before and 0 after, on 2026.1106.0. It also turns `UNIQUE NULLS NOT DISTINCT` into plain `UNIQUE` and truncates timestamps. [issue]
   - The JavaScript engine also emits no CHECK or exclusion constraints in v2026.1023.0. [source]
4. **Recommendation:**
   - No candidate is ready to satisfy E8 as is.
   - The candidate worth an **isolated** test is **Candidate B, a cold copy of the whole stopped instance folder**, because it keeps the PostgreSQL cluster byte for byte, together with the master key and the files.
   - **Candidate A, dump plus restore,** is worth testing only with PostgreSQL 18 client tools, so that the dump uses `pg_dump` rather than the JavaScript engine. It must be preceded by a Board decision on installing those tools.
   - Both candidates are **technically possible but unsupported**.
5. **E8 stays not met.** OQ-025 stays open.

## 2. Scope and versions inspected

| Item | Version or reference |
|---|---|
| Installed Paperclip | 2026.1023.0: the CLI bundle and the `@paperclipai/db` and `@paperclipai/server` packages of the global install |
| Repository tags | `v2026.1023.0`; `v2026.1117.0` (commit `c0f13289`) |
| Repository `master` | commit `0e38c803` (2026-11-20). Matches v2026.1117.0 for the files checked |
| Release notes | v2026.1106.0, v2026.1117.0 |
| Docs site | https://docs.paperclip.ing/deploy/database (read on 2026-11-20; the quotes below are not verbatim) |
| Embedded PostgreSQL | `embedded-postgres` 18.1.0-beta.16 (PostgreSQL 18.1), patched. The same at both tags |

## 3. Official restore support

| Source | Content | Support status |
|---|---|---|
| `doc/DATABASE.md` "## Backups" (v2026.1117.0, around line 1422) | "Paperclip supports automatic and manual logical database backups". Dumps do not include "uploads, workspace files, or the local encrypted secrets master key. Back those paths up separately …" | Backup documented; no restore procedure |
| `doc/DATABASE.md` line 1358 (v2026.1117.0) | "Disaster recovery requires the database, object store, and original master key." | Requirement stated; no procedure |
| `docs/deploy/secrets.md` "Backup And Restore" (v2026.1117.0, line 430) | For `local_encrypted`: back up the master key file and the database together; "Either alone is not enough to restore the encrypted …" values | Secrets-only guidance; no database restore steps |
| `docs/deploy/database.md` (v2026.1117.0) | Only "To reset: `rm -rf ~/.paperclip/instances/default/db`" | No restore |
| Docs site `deploy/database` | Summarized by the reading tool: restoring identities needs the matching secrets key; disaster-recovery backups are for recovering that instance | Not verbatim; no restore steps found |
| `doc/DEVELOPING.md` "Automatic DB Backups" | Backup defaults, `db:backup`, `PAPERCLIP_DB_BACKUP_*` variables | Backup only |
| Release notes v2026.1106.0 | Nothing on database backup or restore | — |
| Release notes v2026.1117.0 | JavaScript backups keep `bytea` intact (#18650); `KillMode=mixed` for a clean embedded-PostgreSQL shutdown under systemd (#18598). "Skill packages move out of PostgreSQL, and this release becomes the rollback floor" after migration 0415 | No restore command. **This release changes what a database backup covers** (skill packages leave the database) |
| `cli/src/index.ts` (v2026.1117.0) | The only `db:` command is `db:backup` | No `db:restore` |
| Server route `instance-database-backups` (both tags, `master`) | Only `POST /instance/database-backups` | No restore route |
| `company export` guide | Portable company export | Not a database backup |

**Conclusion [doc] [source]:** restore is **not officially supported** in any inspected version. It is not experimental or documented either. It is internal-only.

## 4. Source-code findings (installed 2026.1023.0)

Line numbers refer to the installed CLI bundle `dist/index.js` unless noted.

**Backup (`runDatabaseBackup`, about 45745):** two engines; the default is `auto`.
- **`pg_dump` engine:** `--format=plain --clean --if-exists --no-owner --no-privileges`, then gzip (about 45559-45583). Used when `pg_dump` is available and no transforms are set.
- **JavaScript fallback:** plain SQL generated in JavaScript, wrapped in `BEGIN; SET LOCAL session_replication_role = replica; … COMMIT`, with a statement marker line after every statement (`-- paperclip statement breakpoint …`, about 46250). Its order:
  - schemas, `CREATE TYPE` (without DROP) and `CREATE EXTENSION`;
  - sequences, and tables with primary keys;
  - unique constraints, functions, indexes and foreign keys;
  - one `INSERT` per row; triggers; `setval`.
- **Not emitted by the JavaScript engine:** roles and grants, **CHECK constraints**, exclusion constraints, views (about 45820-46173). Migrations do create CHECK constraints.
- **Used by:** `db:backup`, the server's scheduled, manual and idle backups, and `POST /api/instance/database-backups`. [used]

**Restore (`runDatabaseRestore`, about 46207; `@paperclipai/db` `backup-lib.js` 919):**
1. Pipe the file into `psql --set=ON_ERROR_STOP=1 --no-psqlrc` (`PAPERCLIP_PSQL_PATH` or `psql`).
2. If that fails, and the file carries the statement markers, split it on the markers and run each statement with postgres.js. Otherwise it throws.

**Preconditions it does not check itself:**
- an **empty** target database (`CREATE TYPE` has no DROP);
- a superuser-capable role (`session_replication_role`).

[source]

**The only caller, `seedWorktreeDatabase` (about 52726):**
1. Snapshot the source with an exclusion plan.
2. Start a **new** embedded PostgreSQL (`allowExisting: false`).
3. `resetPostgresDatabase` (drop and recreate the database, about 39187-39198).
4. `runDatabaseRestore`, then `applyPendingMigrations`.
5. Mutate the copy: running agents set to idle; agent-assigned `in_progress` issues set to `blocked`; scheduled routines paused; workspace paths rebound.

Even the "full" seed plan excludes `agent_identity_keys`. The default "minimal" plan excludes activity, runs, wakeups and costs. **This is a sanitized developer clone, not a recovery path.** [source] [used]

**Commands that use it:** `worktree init`, `worktree:make`, `worktree reseed` / `repair` / `ensure-seeded`, all described as helpers for Paperclip development git worktrees. [used]

**Migration behaviour:**
- At startup the server applies pending migrations (prompting on a terminal; automatically when non-interactive or with `PAPERCLIP_MIGRATION_AUTO_APPLY=true`), or refuses to start on a stale schema.
- `applyPendingMigrations` refuses a database that has tables but no migration journal.
- **A database newer than the code is not detected** ("pending" is computed as available minus applied).

[source]

## 5. Backup format and dependencies

| Item | Finding | Label |
|---|---|---|
| Format | Gzip plain SQL. On this machine always the JavaScript engine | [source] [local] |
| Tools on this machine | Embedded `bin` has `postgres.exe`, `pg_ctl.exe`, `initdb.exe`; no `pg_dump.exe` or `psql.exe`; neither on `PATH` | [local] |
| Fidelity | The JavaScript engine drops CHECK and exclusion constraints. Issue #17854 also reports `UNIQUE NULLS NOT DISTINCT` turned into `UNIQUE`, millisecond-truncated timestamps, and no single snapshot | [source] [issue] |
| `bytea` | A JavaScript-backup `bytea` corruption was fixed in v2026.1117.0 (#17119, #18650). **Not fixed in 2026.1023.0** | [doc] [issue] |
| PostgreSQL | 18.1 (embedded). A restore target must be PostgreSQL 18-compatible | [source] |
| Extensions | `pg_trgm` (migration 0051), `fuzzystrmatch` (migration 0080). The target needs them available | [source] |
| Roles | The dump has no roles or grants. The embedded cluster uses role `paperclip` | [source] |
| Outside the database | Secrets **master key** (company secrets are AES-256-GCM, `local_encrypted_v1`; without the original key they cannot be decrypted, and Paperclip silently creates a new key if the file is missing); `PAPERCLIP_AGENT_JWT_SECRET` / better-auth secret (sessions and agent tokens); `PAPERCLIP_TOOL_ACTION_SIGNING_SECRET` (tool-action signatures); `data/storage` (uploads and artifacts); agent workspaces; logs | [source] [doc] |
| Version boundary | From v2026.1117.0, skill packages leave the database after migration 0415, and that release is the rollback floor | [doc] |

## 6. Candidate A: dump and restore into a new isolated instance

| Aspect | Assessment |
|---|---|
| Method | A fresh isolated instance with a **new, empty** database (a new embedded cluster). Replay the dump with `psql` (or the internal JavaScript fallback) into it, with the source instance's master key, `.env` secrets, `data/storage` and workspaces copied alongside. Then start the server |
| Dump compatibility | **With today's JavaScript-engine dumps: not faithful.** CHECK and exclusion constraints are lost, and in 2026.1023.0 `bytea` values can be corrupted. **With a `pg_dump` 18 dump: expected faithful** (plain SQL with `--clean --if-exists`), but no `pg_dump` 18 exists on this machine |
| Roles and extensions | No roles in the dump; the target cluster must have the `paperclip` role. `pg_trgm` and `fuzzystrmatch` must be available. The embedded cluster provides both, as the source runs them |
| Keys | The original master key and `.env` secrets are required. With a different key, secrets are unreadable and sessions and agent tokens break |
| Migrations | The target code version must be **equal to or newer than** the dump's schema. A newer database is not detected |
| Starts without touching the source? | Yes, if the target has its own home folder, instance id and ports (as in A.4) |
| Data loss and inconsistency | JavaScript engine: schema constraints lost; data otherwise copied row by row. Uploads and workspaces only if copied separately |
| Support status | **Technically possible but unsupported.** With JavaScript-engine dumps: **not recommended** for recovery |

## 7. Candidate B: cold copy of the stopped instance folder

| Aspect | Assessment |
|---|---|
| Method | Stop the source instance **cleanly** (server and embedded PostgreSQL), so that `postmaster.pid` is gone. Copy the **whole instance folder** to a new location: `db` (PostgreSQL data directory), `secrets/master.key`, `.env`, `config.json`, `data/storage`, `data/backups`, `workspaces`. Point a new isolated instance at the copy, with a different instance id and ports, and start it |
| Completeness | Keeps the PostgreSQL cluster physically, so constraints, sequences, extensions and the migration journal are exact. Keeps the master key, secrets and files together [inference] |
| Requirements | A clean shutdown (an unclean stop needs WAL recovery, which works but is not a "cold" copy); the same PostgreSQL major version (18) and platform; the copied config edited for the new folder, ports and instance id (`config.json` holds absolute paths) |
| Across machines or users | Same OS and architecture and PostgreSQL major version required. Folder permissions must allow the new user. Absolute paths in the config and in project workspace records must be rebound [inference] |
| Risks | An unclean source stop (seen twice on the live instance, A.4 §2.3) makes the copy crash-consistent rather than cold. A full copy duplicates secrets, so its location must be as private as the original |
| Official support | **Not documented** by Paperclip. Standard PostgreSQL practice for a stopped cluster |
| Support status | **Technically possible but unsupported** by Paperclip. Recommended as the first isolated test candidate |

## 8. Comparison and recommendation

| Criterion | Candidate A (dump and restore) | Candidate B (cold copy) |
|---|---|---|
| Paperclip-supported | No | No |
| Fidelity on this machine | Low with JavaScript dumps (constraints lost); high only with `pg_dump` 18 | High (physical copy) [inference] |
| Extra tooling | `pg_dump` and `psql` 18 to be installed (a decision) | None |
| Needs the source stopped | No for backup; yes for a consistent file copy of the keys and storage | Yes, a clean stop |
| Covers keys and files | Only if copied separately | Yes |
| Restores to a point in time | Any dump | Only when stopped |
| Recommended for an isolated test | Second, after a tooling decision | **First** |

**Answers to the brief:**
1. **Is there a supported restore method?** No, in v2026.1023.0, v2026.1106.0, v2026.1117.0 or `master`.
2. **Which version and procedure?** Not applicable.
3. **Which candidate to test in isolation?** Candidate B first. Candidate A only with a `pg_dump` 18 dump, after a tooling decision. A test of A with today's JavaScript dumps would only reproduce #17854.
4. **What must be approved before testing?** See §10.
5. **What evidence satisfies E8?** A successful isolated restore that passes every comparison in §9, under a method the Board has accepted as unsupported but adequate. E8's A.2 wording is "a restore into the test environment succeeds".

## 9. Proposed isolated verification (not executed)

1. **Source instance:** a fresh isolated instance; own home folder, instance id, ports and fresh secrets; live instance stopped (§3.1 boundaries of [step2-board-decisions.md](../roadmap/step2-board-decisions.md)).
2. **Seed** through the API. As in A.4, plus:
   - a company secret, to prove master-key handling;
   - an attachment or artifact, to prove storage;
   - a membership in each role.
3. **Snapshot** through the API: every company, issue (with assignee, status, `executionPolicy` and `executionState`), each issue's activity, decision ids (`lastDecisionId`), memberships with roles, instance admins, and secret metadata.
4. **Backup or copy:**
   - Candidate A: take the dump with the chosen engine;
   - Candidate B: stop the source **cleanly** (`postmaster.pid` gone) and copy the folder.
5. **Stop** the source cleanly and keep it untouched.
6. **Restore** into a **second** isolated instance: new home folder, instance id and ports.
7. **Start** the restored instance and check health and startup recovery.
8. **Compare:**
   - **Field-level:** per-record JSON equality of the snapshot fields, keyed by id; not row counts alone.
   - **Constraints:** a read-only catalog query (`pg_constraint` count by type) on both clusters, so that a #17854-style constraint loss shows up.
   - **Secrets:** a secret created before can still be resolved (a decrypt test through Paperclip).
   - **Storage:** the attachment can be downloaded.
   - **Auth:** the Board key or a session from the source works (Candidate B), or the expected invalidation is documented (Candidate A with new secrets).
   - **Migrations:** the journal is identical.

**Failure criteria:**
- any compared field differs;
- fewer constraints;
- a secret cannot be decrypted;
- a file is missing;
- the server refuses to start or reports a migration error.

**Stop conditions:**
- the method needs the live instance or its data folder;
- the target folder is not empty;
- an unclean source stop;
- any write to the source after the snapshot.

**Teardown:** as in A.4 §6.

## 10. Prerequisites and Board decisions

1. **Method acceptance:** Candidate B and/or Candidate A, knowing both are **unsupported** by Paperclip.
2. **Tooling, for A:** whether to install PostgreSQL 18 client tools and set `PAPERCLIP_PG_DUMP_PATH` / `PAPERCLIP_PSQL_PATH`. This would also change how **live** backups are made, which is a separate production decision.
3. **Environment:** a new isolated environment (A.4's was torn down), with a stop of the live instance for its duration.
4. **Version:** test on 2026.1023.0, the live version. Testing on v2026.1117.0 would need an upgrade decision. v2026.1117.0 is also a **rollback floor** and moves skill packages out of the database, which changes the backup scope.
5. **Clean-shutdown procedure:** how to stop Paperclip without the unclean Postgres stop seen in A.4. This matters for B and for any live cold copy.

## 11. Risks and stop conditions

- **Silent fidelity loss:** a "successful" restore of a JavaScript dump that lost constraints (#17854). Mitigated by the constraint comparison in §9.
- **Wrong or missing master key:** Paperclip silently creates a new key, so secrets become unreadable.
- **Version skew:** restoring into older code is not detected.
- **Copy location:** a cold copy duplicates secrets; keep it private.
- **Upstream changes:** v2026.1117.0 changes the backup scope and the rollback floor.

Stop conditions are in §9.

## 12. Evidence references and open questions

**References:**
- **GitHub `paperclipai/paperclip`:**
  - files at `v2026.1117.0`: `cli/src/index.ts` (`db:backup`), `packages/db/src/backup-lib.ts` (`runDatabaseRestore`), `cli/src/commands/worktree.ts`, `server/src/routes/instance-database-backups.ts`, `doc/DATABASE.md`, `docs/deploy/secrets.md`, `docs/deploy/database.md`, `doc/DEVELOPING.md`;
  - release notes v2026.1106.0 and v2026.1117.0;
  - issues #4407 (open), #17854 (open), #17119 (closed);
  - PRs #8574, #14079, #17012 (all open).
- **Installed 2026.1023.0:** the CLI bundle and the `@paperclipai/db` and `@paperclipai/server` packages, with locations as in §4 and §5.

**Open questions:**
- Whether better-auth encrypts any stored data with its secret, beyond sessions. Not checked.
- How a cold copy behaves when moved to another Windows user or machine. Not tested.
- Whether upstream will merge a supported restore (PR #14079).
- How to stop Paperclip cleanly on Windows outside `systemd`.
