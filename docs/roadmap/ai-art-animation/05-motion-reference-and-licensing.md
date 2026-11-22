# Motion reference for 2D animation: sources, tools and commercial licensing

> **Verification (Board operator, 2026-11-22, in-app browser, http://mocap.cs.cmu.edu/):** the CMU home page says the dataset is "free for all uses"; it may be included in commercially sold products, but the data itself may not be resold directly, even in converted form; crawling the site is not allowed. Subject 79 trial 1 is listed as "chopping wood" at 60 fps with ASF/AMC files. The research-agent wording below that came from a GitHub mirror is superseded by this check. Nothing has been downloaded yet (needs Board approval).
> **Status:** `PROPOSED`, research compiled by a Claude Code research agent for the Board; all text is the studio's own summary with source links.


Researched 2026-11-22 for a small studio that ships 2D games made by AI agents. Constraints: one Windows 11 PC (RTX 3060 12 GB, 16 GB RAM); agents have no web access; the Board approves every new dependency and every download; the Board will **not** record motion.

Method: I only read web pages. I downloaded nothing and created no accounts. This is not legal advice. Anything marked "unknown" needs a person to read the full terms, or legal review.

## 0. Fetch log (which pages I read, and which failed)

| Requested page | Result |
|---|---|
| https://www.mixamo.com/ | Fetched, but the page is a JS shell ("Loading Mixamo") with no terms text. |
| https://helpx.adobe.com/creative-cloud/faq/mixamo-faq.html | **Failed: HTTP 403.** The `/au/` regional copy also returned 403. Fallbacks used: the Adobe community thread "Mixamo FAQ - Licensing, Royalties, Ownership, EULA and TOS" (2022), the Adobe General Terms (https://www.adobe.com/legal/terms.html), and search-result snippets of the helpx FAQ. |
| https://mocap.cs.cmu.edu/ (also faqs.php) | **Failed: TLS error "unable to verify the first certificate".** web.archive.org is blocked for this tool. I did not bypass the TLS check. Fallback: CMU's licence statement as quoted verbatim in `READMEFIRST.txt` of github.com/una-dinosauria/cmu-mocap (a BVH conversion), plus the clip index in the same repo and the KIT Motion Database mirror (motion-database.humanoids.kit.edu). **Before the Board relies on it, a person should read the wording on mocap.cs.cmu.edu in a browser.** |
| https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker | Fetched. The page itself states no licence, so licences were read from the GitHub repo, the HF model card and PyPI. |
| https://docs.blender.org/manual/en/latest/files/import_export/bvh.html | Fetched, but only the navigation text came through (about 216k characters, no BVH section in the parts I read). The add-on page URL returned 404, and blender.org licence pages returned 403. Blender licence facts come from search snippets of blender.org pages (manual "About Free Software and the GPL", FAQ, copyright.txt). |
| Rokoko /legal/terms-of-service, DeepMotion /terms-of-service | 404. Used https://www.rokoko.com/studio-term-of-use and https://deepmotion.com/faq instead. |
| opengameart.org (UAL2) | 403. Used quaternius.com instead. |

## 1. Licence table

Column key: **Commercial** = may the motion end up in a shipped, sold game. **Redistrib.** = may the raw files (BVH/FBX/weights) be shared or placed in a public repo or build.

| Source / tool | Type | Commercial use in shipped game | Redistrib. of raw data | Attribution | Account / login | HW fit (3060 12 GB, 16 GB RAM) | Risk notes | Licence text actually read |
|---|---|---|---|---|---|---|---|---|
| **CMU Graphics Lab Mocap DB** (2,600+ trials, ASF/AMC, C3D; community BVH) | dataset | **Yes.** CMU quote: "This data is free for use in research and commercial projects worldwide." Search snippets of CMU/UPenn mirrors add that it may go into commercially sold products but **may not be resold directly**, even in converted form. | Not as a standalone resale product. Shipping baked derived animation is fine. | Requested only for publications ("The data used in this project was obtained from mocap.cs.cmu.edu" + NSF EIA-0196217). Crediting it anyway is cheap and recommended. | None | Trivial (text files) | Official page unreadable from here (TLS). Some derivatives are **re-licensed** (for example the 4TU FBX conversion is CC BY-NC 4.0), so use the original or Bruce Hahne's BVH ("I (Bruce) place no additional restrictions"). Old optical mocap with some jitter and missing props. | READMEFIRST.txt in github.com/una-dinosauria/cmu-mocap (quotes CMU) |
| **Mixamo** (Adobe) | service + animation library | **Yes, royalty-free.** The helpx FAQ snippet lists video games. The 2022 community FAQ says "unlimited commercial or non commercial use". | **No.** Raw character/animation files may not be distributed (no asset packs, store sales or free redistribution). Sharing inside a project team is OK. | Optional | **Adobe ID required.** Enterprise/Federated IDs not supported (per the FAQ snippet). | Web service | Adobe General Terms §6.6 forbid access "by any means other than the interface we provide" (so no scripted or agent downloads), §6.18 bans scraping, §5.1/§3.1 ban account sharing, and §17(C) bans using outputs to train ML models. Agents have no web access anyway, so a **human must download** and hand files over. The official FAQ page itself was 403. | adobe.com/legal/terms.html; Adobe community Mixamo FAQ thread |
| **Bandai Namco Research Motion Dataset 1 & 2** (BVH) | dataset | **No.** CC BY-NC 4.0 | NC only | Required | None (GitHub) | Trivial | Has "slash", "kick", "punch" in 15 styles, but non-commercial. Blender scripts in the repo are MIT. | GitHub repo + Dataset-1/LICENSE |
| **Ubisoft LaFAN1** | dataset | **No.** CC BY-NC-ND 4.0 | No (ND + NC) | Required | None | Trivial | Fight and locomotion only. Non-commercial, no derivatives shared. | ubisoft-laforge-animation-dataset/license.txt |
| **AMASS** | dataset (SMPL params) | **No.** "any use for commercial purposes, is prohibited". Commercial licence possible via ps-license@tue.mpg.de. | No | Required | Registration on MPI site | OK | Also needs SMPL (non-commercial). | amass.is.tue.mpg.de/license.html |
| **Human3.6M** | dataset | **No.** Free licences "limited to academic use only" | No | Cite | Academic e-mail request | — | Commercial licence only by negotiation. | vision.imar.ro/human3.6m/eula.php |
| **SMPL body model** (needed by 4D-Humans, WHAM, AMASS) | model | **No.** Non-commercial; commercial via Meshcapade | No | — | Registration | — | Makes all SMPL-based video-to-3D tools unusable for production without a paid licence. | smpl.is.tue.mpg.de/modellicense.html |
| **Truebones** free mocap packs | dataset (BVH/FBX) | **Conditional / unclear.** Store listing claims royalty-free "for any and all purposes even commercial". A separate "Terms of Service and Use Restrictions" doc exists that I did not read. | Unknown (probably not) | Unknown | Gumroad checkout (account or e-mail) | Trivial | Only search snippets read. A "Creative Commons Mocap Pak" does not say which CC licence. | Not read directly (search snippets of truebones.gumroad.com) |
| **Rokoko Motion Library** (free moves) / **Rokoko Vision** (video-to-mocap) | asset library + service | **Conditional.** Marketing says export and use "in any of your projects, including commercial ones". Studio ToU §5.3 allows integrating assets into productions. | **No.** §5.3: "may not reproduce, distribute, sublicense…" unless an asset's own licence allows it. | Per asset | **Account required** (§2.1). The licence is tied to holding an account (§5.1). Free fight-pack download needs a form with name and e-mail. | Web service; Vision free tier about 30 s/month | §4.4 bans access "through any automated means". §5.4 bans using assets to train AI/ML. §6.3 gives Rokoko a perpetual licence to user uploads. Vision needs our own video, which the Board will not record. | rokoko.com/studio-term-of-use |
| **DeepMotion Animate 3D** | service (video-to-3D) | **Paid plans only.** FAQ: Freemium is "for personal, non-commercial use". "Commercial License" is a paid-tier feature. | Third-party review says no standalone resale (not verified) | — | Account required | Cloud | Needs input video (none allowed). API only by sales contact. Full ToS URL 404. | deepmotion.com/faq |
| **Quaternius Universal Animation Library 1 / 2** | animation pack (FBX/GLB, Blend in paid "Source") | **Yes.** CC0 | Yes (CC0) | None | None for the free tier (site / itch.io) | Trivial | UAL2 has "melee and armed combos" (3- and 4-hit combos), but no clip names are published. No hammer-smash clip could be confirmed. Clean game-style keyframes on a universal humanoid rig. | quaternius.com/packs/universalanimationlibrary(2).html |
| **Kenney** Animated Characters | asset pack | **Yes.** CC0 | Yes | None | None | Trivial | Very few, generic clips. No heavy melee. | kenney.nl/assets/animated-characters-1 |
| **Paid packs** (Unity/Fab "2Handed Hammer AnimSet", "Heavy Hammer Animation", MoCap Online) | asset packs | Per-store EULA (usually yes, inside a built game; MoCap Online standard caps at 1M users/$1M per search snippet) | Usually no | — | Store account + purchase | — | Purchase needs Board approval. Store EULAs not read. | Not read |
| **MediaPipe Pose Landmarker** (`mediapipe` on PyPI) | library + model | **Yes.** Library Apache-2.0. Model files on HF `litert-community/MediaPipe-PoseLandmarker-*` show `apache-2.0`. | Yes (Apache, keep NOTICE) | Apache notice | None | CPU real-time. GPU delegate optional. `mediapipe 1.2.3` (2026-11-11) ships a `win_amd64` wheel, Python 3.9–3.14. | Model card: single person, Z relative "up to scale", surveillance out of scope. 33 landmarks plus world landmarks in metres. **Needs a video source, which we do not have.** | github.com/google-ai-edge/mediapipe; HF model card; pypi.org/project/mediapipe |
| **MMPose / RTMPose** (+ `rtmlib`) | library + models | **Code: yes** (Apache-2.0; EDPose head is IDEA License 1.0, so avoid it). **Weights: conditional.** rtmlib says weights trained on non-commercial datasets (e.g. COCO-WholeBody, and RTMW3D is "trained on COCO-Wholebody") need a dataset-licence check. | Code yes. Weights unclear. | Apache notice | None | rtmlib runs CPU (onnxruntime) or CUDA. Fine. | Weights inherit training-data licences (AIC, CrowdPose, Halpe, …). Needs legal review. | mmpose README + LICENSES.md; rtmlib README |
| **OpenPose** (CMU) | library + models | **No.** "ACADEMIC OR NON-PROFIT ORGANIZATION NONCOMMERCIAL RESEARCH USE ONLY". Commercial licence is paid. | No | — | — | — | Do not install. (Drawing an "OpenPose-format" stick figure ourselves for ControlNet does not use OpenPose code.) | openpose/LICENSE |
| **MoveNet** (Google, TF Hub/Kaggle) | model | **Unknown.** No licence shown on the pages I read (tfjs-models dir, TF tutorial, Kaggle stub). Commonly Apache-2.0, but not verified. | Unknown | — | Kaggle may need login | Very light (17 2D keypoints only) | 2D only. Weaker than MediaPipe for our use. | Not found |
| **ViTPose** | library + weights | Code Apache-2.0. **Weights unknown** (OneDrive, no terms). Trained on COCO/AIC/MPII/… | Unknown | — | — | ViTPose-H heavy, but fits 12 GB | Needs legal review. | github.com/ViTAE-Transformer/ViTPose |
| **Meta Sapiens** | models | **No.** CC BY-NC 4.0 (LICENSE) | NC only | Required | HF | 0.3B–2B, heavy | Sapiens2 licence not checked. | facebookresearch/sapiens/LICENSE |
| **4D-Humans (HMR2.0)** / **WHAM** | video-to-3D | Code MIT, **but needs SMPL (non-commercial)** plus registration. WHAM also needs ViTPose/DPVO/DROID-SLAM. | No (SMPL) | — | SMPL account | GPU heavy | **Not usable for production.** | GitHub READMEs + SMPL licence |
| **Blender** (BVH importer bundled) | tool | **Yes.** The GPL covers the program, not output. Blender says exported 3D files and .blend files are "your sole property". | Our outputs: yes | None for outputs | None | Fine | Python scripts that `import bpy` are arguably GPL if *distributed*. Internal pipeline scripts are not distributed, so no issue. BVH section of the manual could not be read (truncated). | blender.org manual/FAQ via search snippets (pages 403) |
| **bvh-toolbox** (`bvhtoolbox`) | Python lib | Yes, MIT | Yes | MIT notice | None | Trivial | bvh2csv gives hierarchy, rotations and **world positions** per joint, which is exactly what projection needs. | github.com/OlafHaag/bvh-toolbox |
| **PyMO** | Python lib | Yes, MIT | Yes | MIT notice | None | Trivial | "highly experimental". No retargeting, no releases. | github.com/omimo/PyMO |

## 2. Classification

### Usable now (commercial OK, no account)
- **CMU Graphics Lab Motion Capture Database** (original data, or Bruce Hahne's BVH conversion). Do not resell the raw data, and avoid NC re-packagings such as the 4TU FBX. *(Verify the wording on mocap.cs.cmu.edu in a browser, because the TLS error blocked my direct read.)*
- **Quaternius Universal Animation Library 1 and 2** (free tier, CC0).
- **Kenney animated characters** (CC0, very limited).
- **Blender** (GPL program; outputs are ours) with its bundled BVH importer.
- **bvh-toolbox** (MIT), **PyMO** (MIT), numpy (BSD).
- **MediaPipe Pose Landmarker**: library and model are Apache-2.0. Technically usable, but only if a licensed video source exists (see 3.0).

### Usable with conditions
- **Mixamo**: royalty-free in games, but needs an Adobe ID. A human must do the download (Adobe ToS §6.6 bars non-interface access; agents have no web anyway). Raw FBX must not be redistributed, so keep it out of public repos and asset dumps and ship only baked or derived animation. Never use it as ML training data (§17(C)).
- **Rokoko Motion Library / Vision**: needs an account. No automated access, no AI training, no raw redistribution. Vision needs our own video, which rules it out.
- **DeepMotion**: commercial use only on a **paid** plan. Needs an account and input video.
- **MMPose / RTMPose / rtmlib**: Apache code is OK. Weights are conditional on training-dataset licences.
- **Paid store packs** (hammer animsets): purchase plus store EULA.

### Not usable for production (research / non-commercial)
- Bandai Namco Research Motion Dataset 1 and 2 (CC BY-NC 4.0)
- Ubisoft LaFAN1 (CC BY-NC-ND 4.0)
- AMASS (non-commercial; commercial by separate licence)
- Human3.6M (academic only)
- SMPL, and therefore 4D-Humans, WHAM and other SMPL-based video-to-3D tools
- OpenPose (non-commercial research only)
- Meta Sapiens (CC BY-NC 4.0)
- DeepMotion Freemium tier

### Unknown: needs legal review
- **Truebones** free packs (separate "Use Restrictions" doc not read; the CC pack's licence variant is not named)
- **MoveNet** weights (no licence found on the pages read)
- **ViTPose** weights (no terms on the OneDrive links)
- **RTMPose / RTMW3D weights** (dataset-derived licences, e.g. COCO-WholeBody)
- **Mixamo's current official FAQ** (helpx 403). The community FAQ dates from the 2022 "technology preview" era, so confirm that the current wording still matches.
- **Stock-video-to-pose** (e.g. running MediaPipe on stock footage): the footage licence and the performer's likeness rights were not researched.

## 3. Recommended reference-driven pipeline for 2D

### 3.0 Why mocap and not video
The Board will not record motion. Every video-to-pose route (MediaPipe, RTMPose, Rokoko Vision, DeepMotion) needs licensed video of a person, and SMPL-based video-to-3D is non-commercial anyway. Existing **commercially usable 3D mocap is the cleanest source**. It also gives true 3D joints, so we can choose any camera, including three-quarter. MediaPipe stays an optional, Apache-licensed fallback that should not be adopted now.

### 3.1 Steps

| Step | What | Tool (licence) | Notes |
|---|---|---|---|
| 1. Motion source | Pick trials | **CMU mocap** BVH (CMU: free incl. commercial; Bruce Hahne BVH: no extra restrictions). Fallback: **Quaternius UAL2** (CC0). Optional: **Mixamo** downloaded by a human (conditions above). | The Board downloads a fixed list of trials (see section 4), not the whole 2.5 GB set. Store them in a private repo or out of repo, with a `SOURCES.md` recording the licence and trial IDs. |
| 2. Extraction | BVH to per-frame world joint positions | **Blender** BVH import (bundled) *or* **bvh-toolbox** `bvh2csv` (MIT), which writes `*_worldpos.csv` directly. | bvh-toolbox avoids Blender entirely for a headless, agent-friendly step. Blender is useful when a human or agent wants to look at it. |
| 3. 3D-to-2D projection | Orthographic projection from a three-quarter side camera | numpy (BSD) script, or Blender camera plus `bpy_extras.object_utils.world_to_camera_view` | **Camera:** orthographic (no perspective foreshortening, matching 2D sprites). Yaw **about 30–35° off pure profile** toward the viewer (three-quarter side: the far shoulder is just visible). Pitch **about 10–15° downward** for a slight top-down read. Lock the camera to the character's facing at frame 0, not per frame. Keep depth (camera-space Z) per joint for draw order of near and far limbs. |
| 4. Retarget to custom 2D skeleton | Different proportions (chibi or heroic) | Own numpy script (no new dependency) | Use **direction-based retargeting**: for each 2D bone, take the projected **unit direction** (or angle) of the source bone and re-apply it with the **target bone length**, walking the hierarchy from the pelvis. Scale root translation by the leg-length ratio. Then apply simple 2-bone IK to pin the planted feet, and the hands to the weapon line for two-handed grips. Do this in 2D after projection, so it needs no 3D rig for the custom character. |
| 5. Key pose extraction | Anticipation, apex, contact, follow-through, recovery | Own numpy script | Features: wrist (or weapon tip) speed and height, plus pelvis height. Keys: **(a)** start rest; **(b)** wind-up apex = max wrist height or min wrist speed before the swing; **(c)** mid-swing = peak speed; **(d)** contact = wrist height minimum with a speed drop; **(e)** follow-through extreme; **(f)** recovery settle. Fall back to curve-simplification (Ramer–Douglas–Peucker on the joint-angle curves) for in-betweens. |
| 6. Stylisation | Make it read as a game attack | Own script plus existing art pipeline | Exaggerate angles away from rest (×1.2–1.5) at the wind-up and contact keys. Hold the apex (anticipation) and the contact frames (hit-stop). Cut in-betweens on the strike (1–2 frames, optional smear). Push the hammer arc wider. Output pose skeletons (JSON plus stick-figure PNGs) as pose guides for the art pipeline, with the house style applied there. |

### 3.2 Minimum new dependencies (each needs Board approval)
1. **CMU mocap data**: a named list of BVH trials (download approval). Source: the CMU site, or Bruce Hahne's BVH conversion (cgspeed hosting may be gone; the una-dinosauria GitHub mirror exists). Agents have no web access, so the Board fetches the files.
2. **bvh-toolbox** (MIT, pip `bvhtoolbox`). *Or* skip it and use **Blender** if it is already installed and approved. Pick one; both are not needed.
3. **numpy**: probably already present. If not, it is an approval item (BSD).

Not needed now: MediaPipe, RTMPose, Mixamo, Rokoko, DeepMotion, PyMO.

## 4. Benchmark: heavy overhead hammer / axe / sledgehammer smash

**Best commercially usable source: CMU mocap, subject 79 and subject 80 "chopping wood".** Chopping wood is the closest real-world analogue of an overhead two-handed heavy smash: a two-handed overhead wind-up, a downward strike to a low target, and an impact stop.

Clip IDs, from the CMU index text in github.com/una-dinosauria/cmu-mocap (`cmu-mocap-index-text.txt`) and cross-checked in the KIT mirror (entry #1083 = CMU subject 79, 60 Hz):

| Trial | Description (CMU index) | Fit |
|---|---|---|
| **79_01** | chopping wood | **Primary candidate**: two-handed overhead chop |
| **80_71** | chopping wood | Second take, different actor |
| 86_04 | walking, stretching, punching, chopping, and drinking | Mixed. Chop section only. |
| 86_05 | walking, jumping, jumping jacks, …, punching, chopping, … | Mixed |
| 62_07, 62_08, 62_10 | hammering a nail / hammering sequence | **One-handed** hammer, small amplitude. Useful for a one-handed variant's timing, not for a heavy smash. |
| 124_07 | Baseball Swing | Two-handed horizontal swing, for a side-sweep variant |
| 02_07–02_09 | swordplay | One-handed weapon arcs |

No CMU trial is labelled "axe", "sledge" or "overhead". I saw no motion files, so the Board or an agent must visually confirm that 79_01 and 80_71 show a full overhead two-handed swing before relying on them.

**Licence status:** commercial use allowed per CMU ("free for use in research and commercial projects worldwide"). Raw data must not be resold. Acknowledgement is requested for publications. Status: **usable now**, pending a browser check of the CMU wording.

Other options considered:
- **Bandai Namco** "slash" (Dataset-1) is non-commercial, so not usable.
- **Mixamo** reportedly has two-handed and greatsword downward attacks (forum hint only; exact clip names not confirmed). It is usable with conditions (human download, Adobe ID, no raw redistribution). It is a good stylised second reference if the CMU chop reads too "woodcutter".
- **Quaternius UAL2** has CC0 "melee and armed combos", but no hammer or overhead clip could be confirmed from the published pages.

## Sources read
- https://raw.githubusercontent.com/una-dinosauria/cmu-mocap/master/READMEFIRST.txt and `cmu-mocap-index-text.txt`
- https://motion-database.humanoids.kit.edu/details/motions/1083/
- https://www.adobe.com/legal/terms.html ; https://community.adobe.com/questions-696/mixamo-faq-licensing-royalties-ownership-eula-and-tos-589400
- https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker ; https://github.com/google-ai-edge/mediapipe ; https://huggingface.co/litert-community/MediaPipe-PoseLandmarker-Full ; https://pypi.org/project/mediapipe/
- https://github.com/BandaiNamcoResearchInc/Bandai-Namco-Research-Motiondataset (+ Dataset-1 README and LICENSE)
- https://github.com/ubisoft/ubisoft-laforge-animation-dataset (+ license.txt)
- https://amass.is.tue.mpg.de/license.html ; https://smpl.is.tue.mpg.de/modellicense.html ; http://vision.imar.ro/human3.6m/eula.php
- https://github.com/open-mmlab/mmpose (+ LICENSES.md, projects/rtmpose) ; https://github.com/Tau-J/rtmlib
- https://github.com/CMU-Perceptual-Computing-Lab/openpose/blob/master/LICENSE
- https://github.com/ViTAE-Transformer/ViTPose ; https://github.com/facebookresearch/sapiens (+ LICENSE)
- https://github.com/shubham-goel/4D-Humans ; https://github.com/yohanshin/WHAM
- https://www.rokoko.com/studio-term-of-use ; https://www.rokoko.com/es/resources/motion-library-10-free-fight-and-weapon-animations
- https://deepmotion.com/faq
- https://quaternius.com/packs/universalanimationlibrary.html ; https://quaternius.com/packs/universalanimationlibrary2.html ; https://kenney.nl/assets/animated-characters-1
- https://github.com/OlafHaag/bvh-toolbox ; https://github.com/omimo/PyMO
- https://www.tensorflow.org/hub/tutorials/movenet ; tfjs-models movenet directory
- Search snippets only (not read directly): helpx Mixamo FAQ, blender.org licence/FAQ, Truebones Gumroad, CMU/UPenn "may not resell" wording, MoCap Online licensing.
