"""Writes the entity-motion-profile definition and the example entities (Board amendment 2026-11-22)."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(HERE, "examples"), exist_ok=True)

schema = {
    "schema": "entity-motion-profile.v1 (definition)", "status": "PROPOSED",
    "principle": "composition, not inheritance: an entity lists motion components; knowledge profiles (anatomy, materials, "
                 "fictional rules) are parameters of components. Only id, components and validation are required.",
    "fields": {
        "id": "unique id",
        "identity": {"name": "", "role": "player|enemy|npc|prop|environment|effect", "movement_identity": "one sentence: how it should feel"},
        "topology": "skeletal | segmented chain | rigid parts | deformable | particle/field | hybrid",
        "anatomy": "optional anatomy profile (profiles/*.json) for biological skeletal components",
        "proportions": {}, "mass": {"total": "relative", "distribution": "per component/segment"},
        "materials": {"<part>": {"elasticity": 0, "damping": 0, "friction": 0, "rigid": True}},
        "components": [{"type": "<registry id>", "name": "<instance>", "params": {}, "attach_to": "<component.socket>"}],
        "locomotion_modes": ["walk", "run", "fly", "swim", "slither", "hover", "roll", "teleport"],
        "contacts": {"<name>": {"component": "", "point": "", "expected": "always|phase|never"}},
        "attachments": {"<socket>": {"component": "", "transform": [0, 0, 0]}},
        "collision": {"approx": "capsules|polygons|circles"},
        "environment_interactions": ["ground", "water", "wind", "walls"],
        "interactions": [{"type": "attach|driven_by|grab|throw|collide|transform", "a": "", "b": "", "events": []}],
        "references": [{"kind": "mocap|video|anatomy|art|analogue", "source": "", "licence": "", "use": "timing|arcs|gait|pose"}],
        "artistic": {"weight_feel": "", "stylisation": "", "readability": "", "telegraph": ""},
        "gameplay": {"events": [], "hitboxes": "", "timing_budgets": {}},
        "methods_allowed": ["fk_keyframe", "mocap_retarget", "procedural", "physics", "shader", "engine particles", "frame-by-frame (generated)"],
        "fictional_rules": [{"id": "", "rule": "", "overrides": "<validator id> -> expected behaviour"}],
        "validation": {"physical": "validators that apply", "fictional": "validators replaced by fictional rules", "artistic": "review items"},
    },
}
json.dump(schema, open(os.path.join(HERE, "entity-motion-profile.schema.json"), "w"), indent=1)

ex = {
    "brute_hammer": {
        "id": "brute_hammer",
        "identity": {"name": "Attacker (Deckbound benchmark)", "role": "enemy", "movement_identity": "slow, heavy, committed blows; head low between the shoulders"},
        "topology": "skeletal + rigid attachment", "anatomy": "../../profiles/heavy_humanoid.json",
        "components": [{"type": "articulated_skeleton", "name": "body", "params": {"structure": "../../data/structure_brute_hammer.json", "limit_tier": "stylized"}},
                       {"type": "rigid_attachment", "name": "hammer", "params": {"asset": "hammer_master", "grip": "body.hand_f"}},
                       {"type": "flexible_appendage", "name": "loincloth", "params": {"stiffness": "low", "driver": "body.pelvis"}}],
        "locomotion_modes": ["walk"], "contacts": {"feet": {"component": "body", "expected": "always (attacks)"}},
        "references": [{"kind": "mocap", "source": "CMU 79_01 chopping wood", "licence": "CMU: free for all uses, no resale", "use": "body timing, coil, weight"}],
        "artistic": {"weight_feel": "heavy (mass_scale 1.4)", "telegraph": "wind-up readable at 270 px"},
        "gameplay": {"events": ["impact"], "timing_budgets": {"windup_min_ms": 340}},
        "validation": {"physical": "skeletal + attachment validators", "fictional": [], "artistic": "director on previews"}},
    "dragon": {
        "id": "dragon",
        "identity": {"role": "boss", "movement_identity": "reptilian weight on the ground, bat-like wings, whip tail, fire breath"},
        "topology": "hybrid", "anatomy": "../../profiles/quadruped.json",
        "components": [{"type": "articulated_skeleton", "name": "body", "params": {"anatomy": "quadruped"}},
                       {"type": "legged_gait", "name": "walk", "params": {"pattern": "lateral-sequence walk", "duty": 0.7}},
                       {"type": "wing", "name": "wings", "params": {"membrane": "bat-like", "fold_coupling": True}, "attach_to": "body.scapula"},
                       {"type": "undulating_body", "name": "tail_wave", "params": {"mode": "lateral"}, "attach_to": "body.pelvis"},
                       {"type": "flexible_appendage", "name": "tail_tip", "attach_to": "tail_wave.end"},
                       {"type": "rigid_attachment", "name": "armor_plates", "params": {"parent": "body.spine"}},
                       {"type": "particle_emission", "name": "fire_breath", "attach_to": "body.jaw", "params": {"event": "breath_start..breath_end"}}],
        "locomotion_modes": ["walk", "fly", "glide"],
        "fictional_rules": [{"id": "lift", "rule": "wings lift the body despite its mass (fantasy)", "overrides": "no physical lift/mass check"}],
        "validation": {"physical": "per component", "fictional": ["lift"], "artistic": "reads as one creature, not parts"}},
    "slime": {
        "id": "slime", "identity": {"role": "enemy", "movement_identity": "bouncy, wobbling, sticky"}, "topology": "deformable",
        "components": [{"type": "deformable_body", "name": "body", "params": {"elasticity": 0.8, "damping": 0.3, "volume_preservation": 0.9}},
                       {"type": "ballistic", "name": "hop"}, {"type": "shader_deformation", "name": "surface_wobble"}],
        "locomotion_modes": ["hop", "slide"], "contacts": {"base": {"component": "body", "expected": "phase (between hops)"}},
        "validation": {"physical": ["triangle_flip", "area_preservation", "recovery_time", "parabola_fit"]}},
    "ghost": {
        "id": "ghost", "identity": {"role": "enemy", "movement_identity": "drifting, weightless, fading"}, "topology": "deformable + field",
        "components": [{"type": "hover_float", "name": "drift", "params": {"bob_period_s": 2.4}},
                       {"type": "cloth", "name": "shroud_tail", "params": {"pins": "head"}},
                       {"type": "shader_deformation", "name": "wobble"}, {"type": "particle_emission", "name": "wisps"}],
        "contacts": {"ground": {"expected": "never"}},
        "fictional_rules": [{"id": "no_gravity", "rule": "ignores gravity and ground contact", "overrides": "ground_contact, balance -> not applied"},
                            {"id": "phasing", "rule": "may pass through walls", "overrides": "collision -> not applied"}],
        "validation": {"fictional": ["no_gravity", "phasing"], "physical": ["loop_seam", "pins"], "artistic": "readable silhouette, consistent drift"}},
    "golem": {
        "id": "golem", "identity": {"role": "enemy", "movement_identity": "rigid stone blocks, enormous mass, grinding joints"}, "topology": "rigid parts",
        "components": [{"type": "articulated_skeleton", "name": "body", "params": {"joint_spec": "mechanical (no soft tissue), stiff limits"}},
                       {"type": "hinge_linkage", "name": "plates"}, {"type": "particle_emission", "name": "dust_on_step"}],
        "artistic": {"weight_feel": "exaggerated mass: long anticipation, ground shake on contact"},
        "validation": {"physical": ["pivot", "intersection", "ground_contact"], "artistic": "mass reads"}},
    "giant_spider": {
        "id": "giant_spider", "identity": {"role": "enemy", "movement_identity": "fast skittering, eight legs in an alternating tetrapod gait"},
        "topology": "skeletal (8 legs)", "anatomy": "../../profiles/multi_limbed.json",
        "components": [{"type": "articulated_skeleton", "name": "body", "params": {"legs": 8, "segments": ["coxa", "femur", "tibia", "tarsus"]}},
                       {"type": "legged_gait", "name": "skitter", "params": {"pattern": "alternating tetrapod"}}],
        "validation": {"physical": ["support_polygon", "gait_sequence", "limb_intersection", "ground_contact"]}},
    "lantern_interaction": {
        "id": "lantern_interaction", "identity": {"role": "prop interaction", "movement_identity": "a lantern swings from the carrier's hand"},
        "topology": "interaction",
        "components": [{"type": "rigid_attachment", "name": "hook", "params": {"parent": "carrier.hand_b"}},
                       {"type": "pendulum", "name": "lantern", "attach_to": "hook.end", "params": {"length_px": 110, "damping": 0.12}},
                       {"type": "particle_emission", "name": "flame", "attach_to": "lantern.wick"}],
        "interactions": [{"type": "attach", "a": "carrier.hand_b", "b": "hook", "events": ["pickup", "drop"]},
                         {"type": "driven_by", "a": "lantern", "b": "carrier.chest", "note": "pendulum driven by the carrier's acceleration"}],
        "validation": {"physical": ["attachment", "settle_time", "socket_attachment"]}},
}
for k, v in ex.items():
    json.dump(v, open(os.path.join(HERE, "examples", f"{k}.json"), "w"), indent=1)
print(sorted(ex))
