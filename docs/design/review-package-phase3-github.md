# Review Package Phase 3: GitHub source

- **Status:** code and offline tests done; **first live run done** (2026-11-20, §4) against `datpham02/soucean-game` PR #27 (read-only). Not covered live: pagination over several pages, a moved head, modified/renamed/deleted files, and the 401/403 path.
- **Phase definition:** [review-package.md](review-package.md) §11, Phase 3 "GitHub source"; procedure §4 option A; token §6.
- **Code:**
  - `.claude/skills/paperclip/scripts/review_github.py` (new);
  - `review_pack.py`: the `--github-pr`, `--github-repo` and `--task-file` options, `load_github_source`, the manifest `source` field.
- **Tests:** `test_review_github.py`, 25 tests against an in-memory fake GitHub, run with the other 153 by `test_pc.py`.
- **G-13 stays open.**

## 1. What the code does

It follows design §4 option A, reads only. The steps below are numbered as in §4.

1. `GET /repos/{o}/{r}/pulls/{n}`: `head.sha`, `base.sha`, `changed_files`, state.
2. `GET /repos/{o}/{r}/compare/{base}...{head}`: the merge base. "Before" content comes from the merge base, not the base tip.
3. `GET /repos/{o}/{r}/pulls/{n}/files?per_page=100&page=…`: read until an empty page. The count must equal `changed_files`. More than 30 pages is refused.
4. `GET /repos/{o}/{r}/git/trees/{sha}?recursive=1` at the head and at the merge base. A truncated tree is refused.
   - Each file's head blob SHA must equal the tree entry; the file list SHA must agree.
   - Blobs come from `GET /git/blobs/{sha}` (base64).
   - The packager's existing `_blob` check recomputes `sha1("blob " + len + "\0" + bytes)` for every blob.
5. `patch.diff` is built in-process from the two blob sets (unchanged packager code). GitHub's `patch` field is never read.
6. The PR is read again. A different `head.sha` becomes `headShaAfterBuild`, and the packager refuses ("PR head moved").
7. Read-set files: blobs at head, verified the same way.

**Other refusals:**
- submodule changes (no blob to verify);
- file statuses other than added, modified, removed, renamed, copied and changed;
- a blob GitHub does not return as base64;
- a read-set file that is missing at head;
- a repository not given in `--allow-repo`.

**Token** (design §6):
- read from Windows Credential Manager, generic credential `company-os/review-packager`;
- sent only in `Authorization: Bearer`;
- any text that looks like a GitHub token is replaced by `<token>` in every error;
- 401/403 means "token invalid, revoked or lacking read access", with no fallback credential; a 403 with `x-ratelimit-remaining: 0` gets a rate-limit message;
- a `github-authentication-token-expiration` header under 14 days produces a warning.

**Task data** comes from `--task-file` in the `company-os/review-task@1` shape, `{issue, task}`, standing in for Paperclip until the relay phase.

## 2. Acceptance (§11 Phase 3) against the offline tests

| Condition | Offline evidence (fake GitHub) | Live evidence |
|---|---|---|
| Blob SHAs verified | `test_tampered_blob_refused_by_the_packager_sha_check`; `test_file_list_sha_differing_from_head_tree_refused` | **Met** for 7/7 files of PR #27 (§4) |
| Pagination complete | `test_reads_every_page_until_empty` (pages 2+2+1+empty); `test_incomplete_file_list_refused`; `test_too_many_pages_refused` | Partly: one page plus the empty page; count 7 = `changed_files` (§4). Several pages: offline only |
| Head-moved refused | `test_head_moved_is_recorded_and_refused_by_the_packager` | Not tested live (nothing pushed to the repository) |
| Missing-patch cases refused | See the note below; `test_missing_blob_content_refused`, `test_truncated_tree_refused`, `test_submodule_refused` | Not triggered live (complete tree and blobs) |
| Token never logged | `test_token_never_appears_in_errors`, `test_redact_catches_token_shapes`, `test_github_errors_become_redacted_refusals`, and the manifest and `REVIEW.md` checked in `test_end_to_end_package_records_github_source` | **Met**: not found in output, audit log, package, staging or the repository (§4) |

**Note on "missing-patch".**
- §4 step 5 says the `patch` field must never be the only source, because GitHub omits it for large files. The packager therefore ignores `patch` and builds the diff from blobs, so a missing `patch` field is **not** a reason to refuse.
- What is refused is missing **content**: a blob or tree GitHub does not return, or returns truncated.
- **Confirmed by the Board Operator (2026-11-20, in chat):** "missing-patch" means "missing the data needed to build the diff", not "missing the `patch` field".

**Not covered offline:**
- GitHub's real response shapes;
- fine-grained token permissions;
- forks;
- rate limits under load;
- the expiration header's exact format.

These need the live run.

## 3. Live-run checklist (needs the Board; nothing done yet)

**Board steps:**
1. **Create a throwaway repository**, private, owned by the Board Operator. It must not be a studio game or web repository.
2. **Create a pull request** in it that changes, adds, renames and deletes a few small text files. Optionally add a second commit after the first run, to test "head moved".
3. **Create a fine-grained personal access token** with:
   - "Only select repositories": that repository only;
   - Metadata: read; Contents: read; Pull requests: read; nothing else;
   - an expiry of at most 90 days.

   Record the expiry date in the operations runbook.
4. **Store the token** in Windows Credential Manager as a generic credential, target `company-os/review-packager`, entered by the Board Operator in their own terminal (for example `cmdkey /generic:company-os/review-packager /user:review-packager /pass`, which prompts for the value). **Never paste it into chat or a file.**

**Then the assistant runs**, with throwaway roots outside every repository and a `review-task@1` file for the test issue:

```text
python -I .claude/skills/paperclip/scripts/pc.py review-pack TEST-1 --github-pr <n> --github-repo <owner>/<repo> \
  --allow-repo <owner>/<repo> --task-file <task.json> --state-file <state.json> \
  --review-root <dir> --staging-root <dir>
```

**Live acceptance:**
- the package builds;
- every file's `gitBlobSha` matches GitHub;
- a pushed new commit during or before a re-run is refused as "head moved";
- the token appears in no output, no audit line, no package file and no shell history;
- revoking the token makes the next run refuse with the 401/403 message.

**After the run:** delete the throwaway roots. Keep or revoke the token, and keep or delete the throwaway repository, as the Board decides.

## 4. Live run (2026-11-20)

- **Authorization:** the Board Operator created a fine-grained token (Metadata, Contents and Pull requests read-only, `datpham02/soucean-game` only), stored it in Windows Credential Manager under `company-os/review-packager`, and asked for the run on that repository instead of a throwaway one.
- **Target:** PR #27 (SOU-28, open), the only open PR: 7 added files. The run is read-only: nothing pushed, no review requested, no Paperclip call. The task and state files were local stand-ins; roots were in a private folder outside every repository.
- **Command:** `pc.py review-pack SOU-28 --github-pr 27 --github-repo datpham02/soucean-game --allow-repo … --task-file … --state-file … --review-root … --staging-root …`.

**Results:**

| Check | Result |
|---|---|
| Build | Exit 0: "package built (7f22f059666b), staged". No warning; the token expiry is more than 14 days away |
| Head | Manifest `headSha` `7f22f059666b…` equals GitHub's PR head (independent check with the Board Operator's own `gh`, read-only) |
| Files | 7 in the manifest, 7 on GitHub (`changed_files` = 7) |
| Blob SHAs | 7/7: manifest blob SHA = GitHub file SHA = the SHA recomputed from the staged bytes; SHA-256 matches the manifest |
| Audit log | Two lines, `build` and `stage`, with no token |
| Token | Read in memory to search for it, never printed. Its exact value (UTF-8 and UTF-16) and the `github_pat_` prefix were found in **none** of the 30 files of the test folder (outputs, audit log, package, staging), nor in the repository |

**Not covered by this run:**
- several result pages (the PR has 7 files);
- a moved head (nothing was pushed);
- modified, renamed and deleted files (the PR adds files only);
- a truncated tree or missing blob;
- the 401/403 path. That needs the token revoked or replaced; it is the Board's choice.

These stay covered by the offline tests only.

**Left in place:** the private test folder (package and staging of SOU-28). It is to be deleted when the Board no longer needs it. The token stays stored; rotate or revoke per §6.

