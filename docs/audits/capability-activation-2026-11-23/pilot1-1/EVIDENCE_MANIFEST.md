# Pilot 1.1 — evidence manifest and provenance

**Logical evidence id:** `capability-audit-2026-11-23/pilot1-1`, run `2026-11-25`.

The underlying files are untracked local Runtime Data on the studio machine (ADR-010). This repository holds only the report, the sanitized protocol and this manifest. All hashes are sha256 of the original local files.

## Provenance

| Item | Source of truth | Observer |
|---|---|---|
| Quota | `claude -p` JSON results for both models | Operator session (Claude Code desktop, `claude-opus-5-5`) |
| Reads, tools, denials, turns, tokens, cost, word count | Each session's `stream-json` trace, extracted by the frozen pipeline | Script |
| Evidence-trail score | Frozen pipeline: listed sources compared with `Read` events | Script |
| Correctness, quality, completion, key items, false claims, arm guess | Blind scorer session output | Independent `claude-opus-5-5` session (not human, same provider family) |
| Unblinding and decision rule | Pipeline mapping plus the pre-registered thresholds | Operator script |
| Spot checks (2 scorer error calls) | Raw outputs | Operator; **not independent** |

## Frozen before the first run (2026-11-25 21:02:28 +07)

| Logical file | sha256 |
|---|---|
| Prompt A (= Pilot 1) | `3566dd75f0e65b263225cfc9c6ff0b7996a0e2ae8ac8df2e0a1f8ec3288a1640` |
| Prompt B (= Pilot 1) | `12302c4ba6e93745638d97e3bdb09390a41b0d80ee2f2666c5b5ae63a7993c76` |
| Router block (= Pilot 1) | `42bc1895109bab5db7e15016868b01cc741f79493d37f9fc17b4bfd8d6c3f6b7` |
| TASK (= Pilot 1) | `5832a1671bba11a313ef6debd3460481e8247eb96bb217c26d38f7808177d2eb` |
| Draft key | `3368eed44533822ab8e808c65a0d43423a3945703187d66c37f327c13cd3ba80` |
| Key-review prompt | `eb55441b49b657e160df9d9cc5d72923e2b1b86d774a36645f142c1111ca4577` |
| Key-review result | `9c43c4eb263591fc9ae0ede55b2526eebdbfbd2046b6143bc034860094c60c2f` |
| Frozen key | `603ab00dc3fc91395b6b494f1de8adb7f9840c760ecb5fc03d2de9e7ce22795d` |
| Blind key copy | `a0c86c6b53c4f01ca42a0278da629f3007a7484ad0f4c2fdadc8ecc9c0ff952e` |
| Seeded order | `1a13d60d8ca9eb6d22e8fde1806d1ee6eb9ef36947f9314121b4d894b3399ed7` |
| Scoring pipeline | `236448af923dd52df7b4d97a122ab9360ee4710b6ac890ef43085603c832f903` |
| Scorer prompt | `7bebeee46a816e5430b2fab349a889e6af4b6d45edc2f3312dd6614c3e9b7229` |

The V2 pack and the two studio knowledge files were checked against the Pilot 1 hashes ([../pilot1/EVIDENCE_MANIFEST.md](../pilot1/EVIDENCE_MANIFEST.md)), and all matched.

## Hash-timing caveat: scoring pipeline

The pipeline hash above was taken at the freeze. Before the freeze, the pipeline's evidence parser had already been patched to ignore "not opened" lines and given environment overrides for the dry run. The pipeline was **not edited after the freeze**.

## Outputs and records

| Logical file | sha256 |
|---|---|
| Preflight sonnet | `4d49e7e2d702f7804f2b8d75abe1a03e7acbfbaf2ecd572bdf7d5d7298e13c2e` |
| Preflight opus | `9724d0f6fbc1befd08482d5d4b0f301415840e5e614590308e12c683d0979d0a` |
| p1_A trace | `7ac79638b88ca8385c045f709f87fdf88fe38b20aece8e6df9c9c2ce23688033` |
| p1_B trace | `6e5886b17da753d6fb40ebeda9a85dafcad99e3fc544628678785cfa93755c69` |
| p2_A trace | `5992c68473e44ab3353e4fede837878594aa8c87cfe08072777227a179e4184e` |
| p2_B trace | `843b95924bc45bbc5c014bac91c62d77f7f01952e7706ff93c610cbce97b0d9f` |
| p3_A trace | `bd0ecb366f6788b33f3261086d0ea55b7a57cb2ca462f222e7680fcd5c7d7795` |
| p3_B trace | `201179a7849607d364918c824a4632de519c42ba4aa7b2d50399d3c9ee151cd0` |
| p4_A trace | `68495cb7868069613642911641c7767dff4085f5ad22d5e3237927a224a3ebb7` |
| p4_B trace | `06970e5d8ab6cb37bf43f0558c14b58a628a6fb96731e891cf65eb7f923103e9` |
| p5_A trace | `dc8e7d44d0df8e6675d2fe9dad4009705d633805426c6cd117ff80f99caf890b` |
| p5_B trace | `0d798fca02f2423ed74fc1bc7c4ec34f1237ca4fd561a813a6755e286ea59a18` |
| Run log | `60eb91273c561bb436aa5e0ca46e5462ba1ae959c11096e2d9c9fff98535413d` |
| Key-review trace | `624e5294aa8bf843b73411507bd9619aa2b7b524949bbad6a8474e4889a1fc9a` |
| Scorer trace | `e82be85d39fc12e45687fcfe8fb6f376a1d0c07347f69855ebc3c197eb931329` |
| Scorer result | `47e7212ee0790346ce749ead1fb81f844ff25119cd985f73854a7a731761dd9c` |
| Extracted metrics | `0d0bb0ad9b8a272991edc232b0c5fff46af8fa18c7df8613875fe9559ddb624d` |
| Evidence-trail scores | `3dddf10367f8eb817e56ff2fbd5ac1d0e73e5bf7348baded4ed31614ffa8bc7e` |
| Output-to-arm mapping | `4494dc1acaf03d69c8712c6d844027f2147656e9e10fe205c37a8f3d8728e6c0` |
| Unblinded results | `91c1caefc4fef9419328620b7d0a0b3f749eb7a4f8efea1c1e82f96c4c398e19` |
| Local report | `84369212852b58045ad32abfd5af428672a48a9c5764311722ca5cd51c226770` |

## Kept out of the repository

- **Raw traces, raw and anonymized outputs, the full key text, and scorer rationales.** They contain machine paths, session ids or verbatim V2 R&D content.
- **The V2 pack itself.**

## Not measured or not available

- **Blinding.** It was effectively absent: the scorer guessed the arm correctly for 10/10 outputs.
- **Inter-rater reliability.** There was one scorer, so it is not measured.
- **Human judgement.** None; the Board's optional spot-check was not used.
- **Billing-grade cost.** CLI `total_cost_usd` is a list-price figure, not a billing record.
- **Separate thinking tokens.** Not reported.
- **Generalization.** No evidence beyond one task type.
