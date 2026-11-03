# Viral "finger-drawn shape" hand-tracking AR effects: creators, stacks and the algorithms to rebuild them (as of Sep 2026)

Scope: webcam effects where two hands define a rectangle or polygon, a 3D box or prism, or a "frame" that applies a filter inside it. Covers (a) who makes them and with what tools, and (b) the code-level techniques: geometry from landmarks, 3D and depth, jitter filtering, gesture state machines, and rendering effects inside a shape. Research date: 2026-09-27. Older items are dated inline.

---

## 1. Who makes the viral finger-frame and shape demos, what stacks they use, and which open-source repos reproduce them

### Takeaway
The viral look comes from two stacks. Artists and "creative technologists" use **TouchDesigner plus Torin Blankensmith's MediaPipe plugin**: a Corner Pin TOP is pinned to 4 fingertips and a Lookup, noise or feedback effect is composited inside it. Developers use **Python + MediaPipe Hand Landmarker + OpenCV** or **browser JS (MediaPipe Tasks Vision) + Three.js/WebGL**. Several open-source repos from 2025–2026 reproduce the "rectangle between two hands applies a filter" effect and the "glass box / cube held between hands" effect. One of them credits the Douyin creator "manualtracking / AM" as the source of the glass-box and mirror-sheet effects.

### Cited Findings
**TouchDesigner ecosystem (the main source of the "artsy" viral clips)**
- Torin Blankensmith (@blankensmithing) and Dom Scott made the MediaPipe TouchDesigner plugin. It is "a GPU Accelerated, self-contained, MediaPipe Plugin for TouchDesigner that runs on Mac and PC with no installation" and supports all MediaPipe vision models except Interactive Segmentation and Image Embedding — [GitHub torinmb/mediapipe-touchdesigner](https://github.com/torinmb/mediapipe-touchdesigner); [Derivative tutorial](https://derivative.ca/community-post/tutorial/face-hand-pose-tracking-more-touchdesigner-mediapipe-gpu-plugin/68278)
- Plugin internals: data flows over a **WebSocket** from an embedded browser component. The README notes a **minimum 3-frame latency** from that component and a 720p input-resolution limit. It is MIT-licensed with about 2.8k stars. Mac uses Syphon and Windows uses SpoutCam for virtual-camera input. Disabling HyperThreading/SMT reportedly gives a "60-80% improvement" — [GitHub torinmb/mediapipe-touchdesigner](https://github.com/torinmb/mediapipe-touchdesigner)
- Plugin hand-tracker defaults per DeepWiki (indexed Apr 2025): numHands 2, min detection/presence/tracking confidence 0.5, gesture scoreThreshold 0.5. Outputs are landmarks (x,y normalized 0–1, z relative to wrist), world landmarks, handedness and gesture categories with scores — [DeepWiki: mediapipe-touchdesigner hand tracking](https://deepwiki.com/torinmb/mediapipe-touchdesigner/4.2-hand-tracking-and-gestures)
- Torin is a freelance creative technologist and an adjunct professor at Parsons School of Design, teaching TouchDesigner — [ACM paper page](https://dl.acm.org/doi/fullHtml/10.1145/3641236.3665164). His X post (Jan 2025) says: "Created in #TouchDesigner using the MediaPipe plugin for hand tracking (created by myself & @domscott.art)" — [X/blankensmithing](https://x.com/blankensmithing/status/1884523747798835239) (search snippet; page not fetchable)
- On Feb 19, 2025 Torin released a **3-part "Hand Tracking Master Class in TouchDesigner with MediaPipe"**, based on his Genuary 2025 artworks, with project files on Patreon — [Derivative](https://derivative.ca/community-post/tutorial/hand-tracking-master-class-touchdesigner-mediapipe/71352); [Patreon](https://www.patreon.com/posts/hand-tracking-in-122563479); [TikTok announcement](https://www.tiktok.com/@blankensmithing/video/7473216793918721323)
- Earlier (Jan 3, 2024) Torin published a "Picture in Picture Hand Tracking Effect" tutorial: a hand-controlled Droste (recursive frame) effect inspired by the Genuary day-3 prompt, with bonus reaction-diffusion — [Derivative](https://derivative.ca/community-post/tutorial/picture-picture-hand-tracking-effect-touchdesigner-tutorial/68828)
- **Reference TD build of the "rectangle between fingers" effect (neempata, "Hand-Held Noise Portal").** The four corners are the **thumb tips (bottom-left/right) and index tips (top-left/right) of hand 1 and hand 2**. A **Corner Pin TOP** uses expressions that read the tracked points, so the panel "stretch[es], skew[s], and rotate[s]". Inside, a **Lookup TOP + animated noise** recolours pixels: "Every pixel inside the panel is replaced by a colour chosen by its brightness", and noise Z-translate is tied to `absTime.seconds`. MediaPipe settings: hands only, 1280×720, horizontal flip on, detection/presence/tracking confidence **0.2**, because lower values reduce panel dropout. It requires TouchDesigner 2025.30000+ and a Vulkan GPU, and the .toe is about 180 MB because it embeds the MediaPipe component — [GitHub neempata/Noise-Portal-Handtracking-Touchdesigner](https://github.com/neempata/Noise-Portal-Handtracking-Touchdesigner)
- A YouTube tutorial titled "Interactive Effect in TouchDesigner w MediaPipe | TUTORIAL | Finger Filter Power" covers the same finger-filter effect. The channel name and date could not be retrieved — [YouTube](https://www.youtube.com/watch?v=Rm56X6to6-Y)
- Bileam Tschepe (elekktronaut) is a Berlin-based artist and educator who makes audio-reactive, interactive and organic works in TouchDesigner and runs tutorials on YouTube and Patreon — [elekktronaut about](https://www.elekktronaut.com/about); [Patreon](https://www.patreon.com/cw/elekktronaut). No specific viral finger-frame piece by him was found (see Gaps).

**The Douyin "glass box / origami mirror" effects and their Python reproduction**
- The repo **Eureka0w0v0/manual-tracking** (pure Python: MediaPipe Hand Landmarker + OpenCV) reproduces three hand-pinned effects. These are an **origami mirror sheet**, a **glass box** (a cuboid held between two hands, each face with a different filter) and a **floating cube**. It credits "the origami mirror sheet and glass box from 'manualtracking / AM' on Douyin (colours and geometry were reverse-measured pixel by pixel from the video)". It runs detection at 30 fps on CPU and references torinmb/mediapipe-touchdesigner as a TD baseline — [GitHub Eureka0w0v0/manual-tracking](https://github.com/Eureka0w0v0/manual-tracking)
- In that repo's table, several glass-box face treatments (riso print, duotone, point cloud, quadtree mosaic, halftone) have "TouchDesigner recording" as their reference source — [GitHub Eureka0w0v0/manual-tracking](https://github.com/Eureka0w0v0/manual-tracking)

**Python/OpenCV "finger-frame filter window" reproductions**
- **Ali533-blip/hand-filter-window** (MIT, Python 3.9+) offers:
  - A dual-hand "frame window" whose quad corners are the **thumb and index fingertips**.
  - A **prayer pose** (palms together) that switches the filter to fullscreen.
  - **Fist**-spawned physics "filter orbs" that can be thrown, stretched and merged.
  - Five filters: `thermal`, `cartoon`, `edges`, `negative`, `pop-color`. Adding one is "a 5-line job: drop a `frame -> frame` function into `filters.py`".
  - Code split into `compositor.py` ("smoothing + mask compositing") and supersampled rendering (`--ss 2`).
  - "All gesture thresholds are relative to hand size in the frame" — [GitHub Ali533-blip/hand-filter-window](https://github.com/Ali533-blip/hand-filter-window)
- **Joshithaaa09/Hand-Filter-Window** is the same concept: Hand Landmarker 21 points plus OpenCV "filters, compositing, and supersampled rendering" — [GitHub](https://github.com/Joshithaaa09/Hand-Filter-Window) (search snippet)
- **varshithakothakota/instaviral** is "inspired by a viral Instagram visual effect" and does not name the creator. Modules: `hand_tracking.py`, `gestures.py`, `filters.py`, `smoothing.py`, `camera.py`; Python 3.12 with `hand_landmarker.task` — [GitHub](https://github.com/varshithakothakota/instaviral)
- **andres-ferreiro/pinch-vision** is a Python/OpenCV desktop app plus a WebGL browser build. Pinches drive thermal, night-vision, edge-glow, echo-trails, glitch, ASCII, halftone, pixelate and invert effects (details in §5) — [GitHub](https://github.com/andres-ferreiro/pinch-vision)

**Browser / Three.js creators**
- "Alan" (Instagram @stereo.drift, X @measure_plan, GitHub collidingScopes) publishes a "Fun With Computer Vision" series of Three.js + MediaPipe demos:
  - **3D-editor**: the right hand pinches to grab or move a cube corner and pinch-drags a colour wheel; the left hand makes a fist and moves to rotate — [GitHub collidingScopes/3D-editor](https://github.com/collidingScopes/3D-editor)
  - **threejs-handtracking-101**: pinch to resize a sphere — [GitHub](https://github.com/collidingScopes/threejs-handtracking-101)
- Browser tools that productize the effect: **Finger Frame AI Effect** ("frame your face with both hands", styles such as Toon, Anime, Van Gogh, live in the browser) — [fingerframeai.com](https://fingerframeai.com/); [fingerframe.app](http://fingerframe.app/). **ZoopTools "Hand Portal Filter"** runs client-side in the browser with a "Thermal" option and notes that "if the portal lags behind your gesture by even a few frames, the whole illusion falls apart" — [ZoopTools](https://www.zooptools.com/hand-portal-filter)
- A Bolt blog says "viral hand and face tracking effects [are] taking over X in recent months" and recommends React + MediaPipe stacks. It names no creators — [Bolt blog](https://bolt.new/blog/face-and-hand-tracking-bolt-mediapipe)

**Platform context (no-code AR tools)**
- **Meta Spark shut down on Jan 14, 2025.** Third-party AR effects built on Spark were removed from Instagram, Facebook and Messenger — [Meta Spark](https://spark.meta.com/learn/publishing/spark-ar-review-policies/); [Social Media Today](https://www.socialmediatoday.com/news/metas-shutting-down-spark-ar-studio/725443/)
- Snap **Lens Studio** has a 3D Hand Tracking component with two rigged hand models and a "Two hands" option, plus 3D Hand Interactions and Hand VFX templates — [Snap docs](https://developers.snap.com/lens-studio/features/ar-tracking/hand/hand-tracking-templates/3d-hand-tracking)
- TikTok **Effect House** offers a Hand Tracker, a 3D Hand Tracker (per-joint keypoints for both hands), Hand Info (bounding rect, keypoints) and a Gesture Detection node — [Effect House 3D Hand Tracker](https://effecthouse.tiktok.com/learn/guides/technical-guides/objects/ar-tracking/3d-hand-tracker); [Gesture Detection](https://effecthouse.tiktok.com/learn/guides/visual-scripting/nodes/hand/gesture-detection)

**Library versions (2026)**
- PyPI `mediapipe` latest is **1.0.1 (2026-08-14)**, after 1.0.0 (2026-07-27) and 0.10.35 (2026-04-27). npm `@mediapipe/tasks-vision` latest is 1.0.1, with a nightly of 1.1.0-rc.20260924 — [PyPI mediapipe](https://pypi.org/project/mediapipe/); [npm @mediapipe/tasks-vision](https://www.npmjs.com/package/@mediapipe/tasks-vision)
- Since 0.10.30/0.10.31 (Dec 2025) many users report `AttributeError: module 'mediapipe' has no attribute 'solutions'`. The legacy `mp.solutions.hands` API used by most older tutorials is gone, and only `mediapipe.tasks` is exposed — [Issue #6192](https://github.com/google-ai-edge/mediapipe/issues/6192); [Issue #6200](https://github.com/google-ai-edge/mediapipe/issues/6200)
- pinch-vision pins MediaPipe **0.10.35** and says "version 1.x incompatible on macOS" — [GitHub andres-ferreiro/pinch-vision](https://github.com/andres-ferreiro/pinch-vision)

### Inferences
- The recurring recipe across TD, Python and JS reproductions is the same: **4 fingertip points (thumb tip 4 and index tip 8 of each hand) → quad → per-pixel effect inside, original feed outside**. The only big variables are the effect and whether the quad may self-intersect (TD Corner Pin and the Eureka mirror sheet let it twist).
- Because Spark effects vanished in Jan 2025, the IG/TikTok "finger frame" clips in 2025–2026 are most likely **screen recordings from TouchDesigner or custom code**, not in-app filters. Lens Studio and Effect House are the remaining in-app routes.
- Torin's plugin uses MediaPipe's web runtime in an embedded browser (WebSocket plus a 3-frame minimum latency). So a native Python or JS pipeline can have lower end-to-end latency than the TD route. That matters because of the ZoopTools point about lag.
- New Python code should target the **Tasks API** (`mp.tasks.vision.HandLandmarker` with a `.task` model) rather than `mp.solutions`. Pin the version and test on the target OS, given the 1.x/macOS report.

### Gaps
- I could not identify with certainty the original creator of the specific viral "rectangle between both hands applies a colour/thermal filter" reel. Repos call it "a viral Instagram visual effect" without credit. Instagram, TikTok and X content could not be crawled (X returned 402, and YouTube metadata was unavailable).
- No view counts or engagement numbers were obtainable for any viral clip.
- No specific finger-frame or shape viral work by Bileam Tschepe (elekktronaut) was found; his relevance is as a TD educator.
- The exact CHOP channel naming in Torin's plugin (e.g. per-landmark channel names) was not documented in the pages fetched.

---

## 2. Geometry from landmarks: indices, quads, vertex ordering, cubes from 3 points, depth, intrinsics, solvePnP and monocular limits

### Takeaway
MediaPipe gives 21 landmarks per hand in two coordinate systems:
- **Normalized image landmarks**: x,y in [0,1]; z is relative depth with the wrist as origin, in roughly the same scale as x.
- **World landmarks**: metric meters, with origin at the hand's approximate geometric centre, *not* the camera.

Getting camera-space metric positions (needed for true 3D boxes) means combining the two with approximate intrinsics via **solvePnP**, or with a similar-triangles scale estimate. Most viral builds instead construct geometry in 2D, or in "weak perspective" 3D driven by a few low-noise hand parameters.

### Cited Findings
- Landmark indices (`HandLandmark` enum in MediaPipe Tasks Python):
  - WRIST=0
  - THUMB_CMC=1, THUMB_MCP=2, THUMB_IP=3, **THUMB_TIP=4**
  - INDEX_FINGER_MCP=5, PIP=6, DIP=7, **INDEX_FINGER_TIP=8**
  - MIDDLE_FINGER_MCP=9, PIP=10, DIP=11, **TIP=12**
  - RING 13–16 (TIP=16)
  - PINKY 17–20 (TIP=20)

  — [mediapipe/tasks/python/vision/hand_landmarker.py](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/python/vision/hand_landmarker.py)
- Normalized landmarks: "`x` and `y` are normalized to `[0.0, 1.0]` by the image width and height respectively. `z` represents the landmark depth with the depth at the wrist being the origin, and the smaller the value the closer the landmark is to the camera. The magnitude of `z` uses roughly the same scale as `x`." — [MediaPipe Hands legacy docs](https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/hands.md)
- World landmarks: "real-world 3D coordinates in meters with the origin at the hand's approximate geometric center" — [MediaPipe Hands legacy docs](https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/hands.md). The current Hand Landmarker guide describes world landmarks as meters "relative to the wrist" — [Hand Landmarker guide](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker). The two docs conflict on the origin (geometric centre vs wrist); treat the origin as hand-local either way.
- Handedness "is determined assuming the input image is mirrored, i.e., taken with a front-facing/selfie camera with images flipped horizontally" — [MediaPipe Hands legacy docs](https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/hands.md)
- Hand Landmarker model and defaults:
  - It is a bundle of a palm-detection model and a landmark model, trained on about 30K real images plus synthetic renders.
  - Options: running modes IMAGE, VIDEO or LIVE_STREAM; `num_hands` default **1** (set 2 for two-hand shapes); detection/presence/tracking confidence default 0.5.
  - Pixel 6 latency: 17.12 ms CPU, 12.27 ms GPU; float16.

  — [Hand Landmarker guide](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker)
- A Google forum answer (Dec 2025) says world-landmark z "can be used to estimate relative depths". The 21 points are skeletal, not surface points — [Google AI forum](https://discuss.ai.google.dev/t/clarification-on-the-world-landmark-coordinates-of-the-mediapipe-hand-landmarker/86489)
- **solvePnP recipe to get the hand in camera space** (gist by sherbondy):
  - Object points are the world landmarks (`[-l.x, -l.y, -l.z]`); image points are the image landmarks times frame width/height.
  - Intrinsics are approximated with `focal_length = frame_width * 0.75`, principal point at the image centre and zero distortion.
  - It calls `cv2.solvePnP(..., flags=cv2.SOLVEPNP_SQPNP)` and uses **only the translation** for placement, "because the rotation is accounted for in the model coordinates".
  - Caveat: the 3D position depends on focal-length accuracy and needs manual tuning if the true focal length is unknown.

  — [Gist: MediaPipe hand → world space via solvePnP](https://gist.github.com/sherbondy/58bdd1d8983d9ba96043fea57f9e7429)
- OpenCV solvePnP constraints:
  - Generally ≥4 points.
  - SQPnP needs ≥3.
  - P3P/AP3P need exactly 4.
  - IPPE needs ≥4 **coplanar** points; IPPE_SQUARE needs 4 points in a fixed square order (marker case).
  - DLS/UPNP are "broken" and fall back to EPnP.
  - ITERATIVE with `useExtrinsicGuess=true` works from 3 points but has up to 4 solutions.

  — [OpenCV calib3d.hpp (4.x)](https://github.com/opencv/opencv/blob/4.x/modules/calib3d/include/opencv2/calib3d.hpp)
- Monocular models "don't directly say anything about the hand's absolute depth relative to the camera". Collabora's Monado tracker used stereo triangulation to get absolute depth — [Collabora blog, May 2022](https://www.collabora.com/news-and-blog/blog/2022/05/31/monado-hand-tracking-hand-waving-our-way-towards-a-first-attempt/)
- A cheap depth proxy in Three.js (Codrops, Oct 2024): x is mapped as `-landmark.x + 0.5` (mirror + centre). Z comes from the **distance between wrist and middle-finger PIP**, mapped and clamped to a z range (larger hand → nearer) — [Codrops: 3D hand controller](https://tympanus.net/codrops/2024/10/24/creating-a-3d-hand-controller-using-a-webcam-with-mediapipe-and-three-js/)
- **Parametric cuboid instead of vertex pinning** (glass box):
  - Per hand, the code extracts an anchor (between palm centre and finger-arc midpoint, `anchor_lift` 0–1), a box axis and length, a height from finger-arc spread, a depth component from palm-width ratio, and roll from palm orientation.
  - "The hands do not pin vertices, they only supply a few low-noise parameters... The cuboid is built in 3D and projected with weak perspective, so rigidity and two-point perspective are constructed rather than corrected."
  - Vertex order and projection live in `boxgeom.py`, and a `docs/GLASS_BOX_GEOMETRY.md` covers calibration.

  — [GitHub Eureka0w0v0/manual-tracking](https://github.com/Eureka0w0v0/manual-tracking)
- The same repo's **mirror sheet pins its 4 corners to both thumb tips and both index tips**. Flipping one hand darkens that half, crossing hands twists it, and pinching both collapses it to a line — [GitHub Eureka0w0v0/manual-tracking](https://github.com/Eureka0w0v0/manual-tracking)
- Simple cube controller (evch1204): it defines a cube with 8 vertices and 12 edges, applies X/Y/Z rotation matrices, and projects "to 2D screen space with perspective". Hand pitch and yaw come from wrist→middle MCP; scale comes from the distance between the two index tips (clamped 0.5×–3×). It draws a wireframe in OpenCV — [GitHub evch1204/hand_tracker](https://github.com/evch1204/hand_tracker)
- OpenCV `convexHull` uses Sklansky's O(N log N) algorithm and returns points or indices, clockwise or counter-clockwise — [OpenCV imgproc.hpp](https://github.com/opencv/opencv/blob/4.x/modules/imgproc/include/opencv2/imgproc.hpp)

### Inferences
Implementation recipes, synthesized from the sources above:
- **Quad from two hands:** `P = [L[4], L[8], R[8], R[4]]` (left thumb, left index, right index, right thumb), in pixel space after `x*W, y*H`.
  - With a mirrored selfie display, flip x *before* building geometry, and remember that MediaPipe's handedness assumes mirrored input.
  - **Semantic order** (thumbs = bottom, index = top, as in neempata) keeps the texture orientation stable and allows "twist" when the hands cross.
  - For a guaranteed simple polygon, sort the 4 points by `atan2(p.y-c.y, p.x-c.x)` around the centroid `c`.
  - Detect self-intersection with the orientation (2D cross-product) test on edges (0-1 vs 2-3) and (1-2 vs 3-0): segments AB and CD intersect iff `sign(cross(B-A,C-A)) != sign(cross(B-A,D-A))` and `sign(cross(D-C,A-C)) != sign(cross(D-C,B-C))`.
  - `cv2.convexHull` alone can drop a point, returning a triangle when one fingertip lies inside the other three. That breaks 4-point homographies, so use the angular sort for masks and semantic order for texture mapping.
- **More than 4 points / arbitrary polygon:** use all 10 fingertips (4, 8, 12, 16, 20 × 2 hands) → `convexHull` → mask. Or "draw" a polygon by appending the index-tip position while pinching and closing it on release.
- **Cube or prism from 3 points** (e.g. left index tip A, right index tip B, and C = left thumb tip):
  - `u = normalize(B-A)`
  - `v = normalize((C-A) - dot(C-A,u)*u)` (Gram–Schmidt)
  - `n = cross(u, v)`
  - Edge `s = |B-A|`; height `h = |(C-A)·v|` (or `s` for a cube); depth `d` = s, a pinch distance, or a hand-scale-derived value.
  - The 8 vertices are `A + a*s*u + b*h*v + c*d*n` for a,b,c ∈ {0,1}. Project with `x = fx*X/Z + cx`, `y = fy*Y/Z + cy`.
  - In 2D-only builds (weak perspective), keep A, B, C in pixel units with Z = constant, and fake the depth axis as an oblique screen offset whose length scales with hand size. This is what Eureka's "weak perspective" approach constructs.
- **Metric depth options, in order of effort:**
  1. Relative depth from normalized z: fine for ordering which hand is closer, not for absolute distance.
  2. Similar triangles: `Z ≈ f * |W0−W9|_world / |P0−P9|_pixels`, using the world-landmark wrist→middle-MCP length as the real length and the image length in pixels, with `f = (W/2)/tan(HFOV/2)`.
  3. solvePnP (SQPNP) on all 21 correspondences, as in the gist, to get `tvec` in meters.

  All three inherit MediaPipe's assumed hand scale and your focal-length guess, so absolute Z can be off by a constant factor. Relative motion is more reliable.
- For Three.js placement, either unproject NDC (`new Vector3(x*2-1, -(y*2-1), 0.5).unproject(camera)`) and move along the ray to the estimated Z, or match a `PerspectiveCamera` fov to the webcam's FOV and place objects at the solvePnP translation.

### Gaps
- No published webcam-to-webcam benchmark of the solvePnP-from-world-landmarks approach's absolute depth error was found.
- The exact math in Eureka's `docs/GLASS_BOX_GEOMETRY.md` and `boxgeom.py` was not fetched; only the README description is cited.
- I found no authoritative average hand-length constant for the similar-triangles method, which is why the inference above uses world landmarks as the metric reference.

---

## 3. Jitter reduction: One Euro, Kalman, EMA and recommended parameters

### Takeaway
The **1€ filter** (Casiez, Roussel, Vogel, CHI 2012) is the de-facto choice for landmark jitter: an adaptive-cutoff low-pass filter where `fc = fcmin + β|dx/dt|`. Tune fcmin first (static jitter), then β (lag). MediaPipe's own pose filtering uses a 1€ filter with `min_cutoff 0.05, beta 80, derivate_cutoff 1.0` on normalized coordinates, which is a good starting point for hand landmarks in [0,1] units. Simpler builds use EMA (e.g. 0.8 old / 0.2 new) plus hysteresis and dwell times on gestures.

### Cited Findings
- 1€ equations: `α = 1/(1 + τ/Te)`, `τ = 1/(2π fc)`, `fc = fcmin + β|Ẋ|`. The derivative is low-passed with a fixed **1 Hz** cutoff, leaving two parameters, fcmin and β — [Casiez et al., CHI 2012 PDF](https://gery.casiez.net/publications/CHI2012-casiez.pdf); [1€ site](https://gery.casiez.net/1euro/)
- Tuning: "First β is set to 0 and fcmin to a reasonable middle-ground value such as 1 Hz", then fcmin is adjusted while holding still, then β is increased while moving fast. "If high speed lag is a problem, increase β; if slow speed jitter is a problem, decrease fcmin." For β, start with magnitudes like 0.001 or 0.0001 — [1€ site](https://gery.casiez.net/1euro/); [paper](https://gery.casiez.net/publications/CHI2012-casiez.pdf)
- Paper comparison (noisy cursor data at a 50 dB SNR):
  - A moving average with n=14 set the reference jitter.
  - Single exponential needed α=0.11 (laggy). LaViola's double exponential used α=0.06 but overshot on abrupt deceleration.
  - The Kalman filter used measurement noise covariance 18.06 and process noise 0.3, with lag comparable to the moving average.
  - 1€ used fcmin=1 Hz and **β=0.007**, which "made the lag almost imperceivable". It "has less lag across all speed intervals".
  - Kalman needs a process model and more maths background.

  — [Casiez et al., CHI 2012 PDF](https://gery.casiez.net/publications/CHI2012-casiez.pdf)
- Context from the paper's review: MacKenzie found mouse movement times increased 16% with 75 ms lag. In 3D hand tracking, Ware and Balakrishnan found 50 ms of lag reduced performance — [Casiez et al., CHI 2012 PDF](https://gery.casiez.net/publications/CHI2012-casiez.pdf)
- MediaPipe's `pose_landmark_filtering.pbtxt` configures `LandmarksSmoothingCalculator` with `one_euro_filter { min_cutoff: 0.05  beta: 80.0  derivate_cutoff: 1.0 }`. Its comments say this gives "~0.01 alpha" when static and "~0.94 alpha" when moving fast. It also smooths visibility with a low-pass filter at alpha 0.1 — [mediapipe/modules/pose_landmark/pose_landmark_filtering.pbtxt](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/modules/pose_landmark/pose_landmark_filtering.pbtxt)
- Implementations: npm `1eurofilter`, PyPI `OneEuroFilter` (constructor `freq, mincutoff, beta, dcutoff`), Needle Engine's OneEuroFilter class — [npm](https://www.npmjs.com/package/1eurofilter); [PyPI](https://pypi.org/project/OneEuroFilter/); [Needle Engine](https://engine.needle.tools/docs/api/@needle-tools/engine/3.37.6-beta/classes/engine_api.OneEuroFilter.html)
- Real projects:
  - Eureka's `tracker.py` does "hand filtering (One Euro, tracks, handedness latch)" and `detect_service.py` does "velocity extrapolation". It also has keys that "cap angular rate to block flicker" — [GitHub Eureka0w0v0/manual-tracking](https://github.com/Eureka0w0v0/manual-tracking)
  - evch1204 uses EMA with "80% old value, 20% new value" — [GitHub evch1204/hand_tracker](https://github.com/evch1204/hand_tracker)
  - Sander de Snaijer's gesture maps (Apr 2026) use "exponential smoothing (EMA) on all movement", require gestures "held for at least 80ms", use a 150 ms grace period before returning to idle, and need 3 consecutive stable frames before escalating to a two-hand gesture — [sanderdesnaijer.com](https://www.sanderdesnaijer.com/blog/gesture-controls-openlayers-mediapipe)
- Collabora found 1€-style filters "add too much latency for use in XR" and moved on in newer tracking (May 2022) — [Collabora blog](https://www.collabora.com/news-and-blog/blog/2022/05/31/monado-hand-tracking-hand-waving-our-way-towards-a-first-attempt/)

### Inferences
- **Units matter for β.** β multiplies speed, so a β tuned in pixels/s differs from one tuned in normalized units/s by roughly the frame width (about 1000×). Start from MediaPipe's own normalized setting (0.05 / 80 / 1.0) when filtering normalized landmarks, or from the paper's (1 Hz / 0.007) for pixel-like units, then retune.
- **Filter what you render.** Filtering the 4–8 derived corner points (after ordering) is cheaper than filtering 42 landmarks × 3 axes and directly removes corner "swim". Keep a separate, lightly filtered stream for gesture thresholds so pinches don't lag.
- **Key filters by track identity**, not list index (MediaPipe's hand order can swap), and reset them when a hand is lost for more than the grace period. Otherwise the filter "slides" from the old position.
- Use the true per-frame `dt` (timestamps) in the 1€ filter, because webcam frame rates fluctuate.
- For stronger smoothing without lag, add **constant-velocity extrapolation** (as Eureka does) or a small Kalman filter on corners. Keep 1€ as the baseline, given the paper's comparison.

### Gaps
- No hand-specific published 1€ parameter set from Google was found. I found no smoothing calculator in the Tasks `hand_landmarker_graph.cc` source I inspected, so hand landmarks may come out unsmoothed; confirm empirically.

---

## 4. Gesture detection logic: pinch, extended/curled fingers, hysteresis, start/lock/release state machines, GestureRecognizer and Model Maker

### Takeaway
Robust demos use **scale-invariant distances** (divided by a hand-size reference such as wrist→middle MCP), **hysteresis** (separate enter and exit thresholds), **dwell times** and **grace periods**, all feeding an explicit state machine. MediaPipe's GestureRecognizer adds 7 canned static gestures. Custom static poses (e.g. an "L-shape" frame pose) can be trained with Model Maker from a folder-per-label image dataset that includes a required `none` class.

### Cited Findings
- **pinch-vision**:
  - Pinch = thumb–index distance divided by the **wrist→middle-knuckle length**, with **close/open thresholds 0.42 / 0.55** (hysteresis "to prevent flickering").
  - A thumb–pinky tap has a 0.45 s cooldown and a guard that the index finger is not pinching.
  - "Twist" knob: the wrist→pinch-point angle maps about 150° to 0→100%.

  — [GitHub andres-ferreiro/pinch-vision](https://github.com/andres-ferreiro/pinch-vision)
- **Sander de Snaijer (Apr 2026)**: a pinch enters at **25% of hand size** and releases at **35%**. Gestures must be held for ≥80 ms, there is a 150 ms grace period on end, and a two-hand gesture needs the second hand stable for 3 consecutive frames — [sanderdesnaijer.com](https://www.sanderdesnaijer.com/blog/gesture-controls-openlayers-mediapipe)
- **hand-filter-window**:
  - Fist = all four fingertips curled close to the palm centre.
  - Prayer = palms facing each other within a tight angle.
  - Throw = wrist acceleration above a threshold; merge = two fists within a distance threshold.
  - The state machine uses temporal hysteresis.

  — [GitHub Ali533-blip/hand-filter-window](https://github.com/Ali533-blip/hand-filter-window)
- **Eureka floating cube state machine**:
  - Single-hand pinch *on the cube* → rotate (horizontal drag = yaw, vertical = pitch); a pinch elsewhere is a no-op.
  - Two-hand pinch → translate (midpoint) + scale (distance) + twist ("steering-wheel" rotation about the screen normal).
  - Open hand with five fingers spread → exploded view.
  - Release → momentum and drift with edge bounces. Idle, the cube keeps turning at about 10°/s.
  - Rotation uses drag deltas rather than palm orientation, to avoid saturation "turnback".
  - `tools/cube_check.py` enforces 27 "feel" assertions.

  — [GitHub Eureka0w0v0/manual-tracking](https://github.com/Eureka0w0v0/manual-tracking)
- Open palm = "4+ fingers extended" (evch1204) — [GitHub evch1204/hand_tracker](https://github.com/evch1204/hand_tracker). Codrops: fist when the middle MCP→tip distance is below 0.35 in its scene units; interaction uses Box3 AABB intersection — [Codrops](https://tympanus.net/codrops/2024/10/24/creating-a-3d-hand-controller-using-a-webcam-with-mediapipe-and-three-js/)
- Real-Time-Finger-Detection repo uses "joint-angle analysis" for finger counting — [GitHub himanshupareek715-lgtm/Real-Time-Finger-Detection](https://github.com/himanshupareek715-lgtm/Real-Time-Finger-Detection) (search snippet)
- **MediaPipe GestureRecognizer** labels: `None, Closed_Fist, Open_Palm, Pointing_Up, Thumb_Down, Thumb_Up, Victory, ILoveYou`. It is a two-step pipeline (gesture embedding model + lightweight classifier) with the same detection/presence/tracking confidence defaults of 0.5. Pixel 6 latency: 16.76 ms CPU / 20.87 ms GPU — [Gesture Recognizer guide](https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer)
- **Model Maker customization**:
  - Dataset layout: `<dataset_path>/<label_name>/<img>`, and one label **must be `none`**.
  - HParams defaults: learning_rate 0.001, batch_size 2, epochs 10, lr_decay 0.99, gamma 2 (focal loss). ModelOptions: dropout_rate 0.05, layer_widths [].
  - It exports a `.task` bundle (hand detector + canned + custom classifier).
  - When both classifiers fire, the **custom gesture is preferred**.

  — [Customization guide](https://developers.google.com/edge/mediapipe/solutions/customization/gesture_recognizer); [Gesture Recognizer overview](https://developers.google.com/mediapipe/solutions/vision/gesture_recognizer)
- TouchDesigner community example: "MediaPipe Finger Pinch Dial Controller" — [Derivative](https://derivative.ca/community-post/tutorial/mediapipe-finger-pinch-dial-controller/74152)

### Inferences
Implementation patterns for the frame/box effect:
- **Hand scale:** `S = |P0 − P9|` (wrist → middle MCP). Every threshold is a ratio to S, which keeps it invariant to distance from the camera.
- **Finger extended test:** use an angle-based test that is robust to hand rotation. `θ = angle(P_mcp→P_pip, P_pip→P_tip)`; the finger is extended if θ is small (nearly straight), e.g. θ < ~35–40° (tune).
  - Thumb: use the angle at MCP/IP, or `dist(P4, P17) > k·S`.
  - Cheaper alternative: `dist(P_tip, P0) > dist(P_pip, P0)`.
- **"L-frame" pose (arms the frame):** thumb and index extended, middle/ring/pinky curled, and the angle between the thumb vector (P2→P4) and index vector (P5→P8) roughly 60–120°.
- **Suggested state machine:**
  - `IDLE → ARMING` when both hands are in the L-pose for ≥ N frames (e.g. 3–5, or ~100 ms).
  - `ARMING → ACTIVE`: the quad tracks the filtered corners.
  - `ACTIVE → LOCKED` on a trigger (both hands pinch, or corners still for > ~500 ms). Freeze the quad (snapshot the corners) and optionally freeze the texture (capture the frame).
  - `LOCKED/ACTIVE → RELEASE` when hands are lost longer than a grace period (e.g. 150 ms), or on fists or an open-palm swipe. Animate the shape out.
  - Use enter/exit hysteresis on every boolean (pinch 0.42/0.55·S style) and debounce with dwell and grace timers.
- **Two-hand identity:** don't rely on list order. Use handedness (remembering the mirrored-input assumption) plus nearest-neighbour to previous positions, and "latch" handedness (as Eureka does) to avoid left/right swaps.
- Use GestureRecognizer for coarse modes (Open_Palm = reset, Closed_Fist = grab, Victory = switch filter), and geometric rules for the continuous frame. Train a custom "frame" gesture with Model Maker only if the rules prove brittle, and remember the required `none` class.

### Gaps
- No authoritative source gives joint-angle thresholds for "extended vs curled" with MediaPipe; the values above are starting points to tune.
- The internal thresholds of the hand-filter-window prayer and fist detectors were not published in the README.

---

## 5. Rendering effects inside a shape: polygon masks, shaders and stencil, colour/thermal/pixelation/edge/invert, homography warp, translucent 3D boxes

### Takeaway
On CPU (Python/OpenCV):
1. Rasterize the quad or polygon into a mask with `fillPoly` or `fillConvexPoly`.
2. Run the filter (ideally only on the bounding-rect crop).
3. Composite with the mask (optionally feathered).
4. Use `getPerspectiveTransform` + `warpPerspective` to map a texture or rectified content onto the quad.

On GPU (WebGL/Three.js/TD), there are three options:
- Draw the quad itself and sample the camera texture in screen space.
- Do a point-in-polygon test in the fragment shader.
- Write the shape to the **stencil buffer** and run a full-screen effect pass only where the stencil matches.

Translucent cubes need back-to-front ordering per face, because Three.js sorts per object, not per triangle.

### Cited Findings
**OpenCV primitives**
- `fillConvexPoly` "is much faster than" `fillPoly`. It handles convex and monotonic polygons "without self-intersections". `fillPoly` can fill "areas with holes, contours with self-intersections" — [OpenCV imgproc.hpp](https://github.com/opencv/opencv/blob/4.x/modules/imgproc/include/opencv2/imgproc.hpp)
- `pointPolygonTest` returns +1/−1/0 (inside/outside/on edge), or a signed distance with `measureDist=true` — [OpenCV imgproc.hpp](https://github.com/opencv/opencv/blob/4.x/modules/imgproc/include/opencv2/imgproc.hpp)
- `getPerspectiveTransform(src, dst)` computes the 3×3 perspective transform from **exactly four point pairs** (quadrangle vertices). `findHomography` estimates it from ≥4 points with optional robust methods (RANSAC, LMeDS, RHO). Both are used with `warpPerspective` — [OpenCV imgproc.hpp](https://github.com/opencv/opencv/blob/4.x/modules/imgproc/include/opencv2/imgproc.hpp); [OpenCV calib3d.hpp](https://github.com/opencv/opencv/blob/4.x/modules/calib3d/include/opencv2/calib3d.hpp); [OpenCV homography tutorial](https://docs.opencv.org/4.x/d9/dab/tutorial_homography.html); [LearnOpenCV homography examples](https://learnopencv.com/homography-examples-using-opencv-python-c/)
- `applyColorMap` provides ready "thermal-looking" LUTs such as `COLORMAP_JET`, `COLORMAP_INFERNO` and `COLORMAP_TURBO` — [OpenCV imgproc.hpp](https://github.com/opencv/opencv/blob/4.x/modules/imgproc/include/opencv2/imgproc.hpp)

**Effect recipes from working repos**
- pinch-vision:
  - **Thermal**: "false colour driven by a skin-weighted heat estimate" in Cr–Cb chroma space, auto-ranged per frame at 1/6 resolution.
  - **Night vision**: auto-gain with `1 - exp(-gain*x)` roll-off instead of clipping, plus grain, scanlines and phosphor green.
  - **Edge glow**: gradient magnitude, bloomed.
  - **Echo trails**: WebGL ping-pong framebuffers.
  - **Glitch**: RGB channel split plus displaced horizontal slices.
  - **ASCII**: glyph atlas texture, one glyph per cell tinted by that cell's colour.
  - **Halftone** and **Pixelate**: square cells on a flattened palette.
  - **Invert**: a sweeping solarization threshold via a 256-entry LUT (32 cached steps, 0.2 ms).
  - Scene average for auto-exposure: "Sampling the 1x1 mip with `textureLod`".
  - Effects cost **2–15 ms each at 720p** in WebGL. They chain as `(img, amount, cache) -> img`.

  — [GitHub andres-ferreiro/pinch-vision](https://github.com/andres-ferreiro/pinch-vision)
- neempata TD: Lookup TOP with an animated noise palette ("Every pixel inside the panel is replaced by a colour chosen by its brightness") inside a Corner Pin TOP — [GitHub neempata](https://github.com/neempata/Noise-Portal-Handtracking-Touchdesigner)
- Eureka: the mirror sheet is an inverted mirror, `clamp(283 − 0.56 × background)`. Glass-box faces each get a different treatment:
  - Top: inverted blue gradient + horizontal glitch
  - Front: riso print (two colours, channel-offset fringes, ordered dither)
  - Back: hard-threshold duotone
  - Bottom: point cloud using local contrast as pseudo-depth
  - Left/right: quadtree mosaic and halftone

  — [GitHub Eureka0w0v0/manual-tracking](https://github.com/Eureka0w0v0/manual-tracking)
- hand-filter-window: `thermal`, `cartoon`, `edges`, `negative`, `pop-color` as `frame -> frame` functions, mask compositing in `compositor.py`, and a supersampling flag for "crisper edges" — [GitHub Ali533-blip/hand-filter-window](https://github.com/Ali533-blip/hand-filter-window)

**GPU: stencil and portal masking in Three.js**
- Portal technique: the aperture mesh renders only to the **stencil buffer** (no opaque pass), and a later pass fills the content where the stencil is set. Portals can be any shape, and shaders can `discard` for animated outlines. Render portals after other objects (`renderOrder`); depth test prevents stencil writes behind nearer objects — [three.js PR #12033](https://github.com/mrdoob/three.js/pull/12033); [three.js forum: Portal rendering with stencil buffer](https://discourse.threejs.org/t/portal-rendering-with-stencil-buffer/22425) (from search summaries)
- Three.js `Material` stencil properties: `stencilWrite` (default false), `stencilRef`, `stencilFunc` (default Always), `stencilFuncMask`, `stencilWriteMask`, `stencilFail`, `stencilZFail`, `stencilZPass`, plus `colorWrite` and `depthWrite` — [three.js src/materials/Material.js](https://github.com/mrdoob/three.js/blob/dev/src/materials/Material.js)
- `WebGLRenderer` constructor default is **`stencil = false`**, so pass `{ stencil: true }` to use stencil masks — [three.js src/renderers/WebGLRenderer.js](https://github.com/mrdoob/three.js/blob/dev/src/renderers/WebGLRenderer.js)
- `@react-three/drei` provides stencil `Mask` helpers — [thefrontdev.co.uk](https://www.thefrontdev.co.uk/immersive-portals-in-three-and-r3f-unleashing-the-power-of-stencil-masks-from-drei/)

**Translucent 3D cubes**
- Three.js sorts transparent *objects*, but a mesh's triangles are drawn in geometry order: "for individual triangles sorting would be extremely slow". So with depth writes on, back faces of a transparent cube randomly disappear.
- For convex objects, add the mesh twice: once with `side: THREE.BackSide`, then with `side: THREE.FrontSide`. This relies on stable sort order.
- `alphaTest` suits cut-out textures.

— [threejsfundamentals: transparency](https://github.com/gfxfundamentals/threejsfundamentals/blob/master/threejs/lessons/threejs-transparency.md)

### Inferences
- **OpenCV "frame filter" core (per frame):**
  ```python
  quad = order(corners).astype(np.int32)             # 4x2 pixel coords
  x,y,w,h = cv2.boundingRect(quad)                    # clip to frame bounds
  roi = frame[y:y+h, x:x+w]
  fx  = effect(roi)                                   # e.g. cv2.applyColorMap(cv2.cvtColor(roi,cv2.COLOR_BGR2GRAY), cv2.COLORMAP_INFERNO)
  m   = np.zeros((h,w), np.uint8); cv2.fillConvexPoly(m, quad-[x,y], 255, cv2.LINE_AA)  # fillPoly if it may self-intersect
  m   = cv2.GaussianBlur(m, (0,0), 2)[...,None]/255.  # feathered edge (optional)
  frame[y:y+h, x:x+w] = (fx*m + roi*(1-m)).astype(np.uint8)
  cv2.polylines(frame, [quad], True, (255,255,255), 2, cv2.LINE_AA)  # the white frame outline
  ```
  Filtering only the bounding-rect crop keeps cost proportional to frame size. Draw the mask at 2× (`shift` fractional bits or supersampling) for smoother edges, as the repos' `--ss` flag does.
- **Filter menu (CPU):**
  - thermal = `applyColorMap(gray, INFERNO/JET/TURBO)`
  - invert = `255 - roi` or a LUT
  - pixelate = `resize(down, INTER_LINEAR)` → `resize(up, INTER_NEAREST)`
  - edges = `Canny` or Sobel magnitude → colourize
  - cartoon = `bilateralFilter` + adaptive-threshold edges
  - posterize/duotone = LUT
  - chromatic glitch = per-channel `np.roll` on horizontal bands
- **Texture/perspective mode:** `H = cv2.getPerspectiveTransform(src_rect, quad)` → `warpPerspective(tex, H, (W,H))` → mask-composite. To show the region *rectified* (a "zoom through the frame"), use `warpPerspective(frame, inv(H), ...)`.
- **GPU shortest path (Three.js/WebGL):** build a 4-vertex `BufferGeometry` from the quad in NDC with an orthographic camera. Give it a `ShaderMaterial` whose fragment shader samples the webcam `VideoTexture` at `gl_FragCoord.xy / resolution` (screen-space UV, mirrored if needed) and applies the effect. Only pixels covered by the quad are affected, so no mask is needed.
  - For arbitrary polygons, triangulate with `ShapeUtils.triangulateShape`, or use a full-screen pass with a point-in-polygon test: for a convex quad, all four edge cross products have the same sign; for general polygons, use the crossing-number loop over a uniform vertex array.
  - Use the stencil approach when the "inside" must show a whole separate rendered scene (portal) rather than a filtered camera image.
- **Translucent cube in OpenCV (painter's algorithm):**
  1. Project the 8 vertices and compute each face's mean camera-space Z.
  2. Sort faces far→near.
  3. For each face, `fillConvexPoly` onto an overlay, then `addWeighted` (or mask-blend a per-face effect, as in Eureka's glass box).
  4. Back-face test: sign of the 2D cross product of two projected edges (winding). Draw back faces dimmer or skip them.
- **Translucent cube in Three.js:** `transparent:true, depthWrite:false`, plus the BackSide-then-FrontSide double-mesh trick. Or render each face as its own mesh so object sorting applies. Edges can use `EdgesGeometry` + `LineSegments` for the "neon wireframe" look.
- **Per-face effect on a box:** treat each visible projected face as its own quad and reuse the 2D frame-filter pipeline with a different effect per face.

### Gaps
- The Medium "Creating portals in three.js" article returned 403, so stencil specifics are cited from the three.js PR, forum summaries and source code.
- No benchmark comparing CPU `fillPoly`+composite with a GPU shader for this use case was found; only pinch-vision's 2–15 ms/effect WebGL figure is available.

---

## 6. Face-related effects for later: face mesh UV mapping, blendshapes, detection vs landmarking

### Takeaway
MediaPipe Face Landmarker returns **478 landmarks** (468 mesh points + 10 iris), optional **52 blendshape scores** and an optional **4×4 facial transformation matrix**. Face-paint filters are built by using the landmarks as vertex positions, with UVs and triangles taken from Google's canonical face model. A September 2026 Codrops article gives a full Three.js walkthrough.

### Cited Findings
- Face Landmarker outputs 478 3D landmarks, 52 blendshape scores ("coefficients representing facial different expressions") and transformation matrices "for effects rendering".
  - Defaults: `num_faces` 1, `output_face_blendshapes` False, `output_facial_transformation_matrixes` False, confidences 0.5.
  - The bundle is BlazeFace short-range detector (192×192) → Face Mesh V2 (256×256) → blendshape model (input 1×146×2), all float16.

  — [Face Landmarker guide](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker)
- 468 surface points + 10 iris points (5 per eye) — [webai.show FaceLandmarker](https://webai.show/models/face-landmarker/) (search snippet); [MediaPipe Face Mesh wiki](https://github.com/google-ai-edge/mediapipe/wiki/MediaPipe-Face-Mesh)
- Canonical face model:
  - It follows the 468-landmark topology, in centimetres.
  - The face pose transformation matrix maps canonical → runtime landmarks.
  - A face mesh uses runtime metric landmarks as XYZ, with **UVs and triangle topology inherited from the canonical model**.
  - The Effect Renderer's face-mesh mode stretches a texture over the mesh to emulate face paint.

  — [MediaPipe Face Mesh docs](https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/face_mesh.md); [Google Developers Blog: 3D Face Transform](https://developers.googleblog.com/mediapipe-3d-face-transform/)
- Codrops (Marek Jóźwiak, **Sep 6, 2026**): the build steps are:
  1. Parse `canonical_face_model.obj` face records (`f 174/43` = vertex 174 uses UV 43) into a Float32Array reordered to the 468 indices, with `1.0 - v` flip.
  2. Use **880 triangles / 2,640 indices** from TF.js `triangulation.js`, rather than the OBJ's 898 faces.
  3. Use only the first 468 of the 478 landmarks for the surface.
  4. Allocate buffers once with `DynamicDrawUsage` and recompute normals every frame.
  5. Match CSS `object-cover` cropping and mirroring.
  6. Keep hot landmark data outside the UI framework's reactive graph.

  — [Codrops 2026 face mask](https://tympanus.net/codrops/2026/09/06/building-a-real-time-3d-face-mask-with-mediapipe-threlte-and-three-js/)
- An open GitHub issue reports "The canonical_face_model.obj file is outdated" — [Issue #5760](https://github.com/google-ai-edge/mediapipe/issues/5760) (title only; not fetched)

### Inferences
- **Detection vs landmarking:** detection (BlazeFace) gives a box and coarse position and is enough for "sticker follows face" or cropping. Landmarking (Face Mesh) is needed for warps, masks, UV face paint, eye/mouth effects and occlusion.
- Blendshapes (e.g. jaw open, eye blink, per the ARKit-like set) are a clean trigger source for face-driven state machines. Combine them with the same hysteresis and dwell logic as in §4.
- To mix hands and face (e.g. a frame that stylizes only the face), run HandLandmarker and FaceLandmarker in the same loop and intersect the finger quad mask with the face-mesh convex hull mask. This is what "Finger Frame AI" styles appear to target.

### Gaps
- The full list of the 52 blendshape names was not fetched in this pass.
- The specifics of the canonical OBJ "outdated" issue were not reviewed.

---

## 7. Learning resources: courses, books, channels and shader references

### Takeaway
For this specific effect family, the most directly useful resources are:
- Torin Blankensmith's MediaPipe-TD plugin and 2025 Hand Tracking Master Class (TD route).
- The open-source Python repos above (Eureka manual-tracking, pinch-vision, hand-filter-window) as annotated code.
- Codrops' Three.js + MediaPipe articles (2024 hand controller, 2026 face mask).
- The 1€ paper for smoothing.
- OpenCV and LearnOpenCV homography material.
- The Book of Shaders for GPU effects.
- The Coding Train's ml5.js handPose videos for beginners.

### Cited Findings
- Torin Blankensmith's Hand Tracking Master Class (3 parts, Feb 2025, project files on Patreon), plugin repo and older tutorials — [Derivative](https://derivative.ca/community-post/tutorial/hand-tracking-master-class-touchdesigner-mediapipe/71352); [GitHub](https://github.com/torinmb/mediapipe-touchdesigner); [Derivative (Droste/PiP, Jan 2024)](https://derivative.ca/community-post/tutorial/picture-picture-hand-tracking-effect-touchdesigner-tutorial/68828)
- LucieMrc/MediaPipe_TD_EN is an English guide to using MediaPipe in TouchDesigner for webcam interactions — [GitHub](https://github.com/LucieMrc/MediaPipe_TD_EN)
- Bileam Tschepe (elekktronaut) runs TD tutorials on YouTube, Patreon and Vimeo, including an "Instagram workflow" tutorial — [YouTube](https://www.youtube.com/c/bileamtschepe); [Patreon](https://www.patreon.com/cw/elekktronaut); [elekktronaut Instagram workflow](https://www.elekktronaut.com/tutorials/instagram-workflow)
- **The Coding Train** "Hand Pose Detection with ml5.js" (Oct 2024) covers the 21 keypoints, multi-hand and left/right, painting and thumbs-up detection — [The Coding Train](https://thecodingtrain.com/tracks/ml5js-beginners-guide/ml5/hand-pose/); [ml5.js tutorial](https://ml5js.org/tutorials/coding-train-hand-detection/)
- Codrops tutorials: "Creating a 3D Hand Controller Using a Webcam with MediaPipe and Three.js" (Caio Bassetti, Oct 2024) and "Building a Real-Time 3D Face Mask with MediaPipe, Threlte and Three.js" (Sep 2026) — [Codrops 2024](https://tympanus.net/codrops/2024/10/24/creating-a-3d-hand-controller-using-a-webcam-with-mediapipe-and-three-js/); [Codrops 2026](https://tympanus.net/codrops/2026/09/06/building-a-real-time-3d-face-mask-with-mediapipe-threlte-and-three-js/)
- Homography and warping: the OpenCV "Basic concepts of the homography explained with code" tutorial and LearnOpenCV's homography examples (Python/C++) — [OpenCV tutorial](https://docs.opencv.org/4.x/d9/dab/tutorial_homography.html); [LearnOpenCV](https://learnopencv.com/homography-examples-using-opencv-python-c/)
- Books:
  - *Learning OpenCV 3* (Kaehler & Bradski, O'Reilly, 2016; C++) — [O'Reilly](https://www.oreilly.com/library/view/learning-opencv-3/9781491937983/)
  - *Learning OpenCV 4 Computer Vision with Python 3, 3rd ed.* is available on O'Reilly's platform — [O'Reilly](https://www.oreilly.com/library/view/learning-opencv-4/9781789531619/)
- *The Book of Shaders* by Patricio Gonzalez Vivo and Jen Lowe is free online with interactive chapters, e.g. Shaping Functions (ch. 5) and Shapes (ch. 7) — [thebookofshaders.com](https://thebookofshaders.com/); [ch. 5](https://thebookofshaders.com/05/); [ch. 7](https://thebookofshaders.com/07/)
- 1€ filter paper, site and implementations — [gery.casiez.net/1euro](https://gery.casiez.net/1euro/); [paper PDF](https://gery.casiez.net/publications/CHI2012-casiez.pdf); [Jaan Tollander's explainer](https://jaantollander.com/post/noise-filtering-using-one-euro-filter/)
- MediaPipe official guides: Hand Landmarker, Gesture Recognizer, Model Maker customization, Face Landmarker — [Hand](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker); [Gesture](https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer); [Customization](https://developers.google.com/edge/mediapipe/solutions/customization/gesture_recognizer); [Face](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker)
- Snap and TikTok no-code docs (if a native in-app lens is ever wanted) — [Lens Studio 3D Hand Tracking](https://developers.snap.com/lens-studio/features/ar-tracking/hand/hand-tracking-templates/3d-hand-tracking); [Effect House Hand Tracker](https://effecthouse.tiktok.com/learn/guides/workspace/objects/ar-tracking/hand-tracker)

### Inferences
- **Suggested learning path for code reproduction:**
  1. MediaPipe Tasks HandLandmarker in Python (2 hands, VIDEO/LIVE_STREAM mode).
  2. Read the Eureka `manual-tracking` and `pinch-vision` sources for production-grade filtering and gesture code.
  3. OpenCV masks and homography (LearnOpenCV).
  4. Port to the browser with `@mediapipe/tasks-vision` + Three.js, with effects as fragment shaders (Book of Shaders).
  5. Add 1€ smoothing and the §4 state machine.
- Because most pre-2025 YouTube tutorials use `mp.solutions.hands`, favour 2025–2026 material or translate old code to the Tasks API.

### Gaps
- No O'Reilly C++ "Learning OpenCV 4" by Kaehler & Bradski was found; the latest Kaehler/Bradski edition found is *Learning OpenCV 3* (2016). The fetched snippet did not confirm the authors of the Python "Learning OpenCV 4" title.
- Shadertoy was not researched in this pass (no source fetched), although it is a common source of GLSL effect snippets.
- No paid course dedicated specifically to "finger-frame AR effects" was found beyond Torin's Patreon master class.
