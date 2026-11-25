# Pilot 1 — evidence manifest and provenance

**Logical evidence id:** `capability-audit-2026-11-23/pilot1`, run `2026-11-25`.

The external evidence is held as untracked local Runtime Data on the studio machine (ADR-010). This repository holds only this manifest, the sanitized protocol and the report. All hashes are sha256 of the original local files.

## Provenance

| Item | Source of truth | Who observed it |
|---|---|---|
| Quota preflight | `claude -p` JSON result: `QUOTA_OK`, `is_error=false`, `terminal_reason=completed`, model `claude-sonnet-5-5`, 2026-11-25 19:48 +07 | Operator session (Claude Code desktop, `claude-opus-5-5`) |
| Reads, invocations, denials, turns, tokens, cost | Each arm's `--output-format stream-json --verbose` log (`tool_use` events and the final `result` event) | Extracted by the operator script from the logs |
| Findings | Each arm's final `result` text, preserved verbatim locally | Operator |
| Ground-truth checks | The operator read every V2 pack file and both knowledge files | Operator, **not independent** |
| Scores | Operator, against anchors written before outputs were opened | Operator, **not blind** |

## Hashes

### Frozen inputs (hashed before the runs)

| Logical file | sha256 |
|---|---|
| pilot1 `TASK.md` | `5832a1671bba11a313ef6debd3460481e8247eb96bb217c26d38f7808177d2eb` |
| `PROMPT_A.txt` | `3566dd75f0e65b263225cfc9c6ff0b7996a0e2ae8ac8df2e0a1f8ec3288a1640` |
| `PROMPT_B.txt` | `12302c4ba6e93745638d97e3bdb09390a41b0d80ee2f2666c5b5ae63a7993c76` |
| Router block, markdown | `42bc1895109bab5db7e15016868b01cc741f79493d37f9fc17b4bfd8d6c3f6b7` |
| Router block, json | `ccc2227d3a3d889ac1edf4f2d86360ec5fb8a7e650ccfe524a6af276b250e623` |
| V2 `00_CLEAN_SLATE.md` | `97874d01c3e26d2765d0edc2c4fe3f8c3062b0754192a0cde67d8be90185a90f` |
| V2 `Sealwarden_Character_Design_Spec.md` | `574e59fedf11988e87dcd9429fe333a50125d4a254272b1a1cc4e8e95b42e50a` |
| V2 `Sealwarden_Layered_Part_Plan_v2.md` | `32d84d396f12ec7cb57999f4804ad44857ba089b01300c050e4fcf37c4a3f249` |
| V2 `Master_to_Parts_Strategy.md` | `3f761e6a8d135d50ed2eaf02355fb3a5c8edb0ef0d424b5f6a86304531d426aa` |
| V2 `V2-Master-1_Proposal.md` | `ee6ec7982e32e028297cb96100a8a369d4a03d8719e96252c74c6c04fdb48337` |
| V2 `prompt.txt` (equals the proposal's recorded hash) | `0c5aa76094efc40f758928ac1aeb4205e68aba4bfd2f91dadbc794273251c411` |
| `knowledge/departments/game/skills/studio-art-identity-and-refinement/SKILL.md` @ `bf6076c` | `a1152f6183741bf38862deeb7dc49376073fa8d21ef48258b1e336d07768e84e` |
| `knowledge/departments/game/workflows/asset-production.md` @ `bf6076c` | `364d8b65daaf62feec2f3e7ec2d99f2730111b38789bd321c116819920899d37` |

### Outputs and records

| Logical file | sha256 |
|---|---|
| Preflight JSON result | `5375ffaed0ad32c2d6803e32a332fd03ca28db437396de3a14f832e3044e7dc0` |
| Arm A stream-json trace | `b59dddcfcc3d50eb993fc967a3eb2632622a9c8b6e6a33aac513c65ea39f7ab2` |
| Arm B stream-json trace | `07706908a03f2bfd47774638ecf958d916308dfb21c326f6ba8e9245737bb454` |
| Arm A raw output | `5e859dff6695495bc2bf1f798568ba64514c8df27b2752f73c66742e7d55de0f` |
| Arm B raw output | `d241bcd07cea75ae6f994a0ca6225365b40dd602098481b541e4165d08793ab9` |
| Scoring anchors (pre-output) | `79705fe0f76c71dee731792ed36bb4049c095ea910ed838ac5c770150ff67eb7` |
| Local comparison / score sheet | `df394a8ad1390a5d57642b61ba8c326094d3f6212636cfd327a42a78b66db2cd` |

**Hash timing:** the anchors file was written before outputs were opened. Its hash was computed afterwards, and there is no third-party timestamp. The local comparison file received one arithmetic correction (cache-token delta 18 → 29,954) before the Issue #113 comment was posted. No score changed.

## Kept out of the repository

- **Raw traces and raw outputs.** They contain machine paths, session ids and verbatim V2 R&D content.
- **The V2 pack itself.** It is R&D material outside company-os and is not copied here.
- **The 2026-11-23 prepared prompt set and the failed rate-limit capture.** These are superseded or historical, and remain local.

## Not measured or not available

- **Model variance:** n = 1 per arm.
- **Inter-rater reliability:** one scorer.
- **Blind scoring:** not done. Arm B's output necessarily cites the router block.
- **Latency comparability:** the arms ran concurrently on one machine, so wall time is indicative only.
- **Cost basis:** `total_cost_usd` is the CLI's list-price figure, not a billing record.
- **Thinking tokens:** not reported separately in the result event.
