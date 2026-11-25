# Pilot 1.1 — protocol as executed (sanitized)

**Approved design:** [Issue #113 comment 7164331179](https://github.com/datpham02/company-os/issues/113#issuecomment-7164331179)  
**Logical evidence id:** `capability-audit-2026-11-23/pilot1-1`, run `2026-11-25`  
**Placeholders (ADR-010):**
- `<pilot1>`: the local Pilot 1 task folder
- `<v2-pack>`: the Sealwarden V2 R&D folder
- `<company-os>`: the local checkout
- `<run>`: the local Pilot 1.1 run folder

## 1. Arms (unchanged from Pilot 1)

The task text, prompt A, prompt B and router block are **byte-identical** to Pilot 1. See [../pilot1/PROTOCOL.md](../pilot1/PROTOCOL.md) for the sanitized texts. The sha256 values are listed in [EVIDENCE_MANIFEST.md](EVIDENCE_MANIFEST.md).

| Control | As executed |
|---|---|
| Model / effort | `claude-sonnet-5-5` / `medium`, both arms |
| Tools | `Read, Glob, Grep`; `--strict-mcp-config` (0 MCP); `--disable-slash-commands`; `--max-budget-usd 0.50` per session |
| Directory access | Identical `--add-dir` set for both arms: `<pilot1>`, `<v2-pack>`, `<company-os>` |
| Isolation | Each session ran in a fresh, empty working directory. Outputs were written outside every readable directory. Older Pilot 1 prep files were moved out of `<pilot1>` during the runs, so only `TASK.md` was readable there, and were restored afterwards. |
| Order | 5 pairs run sequentially. The within-pair order came from `random.seed(20261125)`: AB, BA, BA, AB, AB. |
| Stop rules | Any non-completed result, any prohibited action, a missing input, or a cumulative run cost of US$3.50 or more. None fired. |

## 2. Freeze sequence

1. Preflight `QUOTA_OK` for both models.
2. Operator draft key: 14 items written from the source documents.
3. Independent key review. A fresh `claude-opus-5-5` session read the sources, the two studio knowledge files and the draft key. It never saw an output. It verified 13 items, marked K05's wording as wrong, and proposed 14 items and 7 false-claim patterns.
4. Operator merge, before any run:
   - K05 reworded.
   - 13 items added.
   - One proposed "recommended next step" item folded into K01.
   - One added item (the three-list gap) overridden to non-router-attributable, because TASK asks both arms for the lists.
5. A blind copy of the key was made. It drops the router-attributable flags and the review notes, and rewords X06 so it does not mention the router.
6. Key, blind key, order, scoring pipeline and scorer prompt hashed at 2026-11-25 21:02:28 +07.
7. Runs.

## 3. Ground-truth key (summary)

Each item has a redacted label, not V2 content. "R" marks a router-attributable item: one that needs `SKILL.md` or `asset-production.md` to find.

| ID | R | Item |
|---|---|---|
| K01 | | Generation must stay blocked (proposal not run; Board approval required) |
| K02 | R | Proposed master stack (FLUX.2 klein on R&D ComfyUI) not available to `game-artist`; R&D lane only |
| K03 | R | Project licensing rule for AI-made art is a precondition and is not stated in the pack |
| K04 | | Part plan claims 22 rest textures; its table lists 19 |
| K05 | | Pixel thresholds lack a reference resolution or an explicit 270 px conversion |
| K06 | | Spec relies on a turnaround that is never planned |
| K07 | | CFG 1.0 with an empty negative leaves the negation clauses weakly enforced |
| K08 | | The Defect quality-bar reference has no location |
| K09 | | ±45° spec requirement vs the ±35°/±50° Gate C test set |
| K10 | | "Seal fully visible" vs fists and mallet in front of the torso; the acceptance check is weaker than the requirement |
| K11 | | Palette authority: spec hex tokens vs palette sampled from the master |
| K12 | | ReferenceLatent on isolated parts is untested |
| K13 | | Master acceptance does not measure the spec's proportions or palette; the prompt omits spec details |
| K14 | | Identity invariants (spec §6, repeated as Gate B) |
| K15 | | No explicit pose-specific or replaceable-representation lists in the pack |
| K16 | | Gate separation A/B/C/D is sound (positive finding) |
| K17 | | Attack beat lists disagree: 4 beats vs 5 |
| K18 | | Corrective allowance: 1 in the spec vs ≤3 in the plan |
| K19 | | Rest draw order puts the back hand under the apron and mallet |
| K20 | | Seal ambiguous as a part ("if separate") |
| K21 | | "Master-derived reconstruction" wording sits close to the crop-from-flat ban |
| K22 | | Clean-slate lineages named without paths; historical evidence vs conditioning |
| K23 | | Pad requirement covers only limb parts; parent plates are unchecked |
| K24 | | Prompt relies on undefined proper nouns |
| K25 | | Prompt hash cannot be checked by reading; report it UNVERIFIED |
| K26 | R | Studio tool and approval path (registry entry, review, Board approval; approved equivalents; known SDXL inpaint limit) |
| K27 | R | Studio brief expects 3–5 reference traits and per-seed keep/reject evidence |

**False or unsupported claim patterns X01–X13.** Each is listed with its severity:

| ID | Pattern | Severity |
|---|---|---|
| X01 | Graph JSON claimed missing | minor |
| X02 | Accepts "22" | minor |
| X03 | Generation approved, or "ready for gen review" | major |
| X04 | Misattributes a studio rule | minor |
| X05 | Claims the hash was verified | minor |
| X06 | Preview or status treated as permission | major |
| X07 | Hash or graph file claimed absent | minor |
| X08 | ReferenceLatent claimed forbidden outright | minor |
| X09 | Knowledge reuse claimed forbidden | minor |
| X10 | Production server or out-of-folder writes claimed | major |
| X11 | AI final art claimed forbidden | major |
| X12 | Gate A claimed to need full invariants, or gates claimed unseparated | major |
| X13 | First master claimed to use an image input | minor |

## 4. Scoring

**Mechanical evidence trail.** The pipeline compares the file names listed in an answer's "Sources consulted" section with the actual `Read` events in its trace:

| Score | Rule |
|---|---|
| 2 | Listed set equals read set (TASK.md excluded) |
| 1 | Files read but not listed, or no Sources section |
| 0 | Files listed with no Read event |

A line that says a file was *not* opened is ignored. Before the freeze, the pipeline was dry-run on the Pilot 1 traces and reproduced the Pilot 1 manual evidence scores (2 and 2).

**Anonymization.**
- Outputs were shuffled (seed 1125) and renamed O01–O10.
- The "Session meta" appendix was removed.
- Company OS paths and file names, `company os`, `capability block`, `read-set`, `ccgs`, router status tokens and `router` were replaced with bracketed tokens.
- The original word count was kept in a header comment.
- The output-to-arm mapping stayed in a file outside the scorer's readable directories.

**Blind scorer.** A fresh `claude-opus-5-5` session, effort `medium`, `Read/Glob/Grep`, `--max-budget-usd 3.00`.
- Readable inputs: `<pilot1>` (task), `<v2-pack>`, the two studio knowledge directories, the anonymized outputs and the blind key.
- It scored correctness, quality and completion on the Board's 0/1/2 anchors, the same as Pilot 1. It also listed key items found, false claims, and an arm guess with a confidence value.
- Its only Glob ran over `<v2-pack>`. It never accessed the mapping.

**Decision rule (pre-registered; quoted from the design).**
- **ACTIVATE (eligible to propose)** requires all of: primary B − A ≥ +0.5; B mean key recall ≥ A; B errors per run ≤ A + 0.5; router-attributable hits in ≥ 4/5 B runs; 0 prohibited actions and 0 preview-as-permission.
- **REVISE:** hits ≥ 4/5, but B regresses on recall or errors, or treats preview or status as permission.
- **NO BENEFIT SHOWN:** |primary difference| < 0.5 and hits ≤ 2/5.
- **BLOCKED:** a stop rule fired before all 5 pairs completed.
- **INCONCLUSIVE:** anything else.
