# 5. Duplicate / Overlapping Capability Analysis

| Cluster | Members | Overlap | Recommendation |
|---|---|---|---|
| Company roles vs Claude-Code-Game-Studios | Company OS agents/skills vs CCGS 49 agents / 74 skills (candidate) | Full second studio template | **Defer / Evaluate only as harvest-source**, never as parallel root |
| Gamedev skills | awesome-gamedev-agent-skills vs Company game workflows vs REA | Engine howto duplication | Evaluate **Godot subset only**; keep Company workflows canonical |
| Design systems | ui-ux-pro-max (integrated), google-design-md, awesome-design-md, open-design, taste, hallmark, emil-design-eng, impeccable(**rejected**) | Competing “taste” packs | Keep ui-ux-pro-max + google-design-md; evaluate ≤1 more; **impeccable stays BLOCKED** |
| Web motion/UI kits | react-bits, gsap-skills, scroll-world, canvas-ui | Front-end sugar overlap | Pick per project need after web-engineer unpause; don’t bulk-activate |
| Cutout / matte | art-ops key vs BiRefNet matte vs ToonOut (evaluating) | Same job | Production: BiRefNet; key for flat BG; ToonOut defer |
| Inpaint stacks | Production SDXL inpaint vs Fooocus patch / comfyui-inpaint-nodes (R&D) vs failed pose repair spikes | Confusing “more nodes = better pose” | Keep production wrappers; R&D evaluate offline only |
| Image gen hosts | `comfyui` (production) vs `comfyui-rnd` vs unregistered operator MCPs | Host confusion | Strict Agent → production wrappers only |
| Orchestration | Paperclip vs Cursor Automations/skills vs personal synced Claude skills | Three control planes | Paperclip = company; Cursor/Claude user skills = operator; don’t merge |
| Spec tools | OpenSpec candidate vs Company task-contract / OpenSpec docs | Spec authority | Decide install-or-drop; until then task-contract wins |
| Pixel FX | pixelfx library vs hand-authored Godot/VFX | Effect source | Activate pixelfx on VFX tasks only; Lamplight license caution in registry notes |
| Animation | S2 Godot skinned JSON vs crop-from-flat construction vs K5 deferred skill | Competing animation stories | One pipeline: articulation-first + Godot; retire cut-paste narrative |

Principle: **reuse Company OS + integrated tools**; candidate packs are ingredient sources after evaluation, not drop-in replacements.
