# Web/JavaScript (browser) stack for real-time webcam hand/face tracking, gesture recognition and 3D AR overlays (state as of 2026-09-27)

Scope: browser-only, code-first stack for a webcam demo where fingers define shapes (a rectangle between both hands' thumb and index tips filled with a shader/filter; a cube/parallelepiped defined by 3 fingertips), plus face mesh and gesture recognition. Target: macOS on Apple Silicon, current Chrome and Safari.

Version numbers below come from the npm registry, queried on 2026-09-27 (`npm view <pkg> version time dist-tags`). They are cited to the npm package pages.

---

## 1. MediaPipe Tasks Vision for Web (@mediapipe/tasks-vision): tasks, versions, GPU delegate, outputs, FPS, legacy packages

### Takeaway
`@mediapipe/tasks-vision` is the current, maintained Google API. It reached **1.0.0 on 2026-07-28** (latest 1.0.1, published 2026-07-31; nightly 1.1.0-rc.20260924). It provides HandLandmarker (21 landmarks per hand plus metric world landmarks and handedness), GestureRecognizer (7 built-in gestures plus custom), FaceLandmarker (478 landmarks, 52 blendshapes, 4x4 transformation matrix), PoseLandmarker, HolisticLandmarker and ImageSegmenter. On the web, "GPU" still means **WebGL2, not WebGPU**: `delegate` only accepts `"CPU" | "GPU"`. The legacy `@mediapipe/hands`, `face_mesh` and `holistic` packages have been unsupported since 2023-03-01 and should not be used for new work.

### Cited Findings
**Versions and release status**
- npm `@mediapipe/tasks-vision`: latest **1.0.1**, with nightly `1.1.0-rc.20260924`. Release history: 0.10.21 (2025-02-06), then 0.10.32 (2026-01-22), 0.10.33–0.10.35 (Mar–Apr 2026), **1.0.0 (2026-07-28)**, 1.0.1 (2026-07-31). The package has 0 dependencies and ships `vision_bundle.mjs/.cjs/.js`, `vision.d.ts`, and `wasm/vision_wasm_internal.wasm` (~11.7 MB), with SIMD, no-SIMD and "module" WASM variants — [npm @mediapipe/tasks-vision](https://www.npmjs.com/package/@mediapipe/tasks-vision); [jsDelivr file list 1.0.1](https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/)
- MediaPipe **v1.0.0** GitHub release (published 2026-07-28). Web-relevant items: "Add IIFE bundles for web task modules.", "Cache running mode in VisionTaskRunner.", "Store wgpu::Instance in WebGpuService.", "Add gpu_postprocessing option for TensorsToSegmentationCalculator.", "Makes InteractiveSegmenter a legacy one, in preparation of releasing v2 / new interface.", "Remove MacOS prebuilts". None of the release bullets change the HandLandmarker, GestureRecognizer or FaceLandmarker web APIs — [MediaPipe v1.0.0 release](https://github.com/google-ai-edge/mediapipe/releases/tag/v1.0.0). Note: one WebFetch summary gave the date as "July 28, 2025". The GitHub API (`published_at 2026-07-28`) and npm (`1.0.0: 2026-07-28`) both say 2026.
- Docs moved from ai.google.dev/edge/mediapipe to **developers.google.com/edge/mediapipe** (301 redirect). The Hand, Face and Gesture web guides were last updated 2026-08-17 — [Hand Landmarker web guide](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/web_js)
- The vision tasks available on Web are Face detection, Face landmark detection, Gesture recognition, Hand landmark detection, Holistic landmark detection, Image classification, Image embedding, Image segmentation, Interactive segmentation, Object detection and Pose landmark detection — [MediaPipe Solutions guide (updated 2026-08-18)](https://developers.google.com/edge/mediapipe/solutions/guide)
- The 1.0.1 type definitions export these classes: FaceDetector, FaceLandmarker, GestureRecognizer, HandLandmarker, HolisticLandmarker, ImageClassifier, ImageEmbedder, ImageSegmenter, InteractiveSegmenter, ObjectDetector and PoseLandmarker — [vision.d.ts 1.0.1](https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/vision.d.ts)

**API surface (from vision.d.ts 1.0.1)**
- `BaseOptions.delegate?: "CPU" | "GPU"`. No WebGPU option exists — [vision.d.ts](https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/vision.d.ts)
- Video methods:
  - `HandLandmarker.detectForVideo(videoFrame: ImageSource, timestamp: number, imageProcessingOptions?) : HandLandmarkerResult`
  - `GestureRecognizer.recognizeForVideo(...)`
  - `FaceLandmarker.detectForVideo(...)`
  - PoseLandmarker, HolisticLandmarker and `ImageSegmenter.segmentForVideo` also have **callback overloads**, for example `segmentForVideo(frame, ts, callback)`.
  - `ImageSource = TexImageSource`, so it accepts HTMLVideoElement, VideoFrame, ImageBitmap, OffscreenCanvas and similar.
  — [vision.d.ts](https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/vision.d.ts)
- `HandLandmarkerResult` has `landmarks: NormalizedLandmark[][]`, `worldLandmarks: Landmark[][]` and `handedness: Category[][]`. `handednesses` is marked `@deprecated Use .handedness instead` — [vision.d.ts](https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/vision.d.ts)
- `FaceLandmarkerResult` has `faceLandmarks: NormalizedLandmark[][]`, `faceBlendshapes: Classifications[]` and `facialTransformationMatrixes: Matrix[]`. `Matrix` is `{rows, columns, data: number[]}`, stored as a flattened array — [vision.d.ts](https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/vision.d.ts)
- Tasks accept an optional `canvas?: HTMLCanvasElement | OffscreenCanvas`. The GPU path "require[s] WebGL2 support". With the GPU delegate, `DrawingUtils` takes a `WebGL2RenderingContext` that must come from the task's canvas — [vision.d.ts](https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/vision.d.ts)

**HandLandmarker**
- Options: `numHands` (default 1), and `minHandDetectionConfidence`, `minHandPresenceConfidence`, `minTrackingConfidence` (default 0.5 each). Set `runningMode` to video with `setOptions({ runningMode: "video" })`. WASM is loaded through `FilesetResolver.forVisionTasks(<cdn>/wasm)`. The official demo is on StackBlitz — [Hand Landmarker web guide](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/web_js)
- The model bundle is a palm detection model plus a hand-landmark model producing 21 knuckle keypoints. It "only re-triggers the palm detection model if the hand landmarks model no longer identifies the presence of hands". It was trained on ~30K real images plus synthetic hands. Model input sizes are 192x192 and 224x224. Published latency on **Pixel 6** is 17.12 ms CPU and 12.27 ms GPU; there are no Mac or browser figures — [Hand Landmarker overview](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker)
- Coordinate semantics (same model family, from the legacy docs):
  - x and y are normalized to [0,1] by image width and height.
  - "`z` represents the landmark depth with the depth at the wrist being the origin, and the smaller the value the closer the landmark is to the camera. The magnitude of `z` uses roughly the same scale as `x`."
  - World landmarks are "real-world 3D coordinates in meters with the origin at the hand's approximate geometric center."
  — [MediaPipe hands.md (legacy doc)](https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/hands.md)

**GestureRecognizer**
- Built-in ("canned") gestures: `None, Closed_Fist, Open_Palm, Pointing_Up, Thumb_Down, Thumb_Up, Victory, ILoveYou`. Options include `numHands`, `cannedGesturesClassifierOptions` and `customGesturesClassifierOptions`. Each result contains handedness, gestures, 21 landmarks and world landmarks. The model file is `gesture_recognizer.task`. Custom gestures are trained with MediaPipe Model Maker (Python) — [Gesture Recognizer web guide](https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer/web_js)
- There is an old open issue titled "Gesture Recognizer unable to use GPU inference" (#4327). Its current status was not verified — [issue #4327](https://github.com/google-ai-edge/mediapipe/issues/4327)

**FaceLandmarker**
- Options: `numFaces`, `outputFaceBlendshapes` and `outputFacialTransformationMatrixes` (all default false/1), plus confidence thresholds. Outputs are **478 landmarks**, **52 blendshapes** and 4x4 transformation matrices "for applying effects". The docs say `detectForVideo()` "run[s] synchronously and block[s] the user interface thread" and recommend web workers — [Face Landmarker web guide](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/web_js)
- The default virtual camera used to compute the face transformation matrix is a perspective camera with `vertical_fov_degrees = 63`, `near = 1.0 (1 cm)` and `far = 10000 (100 m)`. The matrix is in centimetre units in that camera space — [face_geometry_from_landmarks_graph.cc](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/cc/vision/face_geometry/face_geometry_from_landmarks_graph.cc)

**GPU delegate = WebGL2 (no WebGPU for vision)**
- Issue #5826, "WebGPU support for Vision Tasks", opened 2025-01-15, is **still open**. A Google engineer wrote on 2025-01-16: "Our Vision tasks do use WebGL at the moment, as our WebGPU support is currently focused on our LLM Inference API." An Aug 2026 comment reports "mixed results when we compare CPU vs WebGL performance"; CPU beats WebGL on some budget phones — [issue #5826](https://github.com/google-ai-edge/mediapipe/issues/5826)
- Performance issue #5377 (open): profiling shows the standard WASM spends >10 ms in `glReadPixels` even with the CPU backend, because input goes through a WebGL texture. Google acknowledged it on 2026-08-19 and "escalated … to our team to investigate" — [issue #5377](https://github.com/google-ai-edge/mediapipe/issues/5377)
- Other open issues with the Web GPU delegate:
  - ImageSegmenter GPU "GL handle tables grow unbounded during continuous segmentForVideo" (opened 2026-08-31) — [issue #6352](https://github.com/google-ai-edge/mediapipe/issues/6352)
  - Scrambled categories on **iOS** Safari with the GPU delegate for selfie_multiclass — [issue #6142](https://github.com/google-ai-edge/mediapipe/issues/6142)
  - ImageSegmenter aborts when WebGL float-texture extensions are missing — [issue #6296](https://github.com/google-ai-edge/mediapipe/issues/6296)

**FPS on Mac (browser)**
- The only concrete Mac browser measurement found comes from a third-party project (0 stars) benchmarking against stock MediaPipe on a MacBook Pro M1 Max with Chrome 148, macOS 26.2 and a 640x480 webcam. Stock MediaPipe HandLandmarker took **~20 ms per frame** for 1 or 2 hands, compared with ~5 ms for 1 hand and ~8 ms for 2 hands on the author's WebGPU/ONNX reimplementation. Face: ~15 ms for MediaPipe vs ~13 ms. Treat this as a single-source, self-reported benchmark — [Sonified/webgpu-vision README](https://github.com/Sonified/webgpu-vision)

**Legacy packages**
- "We have ended support for the MediaPipe Legacy Solutions listed below as of **March 1, 2023**." Face Mesh became Face landmark detection, Hands became Hand landmark detection, Pose became Pose landmark detection, and Holistic became Holistic landmark detection. Iris was folded into Face landmark detection, and Selfie/Hair segmentation into Image segmentation — [MediaPipe Solutions guide](https://developers.google.com/edge/mediapipe/solutions/guide)
- Frozen npm legacy packages: `@mediapipe/hands` 0.4.1675469240 (build timestamp from Feb 2023), `@mediapipe/face_mesh` 0.4.1633559619 (Oct 2021 build), `@mediapipe/holistic` 0.5.1675471629 and `@mediapipe/camera_utils` 0.3.1675466862. None has an npm `deprecated` flag. Their READMEs still point to the retired google.github.io/mediapipe site — [npm @mediapipe/hands](https://www.npmjs.com/package/@mediapipe/hands); [npm @mediapipe/face_mesh](https://www.npmjs.com/package/@mediapipe/face_mesh)

**Official samples**
- New official repo **google-ai-edge/mediapipe-samples-web** (created 2026-03-30, active as of 2026-09-28). It has Vite/TypeScript demos for every task (`src/tasks/*.ts`) and a **Web Worker per task** (`src/workers/*.worker.ts`). Live demos: https://google-ai-edge.github.io/mediapipe-samples-web/ — [mediapipe-samples-web](https://github.com/google-ai-edge/mediapipe-samples-web)
- In those samples:
  - The main thread runs a `requestAnimationFrame` loop that calls `createImageBitmap(video)` and transfers the bitmap to a module worker.
  - The worker creates the task with `delegate: 'GPU'` and, if GPU init fails, **automatically falls back to CPU**.
  - Failure diagnosis checks `OffscreenCanvas` and `getContext('webgl2')`.
  — [base-worker.ts](https://github.com/google-ai-edge/mediapipe-samples-web/blob/main/src/workers/base-worker.ts); [base-vision-task.ts](https://github.com/google-ai-edge/mediapipe-samples-web/blob/main/src/components/base-vision-task.ts); [hand-landmarker.worker.ts](https://github.com/google-ai-edge/mediapipe-samples-web/blob/main/src/workers/hand-landmarker.worker.ts)
- An older issue (#5292, closed 2024-06 as stale) reported that tasks-vision in workers on iOS 17 tried `document.createElement("canvas")`. Google said it had been resolved — [issue #5292](https://github.com/google-ai-edge/mediapipe/issues/5292)

### Inferences
- For the "fingers form shapes" demo, **HandLandmarker with `numHands: 2` is the core**. Useful landmark indices: 4 = thumb tip, 8 = index tip, 12 = middle tip, 0 = wrist. GestureRecognizer returns the same landmarks plus gesture labels. Use GestureRecognizer instead of HandLandmarker when you also want gesture labels, so you don't run two hand models.
- The rectangle quad can come directly from normalized `landmarks` (2D): left thumb, left index, right index, right thumb. The 3-finger cube can use `worldLandmarks` for metric, hand-relative 3D edge vectors. Combine that with a 2D anchor, or a depth estimate from apparent hand size, to place it in camera space (see Q3).
- Pin exact versions of the npm package and the WASM CDN path, e.g. `@mediapipe/tasks-vision@1.0.1/wasm`. A mismatch between the JS bundle and the WASM version is a common failure mode, and the 1.0 major bump makes this more likely.
- Expect roughly 30–50 inferences/s for hands on an M-series Mac in Chrome with the WebGL delegate. This is inferred from the ~20 ms/frame figure above, which is not an official benchmark. Running it in a worker keeps rendering at display rate even when inference is slower.
- FaceLandmarker's `facialTransformationMatrixes` can be applied directly to a Three.js `Object3D.matrix` if the Three.js camera uses FOV 63°, near 1 and far 10000, with units in cm. This comes from the default environment above; it is not verified here in running code.

### Gaps
- No official Google FPS or latency numbers for tasks-vision on macOS Chrome or Safari; only the Pixel 6 numbers exist.
- No official statement or roadmap for a WebGPU delegate in vision tasks after the 2025-01 comment.
- It is unclear what "Remove MacOS prebuilts" in v1.0.0 refers to (probably native/Python artifacts). It was not verified whether this affects anything web-side (likely not).
- Mac-Safari-specific GPU-delegate bugs for HandLandmarker/FaceLandmarker were not verified; the issues found were about the iOS segmenter.
- The handedness convention (whether the model assumes a mirrored/selfie image) was not verified for tasks-vision 1.0.

---

## 2. TensorFlow.js models, LiteRT.js, ONNX Runtime Web, transformers.js: maintenance and runtimes

### Takeaway
TensorFlow.js and tfjs-models (`hand-pose-detection` 2.0.1, `face-landmarks-detection` 1.0.6) are effectively in maintenance mode. The last substantive model releases were in Oct 2023 and Oct 2024, and tfjs 4.22.0 dates from Jan 2025. Google's new web runtime is **LiteRT.js** (`@litertjs/core`, announced 2026-07-09, WebGPU/XNNPACK/WebNN). For custom or alternative vision models, ONNX Runtime Web 1.30 (WebGPU EP) and transformers.js v4 (WebGPU runtime, 4.0.0 released 2026-03-30) are active options. For hands and face specifically, MediaPipe Tasks remains the turnkey path.

### Cited Findings
- npm `@tensorflow/tfjs` latest **4.22.0** (published 2025-01-08; `next` 4.23.0-rc.0). `@tensorflow/tfjs-backend-webgpu` is also 4.22.0 — [npm @tensorflow/tfjs](https://www.npmjs.com/package/@tensorflow/tfjs)
- npm `@tensorflow-models/hand-pose-detection` latest **2.0.1** (last modified 2023-10-17). `@tensorflow-models/face-landmarks-detection` latest **1.0.6** (2024-10-10) — [npm hand-pose-detection](https://www.npmjs.com/package/@tensorflow-models/hand-pose-detection); [npm face-landmarks-detection](https://www.npmjs.com/package/@tensorflow-models/face-landmarks-detection)
- Recent commit history on `tensorflow/tfjs`: 2026-04-06 "chore: Migrate gsutil usage to gcloud storage", then nothing between 2025-06 and 2026-04. On `tensorflow/tfjs-models`: 2026-03-28 gsutil migration chore, the previous commit 2024-10-24. Neither repo is archived — [tfjs commits](https://github.com/tensorflow/tfjs/commits/master); [tfjs-models commits](https://github.com/tensorflow/tfjs-models/commits/master)
- The tfjs-models `hand-pose-detection` and `face-landmarks-detection` packages wrap the MediaPipe Hands and FaceMesh models. They support two runtimes, `"tfjs"` (TF.js kernels, WebGL or WebGPU backend) and `"mediapipe"` (loads the **legacy** `@mediapipe/hands` / `@mediapipe/face_mesh` solution from a `solutionPath`, default `https://cdn.jsdelivr.net/npm/@mediapipe/hands`). This is visible in ml5's wrapper — [ml5 HandPose source](https://github.com/ml5js/ml5-next-gen/blob/main/src/HandPose/index.js); [ml5 FaceMesh source](https://github.com/ml5js/ml5-next-gen/blob/main/src/FaceMesh/index.js)
- **LiteRT.js** was announced on **2026-07-09**:
  - It is "a JavaScript binding of LiteRT for running AI directly inside the web browser".
  - Backends: CPU (XNNPACK), GPU (ML Drift via WebGPU), NPU (WebNN, experimental in Chrome/Edge).
  - It is described as "a powerful evolution from TensorFlow.js for executing .tflite models" and can complement existing TF.js pipelines.
  - Claims: "outperforming other web runtimes by up to 3x", and 5–60x GPU/NPU speedups vs CPU. Tests were run on a MacBook Pro M4 with Safari.
  - npm `@litertjs/core`, model format `.tflite`. The post says nothing about TF.js maintenance status.
  — [Google Developers Blog: LiteRT.js](https://developers.googleblog.com/en/litertjs-googles-high-performance-web-ai-inference/); [LiteRT/litert/js](https://github.com/google-ai-edge/LiteRT/tree/main/litert/js)
- npm `@litertjs/core` latest **2.5.3** (2026-07-17) — [npm @litertjs/core](https://www.npmjs.com/package/@litertjs/core)
- ONNX Runtime Web latest **1.30.0** (2026-09-14):
  - Enable WebGPU by importing `onnxruntime-web/webgpu` (or `ort.webgpu.min.js`) and passing `executionProviders: ['webgpu']`.
  - Keep data on the GPU with `ort.Tensor.fromGpuBuffer(...)` and `preferredOutputLocation: 'gpu-buffer'`.
  - Unsupported ops fall back to CPU. Graph capture works for static-shape models.
  - The docs page still says Safari WebGPU is "Technology Preview builds only". That is **outdated**: Safari 26 shipped WebGPU in Sept 2025 (see Q5).
  — [ORT WebGPU EP docs](https://onnxruntime.ai/docs/tutorials/web/ep-webgpu.html); [npm onnxruntime-web](https://www.npmjs.com/package/onnxruntime-web)
- transformers.js **v4** (npm `@huggingface/transformers` 4.0.0 published 2026-03-30; latest 4.3.0 on 2026-09-16) adopted "a new WebGPU Runtime, completely rewritten in C++" together with the ONNX Runtime team, tested across ~200 architectures. It also runs WebGPU in Node, Bun and Deno — [HF blog: Transformers.js v4](https://huggingface.co/blog/transformersjs-v4); [release 4.0.0](https://github.com/huggingface/transformers.js/releases/tag/4.0.0); [npm](https://www.npmjs.com/package/@huggingface/transformers)
- Proof of concept: a third-party project rebuilt the MediaPipe hand/face pipeline on **ONNX Runtime Web + custom WGSL** compute shaders, claiming zero CPU readback. It found that the face-landmark model's 69 PReLU ops are unsupported by ORT's WebGPU EP; decomposing them gave "12x speedup (9fps to 77fps)" — [Sonified/webgpu-vision](https://github.com/Sonified/webgpu-vision)

### Inferences
- Do not start a new project on `@tensorflow-models/*` in 2026. They pin tfjs 4.x and legacy MediaPipe solutions and get no model updates. Use them only via ml5 for quick creative-coding sketches.
- LiteRT.js is the likely future of Google's web ML runtime. However, MediaPipe Tasks Web still uses its own WASM + WebGL path, and nothing found says Tasks now runs on LiteRT.js. For hand, face and gesture work today, tasks-vision is still simpler because it includes pre- and post-processing, tracking and ROI logic.
- ORT Web or transformers.js make sense only for extra models, e.g. depth estimation (Depth Anything) for occlusion, segmentation, or a custom gesture classifier. For hands and face they mean reimplementing MediaPipe's multi-stage pipeline.

### Gaps
- No official Google statement found declaring TF.js deprecated or in maintenance mode; the maintenance-mode conclusion comes from commit and release activity.
- No first-party benchmark of LiteRT.js running MediaPipe hand or face `.tflite` models vs tasks-vision on a Mac.
- It was not verified whether the MediaPipe `.task` bundles, which are zip archives of `.tflite` files, load directly in LiteRT.js.

---

## 3. 3D rendering over the webcam: Three.js (WebGLRenderer vs WebGPURenderer/TSL), Babylon.js, R3F, raw WebGL2/WebGPU; video background, landmark unprojection, masked filters

### Takeaway
**Three.js r186 (`three@0.186.1`, 2026-09-24)** is the default choice. The three.js manual still calls WebGPURenderer "experimental", although it auto-falls back to WebGL2 and uses TSL (JS-authored shaders compiled to WGSL or GLSL). It **does not support `ShaderMaterial`, `onBeforeCompile` or `EffectComposer`**, and post-processing goes through `RenderPipeline`. For a quick demo with custom GLSL filters and the pmndrs `postprocessing` library, WebGLRenderer is the lowest-friction path. WebGPURenderer + TSL is the forward-looking path. Three.js ships webcam, video-frame, stencil-clipping and masking examples for both renderers.

### Cited Findings
**Versions**
- npm `three` latest **0.186.1** (2026-09-24). r186.0 came out 2026-09-08 and r185 on 2026-06-25 — [npm three](https://www.npmjs.com/package/three)
- `@babylonjs/core` latest **9.28.0** (2026-09-24). Babylon.js **9.0.0** was released on 2026-03-26 — [npm @babylonjs/core](https://www.npmjs.com/package/@babylonjs/core); [Babylon.js 9.0.0 release](https://github.com/BabylonJS/Babylon.js/releases/tag/9.0.0)
- `@react-three/fiber` stable **9.8.1** (2026-09-24; 9.8.0 adds React 19.3 compatibility). **v10 is in alpha** (10.0.0-alpha.5, 2026-09-08), "as we march toward first class WebGPU and TSL support". `@react-three/drei` 10.7.9 — [R3F releases](https://github.com/pmndrs/react-three-fiber/releases); [npm @react-three/fiber](https://www.npmjs.com/package/@react-three/fiber)
- pmndrs `postprocessing` stable **6.39.5** (2026-09-09), built for `WebGLRenderer`. v7 is in beta (7.0.0-beta.16, 2026-02-19) and "_Requires three ≥ 0.179.0 < 0.184.0_", so it is **not compatible with r186**. `@react-three/postprocessing` is 3.1.3 — [postprocessing releases](https://github.com/pmndrs/postprocessing/releases); [npm postprocessing](https://www.npmjs.com/package/postprocessing)

**WebGPURenderer / TSL (three.js manual)**
- "`WebGPURenderer` is designed to be the modern alternative to the long-standing `WebGLRenderer`… If a device/browser doesn't support WebGPU, the renderer can automatically fall back to using a WebGL 2 backend."
- TSL is used through `three/webgpu` and `three/tsl` imports. "Shader code written in TSL can be transpiled to WGSL or GLSL depending on the available backend."
- Initialization is async: use `await renderer.init()` or `setAnimationLoop`. `forceWebGL: true` forces the WebGL2 backend.
- "Custom materials based on `ShaderMaterial`, `RawShaderMaterial` and modifications of built-in materials via `onBeforeCompile()` are not supported in `WebGPURenderer`."
- "`EffectComposer` with its effect passes are not supported" because post-processing is now TSL node composition.
- "The renderer itself is still in an experimental state although its maturity level has been greatly improved… depending on your application… you will encounter missing features or a better performance with `WebGLRenderer`."
— [three.js manual: WebGPURenderer](https://github.com/mrdoob/three.js/blob/dev/manual/pages/webgpurenderer.html)
- Post-processing for WebGPURenderer: `const renderPipeline = new THREE.RenderPipeline(renderer)` "replaces the previous instance of `EffectComposer`". Effects are TSL nodes such as `pass()`, `dotScreen`, `rgbShift`, `fxaa`, `traa` and `mrt()` — [three.js manual: WebGPU post-processing](https://github.com/mrdoob/three.js/blob/dev/manual/pages/webgpu-postprocessing.html)
- `PostProcessing` is "@deprecated since r183. Use RenderPipeline instead." Older tutorials that use `THREE.PostProcessing` are **outdated** — [PostProcessing.js](https://github.com/mrdoob/three.js/blob/dev/src/renderers/common/PostProcessing.js)
- WebGPURenderer options include `stencil` (default **false**), `alpha` (default true), `antialias` and `forceWebGL` — [WebGPURenderer.js](https://github.com/mrdoob/three.js/blob/dev/src/renderers/webgpu/WebGPURenderer.js)
- Secondary source: "Three.js 0.186 ships a mature WebGPURenderer" but "the three.js manual still describes the renderer as experimental" — [Utsubo migration guide 2026](https://www.utsubo.com/blog/webgpu-threejs-migration-guide)

**Video as a texture/background**
- `VideoTexture` takes an HTMLVideoElement. `VideoFrameTexture` (a subclass) takes manually supplied frames via `setFrame(frame)`. The typical use is WebCodecs `VideoFrame`s, which fits `MediaStreamTrackProcessor` — [VideoFrameTexture.js](https://github.com/mrdoob/three.js/blob/dev/src/textures/VideoFrameTexture.js)
- Official examples in the three.js repo (dev branch):
  - `webgl_materials_video_webcam.html`, `webgl_morphtargets_webcam.html` (face morph targets driven by webcam)
  - `webgl_materials_video.html` / `webgpu_materials_video.html`
  - `webgpu_video_frame.html`
  - `webgl_clipping_stencil.html` / `webgpu_clipping_stencil.html`
  - `webgl_postprocessing_masking.html` / `webgpu_postprocessing_masking.html`
  - `webgpu_mrt_mask.html`
  - `webgl_camera_array.html` / `webgpu_camera_array.html`
  — [three.js examples directory](https://github.com/mrdoob/three.js/tree/dev/examples)
- WebGPU `GPUDevice.importExternalTexture` (zero-copy video to shader) is supported in Chrome 113+ on macOS and Safari 26 — [MDN BCD 8.1.3 via MDN](https://developer.mozilla.org/en-US/docs/Web/API/GPUDevice/importExternalTexture)

**Landmarks to 3D**
- Codrops tutorial (Oct 2024, uses legacy `@mediapipe/hands` + Three.js): builds "a full 3D hand controller with depth", converting 2D screen coordinates into 3D space. It uses wrist and middle-finger keypoints to estimate depth, a closed-fist gesture to grab and drag, and collision detection — [Codrops tutorial](https://tympanus.net/codrops/2024/10/24/creating-a-3d-hand-controller-using-a-webcam-with-mediapipe-and-three-js/); [demo](https://tympanus.net/Tutorials/webcam-3D-handcontrols/); [repo Cai3ra/webcam-3D-handcontrols](https://github.com/Cai3ra/webcam-3D-handcontrols)
- The FaceLandmarker transformation matrix assumes a perspective camera with vertical FOV 63°, near 1 cm and far 100 m (see Q1) — [face_geometry_from_landmarks_graph.cc](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/cc/vision/face_geometry/face_geometry_from_landmarks_graph.cc)

### Inferences
- **Recommended rendering architecture for the "rectangle between hands" effect.**
  - Draw the webcam as a full-screen quad (VideoTexture, mirrored with `uv.x = 1 - uv.x` for a selfie view).
  - Build a `THREE.Shape` or a 4-vertex `BufferGeometry` from the 4 fingertip landmarks, converted to NDC (`x_ndc = (1 - x)*2 - 1` if mirrored, `y_ndc = 1 - 2y`) under an `OrthographicCamera(-1,1,1,-1)`.
  - Give that quad a material that **samples the same video texture** with a filter (invert, pixelate, chromatic aberration, thermal LUT). This produces "the region inside the polygon is filtered" without a stencil buffer.
  - Order the 4 points by angle around their centroid so the quad never self-intersects.
- Alternatives for arbitrary polygons or multiple effects:
  1. Stencil: write the polygon to the stencil buffer (`material.stencilWrite`, `stencilRef`, `stencilFunc`), then draw a full-screen filtered pass with a stencil test. See `webgl_clipping_stencil` and `webgl_postprocessing_masking`. WebGPURenderer needs `stencil: true`.
  2. Render the polygon into a mask render target (or an `mrt()` output in TSL) and mix filtered and unfiltered video in a final full-screen shader.
  3. A signed-distance polygon test in the fragment shader, with points passed as uniforms. This allows soft or feathered edges.
- **3D cube from 3 fingertips.**
  - Take 3 fingertip points p0, p1, p2 in a common 3D frame: build a right-handed basis with e1 = p1 - p0, e2 = p2 - p0 and e3 = normalize(e1 × e2) · scale.
  - Build a `Matrix4` from (e1, e2, e3, p0) and apply it to a unit `BoxGeometry` translated to (0.5, 0.5, 0.5). This gives a parallelepiped spanned by the fingers.
  - Camera-space depth options:
    - (a) Use normalized x, y with relative z (same scale as x) under an orthographic camera. This is simplest and looks right for AR.
    - (b) Estimate absolute distance with a pinhole model: `Z ≈ f_px * L_world / L_px`, using a known world-landmark bone length (e.g. wrist to index MCP from `worldLandmarks`, in meters) vs its pixel length. Then unproject with `Vector3(x_ndc, y_ndc, 0.5).unproject(camera)` along the ray, or directly `X = (u - cx) * Z / f`.
    - (c) Run a PnP solve (e.g. OpenCV.js `solvePnP`) between `worldLandmarks` and 2D landmarks for full 6DoF hand pose.
  - Smooth landmarks with a One Euro filter to reduce jitter; the webgpu-vision project also uses One Euro filtering.
- **Renderer choice.** For a first working demo, `WebGLRenderer` + GLSL `ShaderMaterial` + pmndrs `postprocessing` 6.x has the most tutorials and the fastest iteration. Move to `WebGPURenderer` + TSL when you want compute shaders (particles, fluid) or zero-copy `importExternalTexture`. Babylon.js 9 is a viable alternative with its own node material editor. R3F adds React ergonomics, but its WebGPU support is still in v10 alpha.
- Raw WebGL2/WebGPU is only worth it for a minimal single-pass filter. Three.js already handles video textures, resize and color space.

### Gaps
- The Babylon.js 9 release notes were not examined (WebGPU and video-texture specifics). Only the version and date were confirmed.
- No benchmark of WebGPURenderer vs WebGLRenderer for a video + overlay workload on Apple Silicon.
- It was not verified whether the pmndrs `postprocessing` 6.x `ShaderPass` works with r186 without warnings. The v7 beta explicitly caps at three < 0.184.

---

## 4. Creative-coding options: p5.js + ml5.js (handPose, faceMesh, bodyPose), Hydra, others

### Takeaway
**ml5.js 1.4.0** (2026-08-07) with **p5.js 2.x** (latest 2.3.4) is the fastest way to sketch. By default `ml5.handPose` runs the MediaPipe Hands model through the **TensorFlow.js runtime** (tfjs 4.22, optional WebGPU backend), with `runtime: "mediapipe"` loading the **legacy** `@mediapipe/hands`. It does not use tasks-vision. This works for prototyping, but the underlying models are frozen. **Hydra** (hydra-synth 1.4.0) is good for live-coded video shaders with `s0.initCam()` and can be combined with hand data manually.

### Cited Findings
- npm `ml5` latest **1.4.0** (2026-08-07). CDN: `<script src="https://unpkg.com/ml5@1/dist/ml5.js"></script>`. The maintainers say they "will try our best to maintain compatibility with the existing API going forward, switching to a future 2.x if needed" — [ml5-next-gen repo](https://github.com/ml5js/ml5-next-gen); [npm ml5](https://www.npmjs.com/package/ml5)
- ml5 1.4.0 dependencies:
  - `@mediapipe/hands`, `@mediapipe/face_mesh`, `@mediapipe/pose` and `@mediapipe/selfie_segmentation` (all legacy)
  - `@tensorflow-models/hand-pose-detection`, `face-landmarks-detection@1.0.5`, `pose-detection`, `body-segmentation`, `depth-estimation`, `coco-ssd`, `mobilenet` and `speech-commands`
  - `@tensorflow/tfjs` ^4.22.0 and `@tensorflow/tfjs-backend-webgpu` ^4.22.0
  — [npm ml5@1.4.0](https://www.npmjs.com/package/ml5)
- `ml5.handPose` source:
  - The underlying model is `handPoseDetection.SupportedModels.MediaPipeHands`.
  - Options: `maxHands` (default **2**), `runtime` enum `["mediapipe","tfjs"]` (default **"tfjs"**), `modelType` `["lite","full"]` (default **"full"**) and `flipped` (mirror).
  - `solutionPath` defaults to `https://cdn.jsdelivr.net/npm/@mediapipe/hands` when the runtime is mediapipe.
  — [ml5 HandPose/index.js](https://github.com/ml5js/ml5-next-gen/blob/main/src/HandPose/index.js)
- `ml5.faceMesh` uses `faceLandmarksDetection.SupportedModels.MediaPipeFaceMesh` with runtime default "tfjs", plus `maxFaces`, `refineLandmarks` and `flipped`. `ml5.bodyPose` supports `MoveNet` or `BlazePose`, with BlazePose runtime default "tfjs" — [ml5 FaceMesh/index.js](https://github.com/ml5js/ml5-next-gen/blob/main/src/FaceMesh/index.js); [ml5 BodyPose/index.js](https://github.com/ml5js/ml5-next-gen/blob/main/src/BodyPose/index.js)
- ml5 release notes:
  - **v1.4.0** (2026-08-07): "Remove p5.js 1.x examples", "Fix iOS WebGPU keypoint misalignment", "Add MobileNet Feature Extractor".
  - v1.3.0 (2025-10-15): "Update p5 version to 2.0.4", added tfjs depth-estimation.
  - v1.2.2 (2025-07-31): p5.js 2.0 support, "Add support for OffscreenCanvas".
  — [ml5 releases](https://github.com/ml5js/ml5-next-gen/releases)
- npm `p5` latest **2.3.4** (2026-09-25). p5 2.0.0 was released 2025-04-17, and the 1.x line is kept under dist-tag `r1` = 1.11.13 — [npm p5](https://www.npmjs.com/package/p5)
- Hydra: "Livecoding networked visuals in the browser" (2.7k stars, pushed 2026-04-25). `s0.initCam()` initializes a webcam in source buffer s0. npm `hydra-synth` is 1.4.0 (2025-09-14), usable as a standalone synth engine — [hydra-synth/hydra](https://github.com/hydra-synth/hydra); [npm hydra-synth](https://www.npmjs.com/package/hydra-synth)
- Other hand-tracking library: **WebAR.rocks.hand** is a "Lightweight WebGL and JavaScript library for real time, on device hand detection and tracking" for AR (141 stars, last push 2025-11-15) — [WebAR.rocks.hand](https://github.com/WebAR-rocks/WebAR.rocks.hand)

### Inferences
- p5 + ml5 is best for a one-evening prototype: draw a `beginShape()` quad between fingertips and apply `filter()` or a p5 shader inside a clip mask. For shader-heavy or 3D work, Three.js + tasks-vision gives more control and newer models.
- You can use p5.js (WEBGL mode, p5.Shader) with **tasks-vision directly** instead of ml5, which avoids the legacy tfjs/MediaPipe runtimes. This is a pattern choice, not a documented ml5 feature.
- Hydra can be driven by hand landmarks by writing values into JS variables read in Hydra functions (e.g. `osc(() => handX*10)`). This is a common live-coding pattern; no maintained Hydra + hand-tracking integration library was found.

### Gaps
- Not verified whether ml5's tfjs runtime uses the WebGPU or WebGL backend by default on macOS Chrome and Safari (the 1.4.0 fix mentions "iOS WebGPU").
- No FPS numbers found for ml5 handPose on Apple Silicon.

---

## 5. Performance: Web Workers/OffscreenCanvas, requestVideoFrameCallback, WebCodecs/MediaStreamTrackProcessor, WebGPU availability on macOS (2026)

### Takeaway
Everything needed is available on macOS in both browsers:
- WebGPU: Chrome 113+, Safari 26+
- `requestVideoFrameCallback`: Chrome 83+, Safari 15.4+
- OffscreenCanvas with WebGL: Chrome 69+, Safari 16.4+
- `VideoFrame`: Chrome 94+, Safari 16.4+

The main incompatibility is **MediaStreamTrackProcessor**: Safari (18+) exposes it **only in DedicatedWorker**, while Chrome (94+) exposes it on **Window**. Portable code needs a fallback such as `createImageBitmap(video)` sent to a worker, which is what Google's official samples do. MediaPipe's `detectForVideo` is synchronous and blocks, so run it in a worker.

### Cited Findings
- **Safari 26.0** (released 2025-09-15) ships **WebGPU on macOS**, iOS, iPadOS and visionOS. WebKit says it is "preferred for new sites and web apps, as it maps better to Metal" — [WebKit: Safari 26.0 features](https://webkit.org/blog/17333/webkit-features-in-safari-26-0/); [WebKit WWDC25 post](https://webkit.org/blog/16993/news-from-wwdc25-web-technology-coming-this-fall-in-safari-26-beta/)
- MDN browser-compat-data 8.1.3:
  - `GPU` (WebGPU): Chrome 113 on ChromeOS, macOS and Windows (Linux added in 144); Safari **26**; Firefox 141 partial.
  - `HTMLVideoElement.requestVideoFrameCallback`: Chrome 83, Safari 15.4, Firefox 132.
  - `VideoFrame`: Chrome 94, Safari 16.4.
  - `OffscreenCanvas` and `getContext`: Chrome 69, Safari 16.4.
  - `WebGL2RenderingContext`: Chrome 56, Safari 15.
  - `ML` (WebNN): Chrome 112 behind flags; Safari not supported.
  — [MDN: WebGPU API](https://developer.mozilla.org/en-US/docs/Web/API/WebGPU_API); [MDN: requestVideoFrameCallback](https://developer.mozilla.org/en-US/docs/Web/API/HTMLVideoElement/requestVideoFrameCallback); [MDN: VideoFrame](https://developer.mozilla.org/en-US/docs/Web/API/VideoFrame); [MDN: OffscreenCanvas](https://developer.mozilla.org/en-US/docs/Web/API/OffscreenCanvas)
- `MediaStreamTrackProcessor`: Chrome 94, marked partial with the note "Exposed on `Window` instead of `DedicatedWorker`". Safari **18**. Firefox none in BCD. `VideoTrackGenerator` is Safari 18 only — [MDN: MediaStreamTrackProcessor](https://developer.mozilla.org/en-US/docs/Web/API/MediaStreamTrackProcessor)
- Mozilla: MediaStreamTrackProcessor and VideoTrackGenerator are **worker-only** in the standard, so as to "never block the browser's real time media pipeline on a busy main thread". "Chrome shipped proprietary versions of these APIs back in 2021, which are instead exposed on the main-thread, and also handle audio", whereas Safari's implementation is worker-only and video-only — [Mozilla WebRTC blog](https://blog.mozilla.org/webrtc/unbundling-mediastreamtrackprocessor-and-videotrackgenerator/)
- Safari Technology Preview 234 fixed MediaStreamTrackProcessor to respect `track.enabled = false`, so work on it is ongoing — [STP 234 release notes](https://webkit.org/blog/17674/release-notes-for-safari-technology-preview-234/)
- MediaPipe's `detectForVideo()` "run[s] synchronously and block[s] the user interface thread" and the docs recommend web workers — [Face Landmarker web guide](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/web_js)
- Official worker pattern:
  - The main thread runs `requestAnimationFrame`, calls `createImageBitmap(video)` and does `postMessage({bitmap}, [bitmap])`.
  - The worker runs `FilesetResolver.forVisionTasks(wasmPath, true)` (the second argument selects the ES-module WASM loader in module workers) and creates the task with `delegate: 'GPU'`.
  - The worker falls back to CPU if WebGL2 on OffscreenCanvas fails.
  — [mediapipe-samples-web base-worker.ts](https://github.com/google-ai-edge/mediapipe-samples-web/blob/main/src/workers/base-worker.ts); [base-vision-task.ts](https://github.com/google-ai-edge/mediapipe-samples-web/blob/main/src/components/base-vision-task.ts)
- MediaPipe's WebGL path does synchronous `glReadPixels` readbacks, profiled at >10 ms in one report. This is the main known web bottleneck — [issue #5377](https://github.com/google-ai-edge/mediapipe/issues/5377); [Sonified/webgpu-vision](https://github.com/Sonified/webgpu-vision)
- Frame-budget context from a benchmark on a 120 Hz display: one frame is 8.3 ms. Stock MediaPipe hands at ~20 ms therefore spans ~3 render frames (M1 Max, Chrome 148) — [Sonified/webgpu-vision](https://github.com/Sonified/webgpu-vision)

### Inferences
- **Recommended loop on macOS:**
  1. `getUserMedia({video:{width:1280,height:720,frameRate:60}})`
  2. Render at display rate with `renderer.setAnimationLoop`
  3. Use `video.requestVideoFrameCallback` to send each **new** camera frame, as an ImageBitmap or `VideoFrame`, to a module worker running tasks-vision with the GPU delegate
  4. The worker posts back plain landmark arrays; the renderer interpolates or smooths them (One Euro) between results
- Pass `metadata.mediaTime*1000` from rVFC as the `timestamp`. MediaPipe VIDEO mode requires monotonically increasing timestamps.
- For zero-copy capture on Safari, transfer the `MediaStreamTrack` to the worker and use `MediaStreamTrackProcessor` there. On Chrome, create the processor on Window and transfer its `ReadableStream`, or use the ImageBitmap path. Remember to call `VideoFrame.close()`.
- Keep rendering on the main thread (Three.js on a normal canvas) and inference in the worker. Rendering in OffscreenCanvas in a worker is possible but complicates input and DOM overlays for little gain.
- On Apple Silicon, WebGPU works in both browsers, so a WebGPURenderer render path is viable on both Chrome and Safari. Inference will still use WebGL2 inside MediaPipe, which means two GPU APIs and contexts coexisting. That is fine in practice but prevents zero-copy sharing between inference and rendering.

### Gaps
- It was not verified whether Safari 26 WebGPU is available on older macOS versions (Sonoma/Sequoia) running Safari 26 or only on macOS Tahoe 26.
- No measurement found of `createImageBitmap(video)` vs `VideoFrame` transfer cost on macOS.
- It was not verified whether Chrome now also exposes MediaStreamTrackProcessor in DedicatedWorker; BCD marks it Window-only.

---

## 6. Open-source demos, repos and tutorials (hand-tracking AR in the browser)

### Takeaway
There are many MediaPipe + Three.js hand-tracking demos: particle systems, 3D controllers, air-drawing, gesture-controlled scenes. Most use the **legacy `@mediapipe/hands`** or tasks-vision via CDN. Google's new **mediapipe-samples-web** (TypeScript + workers) is the best-maintained reference. No well-known repo implements exactly "a filtered rectangle between two hands", but several are close, e.g. "frame a window with your hand".

### Cited Findings
- **google-ai-edge/mediapipe-samples-web**: official Vite/TS demos for all tasks, with workers. Live at google-ai-edge.github.io/mediapipe-samples-web — [repo](https://github.com/google-ai-edge/mediapipe-samples-web)
- **google-ai-edge/mediapipe-samples** (2.8k stars, pushed 2026-09-15): the multi-platform samples repo — [repo](https://github.com/google-ai-edge/mediapipe-samples)
- **jaredrhod/barehands** (~1,006 stars, created 2026-08-15): "Move things on your screen with your bare hands. A webcam-powered, hand-tracked interface…". Its hand tracking (Google MediaPipe) and 3D (three.js) load from CDNs, and it runs in Chrome — [repo](https://github.com/jaredrhod/barehands)
- **collidingScopes/stark-shapes** (92 stars): "Animate shapes with hand gestures. Web tool built with threejs and mediapipe hand-tracking" — [repo](https://github.com/collidingScopes/stark-shapes). Same author: **threejs-handtracking-101**, "control a 3D sphere using hand gestures" — [repo](https://github.com/collidingScopes/threejs-handtracking-101)
- **Codrops "Creating a 3D Hand Controller Using a Webcam with MediaPipe and Three.js"** (2024-10-24): depth from 2D, grab gesture, collisions. Uses the legacy `@mediapipe/hands` — [tutorial](https://tympanus.net/codrops/2024/10/24/creating-a-3d-hand-controller-using-a-webcam-with-mediapipe-and-three-js/); [repo Cai3ra/webcam-3D-handcontrols](https://github.com/Cai3ra/webcam-3D-handcontrols)
- **Sonified/webgpu-vision**:
  - Hand and face tracking on WebGPU compute shaders (ORT Web + custom WGSL).
  - Demos: a Three.js head-coupled parallax "ball-toss" demo with a MediaPipe vs WebGPU A/B toggle and One Euro filtering, and a face-puppeting demo with a 52-blendshape head in Three.js.
  - Requires Chrome 113+ or Safari 18+ with WebGPU enabled.
  — [repo](https://github.com/Sonified/webgpu-vision)
- **kirmskhq/media-experiments** (new, 0 stars): "Browser webcam experiments with live hand and face tracking. Roblox Hand Portal: frame a window with your hand". Conceptually closest to the rectangle-between-fingers idea; quality is unknown — [repo](https://github.com/kirmskhq/media-experiments)
- Gesture-controlled Three.js particle "Christmas tree" projects (Three.js + MediaPipe, e.g. electronicminer, 87 stars, pushed 2026-08) — [repo](https://github.com/electronicminer/gesture-Christmas_tree-3d_with_photo)
- Tutorial: a "Gesture-Controlled Particle System Tutorial (Three.js + MediaPipe)" (quality not assessed) — [theaicowboys.com](https://www.theaicowboys.com/post/gesture-controlled-particle-system-threejs-mediapipe)
- Air-drawing and finger painting: dealer1943/FingerPaint ("webcam fingertip drawing on paper (Three.js + MediaPipe)") — [repo](https://github.com/dealer1943/FingerPaint); nidhi1208/AirDraw-3D — [repo](https://github.com/nidhi1208/AirDraw-3D)
- WebXR hand tracking is a different input path: headsets, not webcams. Examples are AdaRoseCannon/handy-work (pushed 2025-12) — [repo](https://github.com/AdaRoseCannon/handy-work) — and marlon360/webxr-handtracking, **last pushed 2020-09, outdated** — [repo](https://github.com/marlon360/webxr-handtracking)
- Three.js official webcam examples: `webgl_materials_video_webcam`, `webgl_morphtargets_webcam`, `webgpu_video_frame` — [three.js examples](https://github.com/mrdoob/three.js/tree/dev/examples)

### Inferences
- Useful starting combination: the hand-landmarker worker from **mediapipe-samples-web** plus the video background and overlay-scene structure from the Three.js `webgl_materials_video_webcam` example. Add the Codrops depth approach for the 3D cube.
- Most community demos were written quickly, some AI-generated (e.g. the "Gemini 3 generated" Christmas tree repos). Use them for ideas, not architecture.

### Gaps
- No curated CodePen list from Google for tasks-vision 1.0 was found; the docs now link StackBlitz. Older `codepen.io/mediapipe*` pens exist but were not re-verified.
- No authoritative "awesome list" for browser hand-AR in 2026 was found.

---

## 7. Web vs native for this use case (latency, dev speed, shaders, sharing)

### Takeaway
The web wins on development speed (hot reload, TSL/GLSL shaders, no build signing) and on sharing (a single URL on any Mac). It costs some tracking latency: stock MediaPipe web is about 20 ms/frame on an M1 Max, with GPU readback overhead, it cannot use WebGPU or the ANE for vision tasks, and camera control is limited. For an interactive demo at 30–60 fps on Apple Silicon, the web is sufficient. Native (Swift/Metal/Vision, or Python/C++) only becomes necessary for sub-10 ms motion-to-photon latency, high-res or high-fps camera modes, or Apple Neural Engine usage.

### Cited Findings
- On the web, stock MediaPipe hand tracking measured ~20 ms/frame (1–2 hands) in Chrome on an M1 Max. That is ~3 render frames at 120 Hz, "3x the input lag" of a custom WebGPU implementation at ~5 ms. This is a single third-party benchmark — [Sonified/webgpu-vision](https://github.com/Sonified/webgpu-vision)
- MediaPipe Web vision tasks use WebGL with synchronous readbacks. WebGPU support "currently focused on our LLM Inference API" (Jan 2025, issue still open) — [issue #5826](https://github.com/google-ai-edge/mediapipe/issues/5826); [issue #5377](https://github.com/google-ai-edge/mediapipe/issues/5377)
- The MediaPipe v1.0.0 release notes include "Remove MacOS prebuilts" (scope ambiguous) — [MediaPipe v1.0.0 release](https://github.com/google-ai-edge/mediapipe/releases/tag/v1.0.0)
- WebNN (NPU access) is Chrome behind a flag only and not in Safari, per BCD. LiteRT.js lists WebNN as "experimental in Chrome and Edge" — [MDN BCD: ML](https://developer.mozilla.org/en-US/docs/Web/API/Web_Neural_Network_API); [LiteRT.js blog](https://developers.googleblog.com/en/litertjs-googles-high-performance-web-ai-inference/)
- WebGPU is on by default in both Safari 26 and Chrome on macOS, and "maps better to Metal" — [WebKit Safari 26.0](https://webkit.org/blog/17333/webkit-features-in-safari-26-0/)

### Inferences
- **Pros of web.**
  - Instant iteration: Vite HMR, and shader edits without recompiling.
  - One URL to share. It runs on any Mac, PC or phone with a webcam, and GitHub Pages or Vercel hosting is free.
  - Huge Three.js/TSL ecosystem and examples.
  - MediaPipe Tasks gives identical models to native.
  - Privacy: everything stays on-device.
- **Cons of web.**
  - Extra latency: camera → video element → texture upload → WebGL inference → readback → postMessage → render.
  - No ANE/CoreML: WebNN is not in Safari.
  - `getUserMedia` constraints limit camera format, exposure and fps control.
  - Browser-specific quirks (MSTP Window vs Worker; Safari GPU edge cases).
  - HTTPS is required for camera access (localhost is exempt).
  - Tab throttling.
- **Pros of native on macOS.** Apple Vision framework hand pose (`VNDetectHumanHandPoseRequest`) and ARKit-grade face tracking with ANE acceleration, Metal compute, direct AVCapture control, and lower and more deterministic latency. Cons: slower iteration and harder distribution (signing, notarization). The MediaPipe native macOS path appears de-emphasized ("Remove MacOS prebuilts").
- **Verdict for the stated goal** (finger-shape demo + face mesh + gestures on Apple Silicon Chrome/Safari): web is the pragmatic choice.
  - Suggested stack:
    - Vite + TypeScript
    - `@mediapipe/tasks-vision@1.0.1`: HandLandmarker or GestureRecognizer (numHands 2) plus FaceLandmarker with blendshapes and matrices, GPU delegate, in a module worker
    - `three@0.186` with WebGLRenderer + GLSL (fast start) or WebGPURenderer + TSL (future-proof)
    - VideoTexture background
    - One Euro smoothing
  - Optionally p5.js 2 + ml5 1.4 for quick sketches.

### Gaps
- No rigorous side-by-side latency measurement (web vs native Apple Vision vs native MediaPipe) on the same Mac was found.
- Apple Vision framework and native hand-tracking specifics were not researched here; they are out of scope for this web-focused note, and the native claims above are inferences.
