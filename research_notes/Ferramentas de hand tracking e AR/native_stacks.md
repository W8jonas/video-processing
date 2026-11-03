# Native and lower-level stacks for real-time webcam hand, face and gesture tracking with 3D AR overlay (macOS Apple Silicon, as of Sept 2026)

Scope: code-first stacks (Swift/Apple frameworks, C++, Rust, creative-coding frameworks, alternative ML models and runtimes) for building a webcam demo where the user forms shapes with their fingers. Examples: a rectangle spanned by both hands' thumb and index tips and filled with a color or filter, or a 3D cube anchored on 3 fingertips. Also covers face detection and mesh, and gestures. Release dates below were checked against GitHub release metadata via `gh api` on 2026-09-27 unless another source is given.

---

## 1. Apple Vision framework (+ AVFoundation, Metal, RealityKit, Create ML)

### Takeaway
On a Mac, Vision is the lowest-friction native path. You get 21-point hand pose for N hands, with confidence and left/right chirality. You also get face landmarks (76 points), 2D/3D body pose and person segmentation, all on-device with no build system pain. Since macOS 15 there is a modern async Swift API, and Apple says new Vision features will ship only in Swift. The weak spots: face "mesh" is sparse (76 points, compared with MediaPipe's 478 plus blendshapes), there is no webcam-based ARKit on the Mac, and Apple publishes no latency numbers.

### Cited Findings
**Hand pose (legacy Obj-C/Swift API, `VNDetectHumanHandPoseRequest`)**
- 21 hand landmarks: "four for each finger and thumb and one for the wrist". Points are grouped by `VNRecognizedPointGroupKey` (e.g. `.handLandmarkKeyIndexTIP`, `.handLandmarkKeyThumbTIP`). Coordinates are normalized with the origin at the lower-left, so the sample flips y (`1 - y`) to convert to AVFoundation coordinates. — [WWDC20 "Detect Body and Hand Pose with Vision"](https://developer.apple.com/videos/play/wwdc2020/10653/)
- `maximumHandCount` defaults to 2. Pose is computed for every detected hand up to the max, so lowering it "can help with performance". Apple recommends tuning it for latency. — [WWDC20 10653](https://developer.apple.com/videos/play/wwdc2020/10653/)
- The official WWDC20 sample (drawing by pinching) uses `AVCaptureVideoDataOutputSampleBufferDelegate` → `VNImageRequestHandler(cmSampleBuffer:)` → reads the thumb and index tips → drops points with confidence ≤ 0.3. Pinch uses a distance threshold (~40 px) plus an "evidence counter" of 3 consecutive frames as hysteresis before changing state. That is a simple, reusable gesture-debouncing pattern. — [WWDC20 10653](https://developer.apple.com/videos/play/wwdc2020/10653/)
- Documented limitations: hands near screen edges (partially occluded), hands parallel to the viewing direction ("karate chop"), gloves, and "the algorithm will sometimes detect feet as hands". — [WWDC20 10653](https://developer.apple.com/videos/play/wwdc2020/10653/)
- `chirality` (left/right) was added to the hand pose observation in 2021. — [WWDC21 "Detect people, faces, and poses using Vision"](https://developer.apple.com/videos/play/wwdc2021/10040/)
- Revisions: `VNDetectHumanHandPoseRequest` revision from iOS 14+. The Swift `DetectHumanHandPoseRequest` revision is from iOS 18+. — [Apple Developer Forums thread 803595 (Oct 2025)](https://developer.apple.com/forums/thread/803595)

**New Swift-only Vision API (iOS 18 / macOS 15, WWDC24)**
- Redesigned for Swift concurrency: async/await, `VN` prefix dropped (`VNDetectBarcodesRequest` → `DetectBarcodesRequest`), observations returned directly from `perform()`, `performAll()` streams results as each request finishes, Swift 6 compatible. — [WWDC24 "Discover Swift enhancements in the Vision framework"](https://developer.apple.com/videos/play/wwdc2024/10163/)
- `DetectHumanBodyPoseRequest` gained `detectsHands = true`, which returns `rightHandObservation`/`leftHandObservation` on `HumanBodyPoseObservation` (holistic body+hands in one request). — [WWDC24 10163](https://developer.apple.com/videos/play/wwdc2024/10163/)
- Old APIs "aren't going away", but Apple "strongly recommend[s] adopting the new APIs", and Vision will "only introduce new features in Swift moving forward". — [WWDC24 10163](https://developer.apple.com/videos/play/wwdc2024/10163/)
- For video, Apple's pattern is a TaskGroup that caps concurrent Vision requests (example: 5) to bound memory. — [WWDC24 10163](https://developer.apple.com/videos/play/wwdc2024/10163/)
- `DetectHumanHandPoseRequest` returns `HumanHandPoseObservation`. — [Apple docs: DetectHumanHandPoseRequest](https://developer.apple.com/documentation/vision/detecthumanhandposerequest?changes=_5)

**2025 update (WWDC25)**
- An "updated hand pose detection model": still 21 joints, "smaller, modernized model" with "improved accuracy, less memory usage, and less latency". **Joints are not in the same location as the previous model**, so Apple encourages retraining any Create ML hand pose or action classifier. — [WWDC25 "Read documents using the Vision framework"](https://developer.apple.com/videos/play/wwdc2025/272/)
- Conflict/uncertainty: in Oct 2025 a developer reported that no new hand pose revision for iOS 26+ exists in the docs (the video says `DetectHandPoseRequest`, which is not a real type name). No Apple reply at the time of the fetch. — [Apple Developer Forums 803595](https://developer.apple.com/forums/thread/803595)
- Other WWDC25 Vision additions: `RecognizeDocumentsRequest` and `DetectCameraLensSmudgeRequest`. — [WWDC25 272](https://developer.apple.com/videos/play/wwdc2025/272/) (via search summary)

**2026 update (WWDC26)**
- "What's new in image understanding" (session 237) added `GenerateIterativeSegmentationRequest` (tap/box/lasso/scribble interactive segmentation, model downloaded on demand via `downloadAssets()`), `GenerateObjectnessBasedSaliencyImageRequest`, Vision on watchOS, and image input plus Vision-based tools for the Foundation Models framework. **No hand, face or body pose changes were mentioned.** — [WWDC26 237](https://developer.apple.com/videos/play/wwdc2026/237/)

**Face**
- Face landmarks revision 3: "76-point constellation to better represent major face regions and also provide accurate pupil detection". Face detection rev 3 adds masked-face detection and continuous roll/yaw/**pitch**. — [WWDC21 10040](https://developer.apple.com/videos/play/wwdc2021/10040/)
- Revisions 1–3 support a 65-point constellation, and rev3 also supports 76 points. Regions: faceContour, eyes, eyebrows, pupils, nose, noseCrest, medianLine, inner and outer lips. — [Apple docs: VNFaceLandmarks2D](https://developer.apple.com/documentation/vision/vnfacelandmarks2d); [VNRequestFaceLandmarksConstellation](https://developer.apple.com/documentation/vision/vnrequestfacelandmarksconstellation)
- Person segmentation: `VNGeneratePersonSegmentationRequest` (stateful across frames, quality levels accurate/balanced/fast, available on macOS) is useful for "filter only the background / only the person" effects. — [WWDC21 10040](https://developer.apple.com/videos/play/wwdc2021/10040/)

**3D body pose**
- `VNDetectHumanBodyPose3DRequest` (WWDC23): 17 joints in 6 groups, positions in **meters**, `bodyHeight`, camera-origin matrix, `VNPoint3D` uses 4×4 matrices "consistent with ARKit". Depth (`AVDepthData`, from LiDAR or portrait disparity) is **optional**. `VNGeneratePersonInstanceMaskRequest` handles up to 4 people. — [WWDCNotes: WWDC23 "Explore 3D body pose and person segmentation in Vision"](https://wwdcnotes.com/documentation/wwdc23-111241-explore-3d-body-pose-and-person-segmentation-in-vision/); [Apple docs](https://developer.apple.com/documentation/vision/vndetecthumanbodypose3drequest)
- There is **no 3D hand pose** request in Vision. Hand pose is 2D-only (normalized x,y plus confidence). — inferred from the WWDC20/21/24/25 sessions above, none of which describe 3D hand joints.

**Custom gestures via Create ML**
- WWDC21 added **Hand Pose Classifier** (static poses) and **Hand Action Classifier** (temporal gestures) templates to Create ML. Both build on Vision hand pose and integrate with Vision, Camera and ARKit. — [WWDC21 "Classify hand poses and actions with Create ML" (10039)](https://developer.apple.com/videos/play/wwdc2021/10039); [WWDCNotes summary page](https://wwdcnotes.com/documentation/wwdcnotes/wwdc21-10039-classify-hand-poses-and-actions-with-create-ml/)
- After the 2025 model update, classifiers trained on old keypoints should be retrained. — [WWDC25 272](https://developer.apple.com/videos/play/wwdc2025/272/)

**Rendering side (Metal, RealityKit, SceneKit)**
- **SceneKit was soft-deprecated at WWDC25 (June 2025)**: it gets critical bug fixes only, with no hard deprecation planned. Apple recommends RealityKit (ECS, USD assets, available on macOS/iOS/visionOS and now tvOS). — [WWDC25 "Bring your SceneKit project to RealityKit" (288)](https://developer.apple.com/videos/play/wwdc2025/288/); [dev.to summary](https://dev.to/arshtechpro/wwdc-2025-scenekit-deprecation-and-realitykit-migration-a-comprehensive-guide-for-ios-developers-o26)
- ARKit on Mac (macOS 26) arrived only alongside Compositor Services for the "Remote Immersive Space" scene type (Mac renders to Vision Pro). It is **not** webcam hand or face tracking on the Mac. — [WWDC25 "What's new in visionOS 26" (317)](https://developer.apple.com/videos/play/wwdc2025/317/) (via search summary)
- Zero-copy camera → GPU: `CVMetalTextureCache` / `CVMetalTextureCacheCreateTextureFromImage` wrap a `CVPixelBuffer` from `AVCaptureVideoDataOutput` as an `MTLTexture`. Typically you capture in `kCVPixelFormatType_420YpCbCr8BiPlanarFullRange` (NV12-style Y + CbCr planes) and convert YCbCr→RGB in a shader. — [Apple docs: CVMetalTextureCache](https://developer.apple.com/documentation/corevideo/cvmetaltexturecache-q3j); [Apple archive sample MetalVideoCapture](https://developer.apple.com/library/archive/samplecode/MetalVideoCapture/Listings/MetalVideoCapture_AAPLRenderer_mm.html); [Rational Matter "Metal Camera Tutorial Part 2"](https://navoshta.com/metal-camera-part-2-metal-texture/)

### Inferences
- For the demo, Vision alone covers the tracking. With `maximumHandCount = 2`, read `thumbTip`/`indexTip` for both hands and use `chirality` to tell which hand is which; those 4 points are the rectangle corners. Fill the quad in a Metal fragment shader that samples the camera texture and applies a filter only inside the quad, or use Core Image with a mask. The 3-finger cube needs a 3D frame. Vision hand points are 2D, so estimate depth heuristically (e.g. from inter-joint pixel distance or palm size), or build an orthonormal basis from the 3 fingertip 2D points and extrude a cube in screen space. For true metric 3D, use MediaPipe world landmarks or a mesh model (sections 2 and 5).
- Swift + AVFoundation + Vision + Metal (MTKView) is the best "all Apple" learning stack. You touch CMSampleBuffer/CVPixelBuffer, YCbCr pixel formats, IOSurface-backed zero-copy textures, shaders and frame-pacing. RealityKit is easier for 3D but hides the pipeline, and SceneKit should not be used for new work (soft-deprecated 2025).
- Because Apple put new features only into the Swift API, C++ or Rust users reach Vision through Objective-C++ or `objc2-vision` and are limited to the `VN*` classes (see section 6).
- A good hybrid is Vision for hands plus MediaPipe Face Landmarker (478 points plus blendshapes, section 2) for face mesh, since Vision's 76-point face landmarks are too sparse for a mesh.

### Gaps
- Apple publishes no latency or FPS figures for Vision hand pose on Apple Silicon, and no statement on whether it runs on the Neural Engine versus GPU. Third-party blogs in search results claim ~8–12 ms per frame, but I could not trace those numbers to a primary benchmark, so they are left out.
- It is unconfirmed whether the WWDC25 "updated hand pose model" ships as an explicit new revision constant or silently replaced the existing revision (forum thread unresolved as of fetch).
- I could not fetch the JS-rendered Apple sample-code page "Detecting Hand Poses with Vision" directly. The code details above come from the WWDC20 session transcript that presents that sample.

---

## 2. MediaPipe in C++ (Bazel), Tasks C API, practicality in 2026

### Takeaway
MediaPipe has the richest models for this exact demo: 21 hand landmarks with metric world coordinates plus handedness, a gesture recognizer, and a face landmarker with 478 3D points, 52 blendshapes and a 4×4 face transform matrix. It is actively released (v1.0.0 July 2026). But native C++ on macOS is still Bazel-only, fragile across Xcode/macOS updates, and CPU-only on desktop per Google's docs. In 2026 the practical native route is to build the **Tasks C API** once into a `.dylib` (the approach ofxMediaPipe takes) or to use the Python wheels for prototyping. Hand-rolling a Bazel C++ graph is not a good first project.

### Cited Findings
- Release cadence (GitHub): v0.10.32 (2026-01-30), v0.10.33 (2026-03-23), v0.10.35 (2026-04-28), **v1.0.0 (2026-07-28)**. — [MediaPipe releases](https://github.com/google-ai-edge/mediapipe/releases); PyPI also lists 1.0.1 (Aug 14, 2026) with **macOS 11+ arm64 wheels**. — [PyPI mediapipe](https://pypi.org/project/mediapipe/#history)
- v1.0.0 notes include "Remove MacOS prebuilts" and migration of Apple rules to `MODULE.bazel` (bzlmod). — [MediaPipe v1.0.0 release](https://github.com/google-ai-edge/mediapipe/releases/tag/v1.0.0). Note: the WebFetch summary gave the date as July 28, 2025, but GitHub API metadata says 2026-07-28, which I treat as correct.
- v0.10.32 moved Bazel 6.5.0 → 7.4.1, Protobuf 5.28.3, and requires C++20 (per the releases-page summary). The repo `.bazelversion` currently pins **Bazel 7.7.0** (checked via GitHub API). — [MediaPipe releases](https://github.com/google-ai-edge/mediapipe/releases)
- The official macOS install doc (Homebrew, Xcode CLT, Bazelisk, `brew install opencv`, Python + `six`) still says desktop examples need `MEDIAPIPE_DISABLE_GPU=1` "as desktop GPU is currently not supported". In other words, CPU-only C++ on macOS. It also notes a glog conflict (`brew uninstall --ignore-dependencies glog`). — [MediaPipe install guide](https://developers.google.com/edge/mediapipe/framework/getting_started/install)
- **Tasks C API** exists in-tree at `mediapipe/tasks/c/vision/`: `face_detector`, `face_landmarker`, `gesture_recognizer`, `hand_landmarker`, `holistic_landmarker`, `image_classifier`, `image_embedder`, `image_segmenter`, `object_detector`, `pose_landmarker`, `interactive_segmenter_legacy` (directory listing via GitHub API, Sept 2026). The Holistic Landmarker C API was added in v0.10.33. — [mediapipe/tasks/c/vision](https://github.com/google-ai-edge/mediapipe/tree/master/mediapipe/tasks/c/vision); [releases](https://github.com/google-ai-edge/mediapipe/releases)
- The C API hand landmarker has **no GPU support**. Feature request #5712 (opened 2024-10-31) is still "awaiting Googler". — [Issue #5712](https://github.com/google-ai-edge/mediapipe/issues/5712)
- Build fragility examples:
  - Feb 2026: on macOS Tahoe 26.0, Bazel 6.5.0 failed with `dyld: missing LC_UUID` in `wrapped_clang`. The fix was bumping to Bazel 6.6.0 (MediaPipeUnityPlugin v0.16.3). — [homuler/MediaPipeUnityPlugin #1428](https://github.com/homuler/MediaPipeUnityPlugin/issues/1428)
  - The ofxMediaPipe build script must patch MediaPipe because on macOS "`opencv_macos.BUILD` and `WORKSPACE` are pinned to an OpenCV 3 under an Intel Homebrew prefix". The author calls these "upstream portability gaps". — [n1ckfg/ofxMediaPipe README](https://github.com/n1ckfg/ofxMediaPipe)
  - **Outdated (2021–2023)**: issue #2798 (Nov 2021) said MediaPipe "doesn't support arm macOS" — [#2798](https://github.com/google/mediapipe/issues/2798). A Gateway240 blog fix for `darwin` versus `darwin_x86_64` config mismatches applied to v0.9.x — [Gateway240](https://gateway240.com/blog/mediapipe-macos-build-failure/). Both are superseded by arm64 wheels and the Bazel 7 migration, but they show the class of problems.
- Hand Landmarker model: palm detector plus a landmark model on the cropped hand, with tracking that avoids re-running palm detection every frame in VIDEO/LIVE_STREAM modes. Output per hand: 21 landmarks in image coordinates, **world coordinates (metric)**, and handedness. Options: `num_hands` (default 1), `min_hand_detection_confidence`, `min_hand_presence_confidence`, `min_tracking_confidence` (0.5 defaults). Input 192/224 px. Pixel 6 latency is 17.12 ms CPU / 12.27 ms GPU. — [Google AI Edge: Hand landmarker guide](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker)
- Gesture Recognizer canned classes (in `gesture_recognizer.task`): None, Closed_Fist, Open_Palm, Pointing_Up, Thumb_Down, Thumb_Up, Victory, ILoveYou. — [ofxMediaPipe README](https://github.com/n1ckfg/ofxMediaPipe)
- Face Landmarker: 478 3D landmarks, 52 blendshape scores, and 4×4 facial transformation matrices "for effects rendering". — [Google AI Edge: Face landmarker guide](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker)
- The old `mp.solutions` (Hands, FaceMesh, etc.) are labeled "MediaPipe Legacy Solutions". New code should use Tasks (`HandLandmarker`, `FaceLandmarker`). — [MediaPipe legacy docs](https://mediapipe.readthedocs.io/en/latest/solutions/hands.html)

### Inferences
- The most practical way to get MediaPipe in native C/C++ on a Mac in 2026 is: build `libmediapipe_tasks_vision.dylib` once (with ofxMediaPipe's script or a similar Bazel target), then call the C API from C++, Swift or Rust. Wrapping the C API rather than the C++ API avoids leaking protobuf/absl headers into the app. Expect to lose a day or two on toolchain issues, and CPU-only inference.
- An alternative that skips Bazel: load the `.task` bundle's inner `.tflite` files (palm detector plus hand landmark) directly in LiteRT, ONNX Runtime or Core ML after conversion, then reimplement the glue in your own code: anchors/SSD decoding, NMS, ROI rotation/crop, landmark un-projection, tracking. This is the best "learn the pipeline" exercise, but it means rewriting what MediaPipe's graph does.
- For quick iteration, Python `mediapipe` (arm64 wheels) plus OpenCV capture is the fastest way to validate the geometry (rectangle or cube from fingertips) before porting.

### Gaps
- There is no official prebuilt MediaPipe C/C++ library for macOS. "Remove MacOS prebuilts" in v1.0.0 suggests even fewer prebuilt artifacts, but the release notes did not say exactly which artifacts were removed.
- I found no measured desktop Apple Silicon latency for MediaPipe C++ (CPU/XNNPACK) Hand Landmarker.
- It is unclear whether the MediaPipe Python wheel on macOS offers any GPU (Metal) delegate for vision tasks. The docs only state that desktop GPU is unsupported for the C++ framework.

---

## 3. OpenCV C++ for capture and image processing; OpenCV DNN / YuNet

### Takeaway
OpenCV is the standard C++ glue for capture (`cv::VideoCapture` over AVFoundation), CPU image processing, drawing and warping. For example, `getPerspectiveTransform` plus `warpPerspective` can map an image or filter onto the finger-defined quad. OpenCV 5.0 (June 2026) rewrote the DNN engine, so running modern ONNX models (YuNet, YOLO, RTMPose) inside OpenCV is far more viable than in 4.x. It is CPU-centric on Mac, though, with no Neural Engine or Metal backend.

### Cited Findings
- **OpenCV 5.0.0 released 2026-06-06**, with 4.14.0 on 2026-07-19 still maintained (GitHub API). — [opencv/opencv releases](https://github.com/opencv/opencv/releases)
- 5.0 has a new DNN engine that runs alongside the classic one: better dynamic shapes and subgraphs, ONNX operator coverage raised from ~22% (4.x) to 80%+, engine modes `ENGINE_CLASSIC`, `ENGINE_NEW`, `ENGINE_AUTO`, `ENGINE_ORT` (ONNX Runtime), and built-in LLM/VLM support. Tuned CPU paths are Intel IPP, **Arm KleidiCV**, Qualcomm FastCV and RISC-V RVV. — [CNX Software (2026-06-10)](https://www.cnx-software.com/2026/06/10/opencv-5-release-new-dnn-engine-with-enhanced-onnx-and-llm-vlm-support-intel-arm-and-risc-v-hardware-optimizations/); [Phoronix](https://www.phoronix.com/news/OpenCV-5.0-Released); [OpenCV 5 deep dive](https://opencv.org/opencv-5/)
- **YuNet** (via `cv::FaceDetectorYN`): MIT license, bounding box plus 5 landmarks, WIDER Face AP 0.834/0.824/0.708 (easy/medium/hard). Variants: `face_detection_yunet_2023mar.onnx` (fixed shape; OpenCV 4.x), int8 and block-quantized versions, and a new `face_detection_yunet_2026may.onnx` with dynamic H/W for OpenCV 5.x. A C++ demo is included. — [opencv_zoo YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet)
- A community C++ YuNet + SFace project reports ~30 FPS with one face at 640×480. Hardware is not stated. — [aryanoff2112-art/face_detection](https://github.com/aryanoff2112-art/face_detection)

### Inferences
- OpenCV teaches the CPU side of video: the `cv::Mat` layout, BGR versus RGB, conversions, resize/letterbox for model input, and homographies. It hides the GPU and zero-copy side, since `VideoCapture` hands you a CPU `Mat` copy.
- For this demo, OpenCV is good for prototyping the geometry: `warpPerspective` a texture or filter into the 4-point finger quad, or `projectPoints`/`solvePnP` for a pseudo-3D cube from 3–4 fingertip points. Use it alongside a real hand model, because OpenCV ships no hand landmark model.
- On Apple Silicon, `ENGINE_ORT` plus ONNX Runtime's CoreML EP (section 5) is the likely route to Neural Engine acceleration inside an OpenCV app. That is inferred from the engine list and not verified.

### Gaps
- No published YuNet or OpenCV 5 DNN latency figures on Apple M-series chips were found.
- It was not confirmed whether OpenCV 5's `ENGINE_ORT` passes through ONNX Runtime execution providers (CoreML EP) or uses only the CPU EP.

---

## 4. Creative-coding frameworks and engines (openFrameworks, Cinder, Processing, nannou, TouchDesigner, Unity, Godot)

### Takeaway
All of these can host the demo, but on macOS most get hand tracking by bridging to MediaPipe: native C API, Python via pybind or OSC/UDP, or an embedded browser running MediaPipe WASM. openFrameworks has a new native C-API addon (very young). TouchDesigner's plugin (embedded Chromium plus MediaPipe web, GPU, 720p cap) is the most polished "it just works" option and explains the viral hand-tracking art. Unity's homuler plugin is the most complete MediaPipe port. For learning low-level video, these frameworks hide the parts you want to learn, except oF/Cinder when you write your own shaders.

### Cited Findings
**openFrameworks (C++)**
- Latest stable is 0.12.1 (2025-05-02). Nightlies are still published (2026-09-27). — [openFrameworks releases](https://github.com/openframeworks/openFrameworks/releases)
- oF is built on OpenGL. On macOS, OpenGL is deprecated and stops at 4.1. — [Wikipedia: openFrameworks](https://en.wikipedia.org/wiki/OpenFrameworks); [carette.xyz "OpenGL and C++ on M1 Mac"](https://carette.xyz/posts/opengl_and_cpp_on_m1_mac/)
- **ofxMediaPipe (n1ckfg)**: wraps the MediaPipe **Tasks Vision C API**, deliberately avoiding the C++ API "to avoid dragging protobuf and absl headers". It provides `PoseLandmarker` (33 landmarks, normalized plus world), `GestureRecognizer` (21 landmarks, gesture label, handedness), and a threaded `Tracker`. A build script fetches the pinned Bazel, patches MediaPipe and outputs `libmediapipe_tasks_vision.dylib` on macOS. Verified with v0.10.35 on a Raspberry Pi. **Very new and niche** (1 GitHub star, last push 2026-09-09), and no face landmarker wrapper yet. — [n1ckfg/ofxMediaPipe](https://github.com/n1ckfg/ofxMediaPipe)
- **ofxMediaPipePython (design-io)**: runs Python MediaPipe inside oF via pybind, on macOS/Linux with oF ≥ 0.12.0. Last push 2026-03-19. — [design-io/ofxMediaPipePython](https://github.com/design-io/ofxMediaPipePython)
- An older pattern streams MediaPipe landmarks to oF over UDP. — [madelinegannon/example-mediapipe-udp](https://github.com/madelinegannon/example-mediapipe-udp)

**Cinder (C++)**
- v0.9.3 was released 2025-11-02, the first release since v0.9.2 (2020-04-12). — [Cinder releases](https://github.com/cinder/Cinder/releases)

**Processing (Java)**
- Processing 4.5.7 was released 2026-09-24 and is actively maintained. — [processing4 releases](https://github.com/processing/processing4/releases)

**nannou (Rust)**
- nannou **0.20.0 (2026-06-22)** is a major rework that runs nannou as a **Bevy plugin**. — [nannou releases](https://github.com/nannou-org/nannou/releases); [nannou issue #1048](https://github.com/nannou-org/nannou/issues/1048)

**TouchDesigner (context only, node-based)**
- Torin Blankensmith's plugin (with Dom Scott) is a "GPU Accelerated, self-contained MediaPipe Plugin for TouchDesigner" for Mac and PC with no install. It covers all MediaPipe vision models except Interactive Segmentation and Image Embedding. Architecture: a local web server, an **embedded Chromium** running MediaPipe via WebAssembly/WebGL, and landmark JSON sent back over a **WebSocket**. Input is capped at 720p. Latest release v0.5.3 (2026-08-10). — [torinmb/mediapipe-touchdesigner](https://github.com/torinmb/mediapipe-touchdesigner); [Derivative tutorial](https://derivative.ca/community-post/tutorial/face-hand-pose-tracking-more-touchdesigner-mediapipe-gpu-plugin/68278)
- Torin teaches TouchDesigner and creative coding at Parsons. — [Derivative / search summary](https://derivative.ca/community-post/tutorial/mediapipe-touchdesigner/72830)

**Unity (C#)**
- homuler/MediaPipeUnityPlugin: latest v0.16.3 (2025-11-08). Supports macOS x86_64 and **arm64**. The iOS framework is no longer bundled in the unitypackage. Building it yourself on macOS Tahoe needed a Bazel 6.6.0 bump (Feb 2026). — [releases](https://github.com/homuler/MediaPipeUnityPlugin/releases); [#1428](https://github.com/homuler/MediaPipeUnityPlugin/issues/1428)
- Unity's ONNX runtime lineage: Barracuda, then **Sentis** (open beta Nov 2023), renamed **Inference Engine** with Unity 6.2 (Aug 2025), then the display name reverted to **Sentis** as of package 2.4 (the package id stays `com.unity.ai.inference`). It runs ONNX models on CPU/GPU. — [Unity Discussions](https://discussions.unity.com/t/did-inference-engine-package-revert-to-the-old-sentis-name/1695183); [Sentis 2.6.1 changelog](https://docs.unity3d.com/Packages/com.unity.ai.inference@2.6/changelog/CHANGELOG.html); [Meta Horizon docs](https://developers.meta.com/horizon/documentation/unity/unity-pca-sentis/)

**Godot**
- GDMP (GDExtension MediaPipe plugin): v0.6 released 2025-09-16, MIT license. — [j20001970/GDMP](https://github.com/j20001970/GDMP); [GDMP releases](https://github.com/j20001970/GDMP/releases)

### Inferences
- If the goal is a viral-looking result fast, TouchDesigner or Unity win. If the goal is to learn, oF or Cinder plus your own GLSL gives a C++ graphics playground, but on Mac it is stuck on deprecated OpenGL 4.1, which is a real negative for learning modern GPU work compared with Metal or wgpu.
- The TouchDesigner plugin's architecture (browser WASM → WebSocket JSON) adds serialization and inter-process latency. That is fine for art, but it is the opposite of a low-level pipeline.
- A pragmatic C++ creative-coding stack for Mac in 2026: oF 0.12.1 + ofxMediaPipe (C API dylib) for hands and pose, + a GLSL shader for the quad fill. Budget time for the MediaPipe build.
- Barracuda should be considered deprecated (superseded by Sentis since 2023). That is inferred from the rename chain above; no explicit deprecation notice was fetched.

### Gaps
- GDMP's macOS arm64 support and supported Godot version were not confirmed (README fetch lacked platform details).
- Processing: I found no maintained native (non-OSC) MediaPipe or hand-tracking library for Processing 4 in 2026.
- Cinder: no maintained MediaPipe block found.
- No FPS or latency measurements were found for any of these integrations on Apple Silicon.

---

## 5. Alternative models and runtimes (ONNX Runtime/CoreML EP, Core ML, YOLO pose, RTMPose/RTMW, LiteRT, HaMeR/WiLoR/MANO, Depth Anything v2)

### Takeaway
For 2D hand keypoints, MediaPipe's models (via LiteRT or converted) and Apple Vision remain the best real-time choices. YOLO26-pose (you must train on the hand-keypoints dataset; AGPL plus a CC BY-NC-SA dataset) and RTMPose-hand/RTMW (Apache-2.0, ONNX) are the main open alternatives. True 3D hand meshes (HaMeR, WiLoR, MANO) are research-grade: heavy ViT backbones and non-commercial MANO licensing. One brand-new, unvetted repo claims ~30 FPS HaMeR on an M4 Neural Engine. Depth Anything V2-small runs at ~25–33 ms on M-series Neural Engines via Apple's own Core ML conversion, which is borderline real-time for adding scene depth.

### Cited Findings
**ONNX Runtime + CoreML EP**
- ONNX Runtime latest is v1.30.0 (2026-09-10). — [onnxruntime releases](https://github.com/microsoft/onnxruntime/releases)
- CoreML EP: macOS 10.15+/iOS 13+. `ModelFormat` is `MLProgram` (macOS 12+, more ops: LayerNorm, GridSample, ConvTranspose…) or `NeuralNetwork`. `MLComputeUnits` is `CPUOnly`, `CPUAndNeuralEngine`, `CPUAndGPU` or `ALL`. Other options: `RequireStaticInputShapes`, `ModelCacheDirectory`. "Performance may be negatively impacted by inputs with dynamic shapes." C++ usage: `so.AppendExecutionProvider("CoreML", {{"ModelFormat","MLProgram"},{"MLComputeUnits","ALL"}})`. — [ONNX Runtime CoreML EP docs](https://onnxruntime.ai/docs/execution-providers/CoreML-ExecutionProvider.html)

**LiteRT (ex-TFLite), for running MediaPipe `.tflite` models directly**
- LiteRT v2.2.0 was released 2026-08-13. — [LiteRT releases](https://github.com/google-ai-edge/LiteRT/releases)
- The Core ML delegate is "only tested on iOS but not macOS". The Metal GPU delegate works on macOS, but a Sept 2026 bug report on an M4 Max shows it computing wrong values for certain ADD broadcasts. — [LiteRT Core ML delegate docs](https://ai.google.dev/edge/litert/ios/coreml); [LiteRT issue #10231](https://github.com/google-ai-edge/LiteRT/issues/10231)
- LiteRT GPU is claimed to average 1.4× faster than the legacy TFLite GPU delegate. — [Google Developers Blog: LiteRT](https://developers.googleblog.com/litert-the-universal-framework-for-on-device-ai/)

**Ultralytics YOLO (YOLO11 → YOLO26) pose**
- Current model family is **YOLO26**. Pose models export to ONNX, CoreML (now with integrated NMS for pose/seg), TensorRT, OpenVINO and LiteRT. Ultralytics ships releases almost daily (v8.4.164 on 2026-09-27). — [Ultralytics CoreML export](https://docs.ultralytics.com/integrations/coreml); [Pose task docs](https://docs.ultralytics.com/tasks/pose); [releases](https://github.com/ultralytics/ultralytics/releases)
- Hand Keypoints dataset: 26,768 images (18,776 train / 7,992 val), 21 keypoints per hand, **auto-labeled with MediaPipe**, license **CC BY-NC-SA 4.0**. **Ultralytics does not ship pretrained hand weights**. The docs example is `YOLO("yolo26n-pose.pt").train(data="hand-keypoints.yaml", epochs=100, imgsz=640)`. The framework is **AGPL-3.0**. — [Ultralytics hand-keypoints docs](https://docs.ultralytics.com/datasets/pose/hand-keypoints/)
- A community-trained YOLO11n-pose hand model exists. — [chrismuntean/YOLO11n-pose-hands](https://github.com/chrismuntean/YOLO11n-pose-hands)

**RTMPose / RTMW (OpenMMLab)**
- RTMW is whole-body (133 keypoints, including 2×21 hand keypoints). RTMW-l is "the first open-source model to surpass 70 mAP on COCO-WholeBody" while real-time. — [RTMW paper arXiv 2407.08634](https://arxiv.org/abs/2407.08634)
- rtmlib runs RTMPose, RTMO, RTMW, DWPose and ViTPose without mmcv/mmpose. It includes a 21-keypoint RTMPose hand model ("RTMPose-m 256×256", 83.9 AUC) plus an RTMDet-nano hand detector. Backends: onnxruntime, opencv, openvino, tensorrt (no Core ML listed). Apache-2.0. Last push 2026-08-03. — [Tau-J/rtmlib](https://github.com/Tau-J/rtmlib)

**3D hand mesh (MANO-based)**
- **HaMeR** uses a ViT-H backbone plus a transformer head that regresses MANO pose/shape and camera. The heavy backbone is its known speed problem. — [OmniHands arXiv 2405.20330](https://arxiv.org/html/2405.20330v3); repo last push 2026-02-07 — [geopavlakos/hamer](https://github.com/geopavlakos/hamer)
- **Fast-HaMeR** (arXiv 2603.16444, Mar 2026): knowledge distillation to backbones about 35% of the original size gives 1.5× faster inference for ~0.4 mm accuracy loss. — [arXiv 2603.16444](https://arxiv.org/pdf/2603.16444)
- **fasterhamer** claims ~30 FPS end-to-end with **two hands at 640 px on a fanless M4 MacBook Air**. The whole HaMeR (ViT-H + MANO) runs as one Core ML program on the Neural Engine with 6-bit palettized weights, and a ~1 ms "fasthands" detector. Code is MIT, but MANO weights need non-commercial research registration. **Caveat: 0 stars, pushed 2026-09-27. These are unverified author claims.** — [VimalMollyn/fasterhamer](https://github.com/VimalMollyn/fasterhamer)
- **WiLoR** (2024): real-time fully convolutional hand detector (138 FPS medium / 175 FPS small on RTX 4090, 7 MB) plus a ViT-L transformer reconstruction. FreiHAND PA-MPJPE is 5.5 mm, beating HaMeR, with lower jitter on video without temporal modules. **The paper gives no end-to-end FPS.** The paper is licensed CC BY-NC-ND 4.0. — [arXiv 2409.12259](https://arxiv.org/html/2409.12259v2); repo last push 2026-04-07 — [rolpotamias/WiLoR](https://github.com/rolpotamias/WiLoR)

**Depth Anything V2 (for true scene depth)**
- Apple's own Core ML conversion of DA-V2-small: 24.8M params, fixed 518×396 input, F16 49.8 MB. Neural Engine latency: **M1 Max 32.80 ms, M3 Max 24.58 ms**, iPhone 15 Pro Max 33.90 ms. Apache-2.0. — [apple/coreml-depth-anything-v2-small (Hugging Face)](https://huggingface.co/apple/coreml-depth-anything-v2-small)

### Inferences
- For the cube demo, the cheapest route to "true-ish 3D" is MediaPipe world landmarks (metric, hand-centric) plus a projected depth scale from hand size. Adding Depth Anything V2 at ~30–40 fps on an M-series ANE gives relative scene depth for occlusion (e.g., the cube hidden behind fingers), which costs roughly one frame of budget at 30 fps.
- Mesh models (HaMeR/WiLoR) are worth exploring only as a stretch goal. They give MANO meshes for "hand occludes virtual object" effects, but licensing (MANO non-commercial; WiLoR paper CC BY-NC-ND) and runtime cost make them unsuitable as the core tracker.
- YOLO26-pose on hands is mainly educational: training your own keypoint model and exporting to Core ML shows the full training → export → on-device loop. It will likely not beat MediaPipe or Vision hand trackers on jitter, since it has no dedicated tracking stage (inference, not benchmarked).
- ONNX Runtime + CoreML EP (C++, or Rust via `ort`) is the most portable "bring any model" runtime on Mac. Native `coremltools` conversion plus the Core ML API is the most efficient but Apple-only.

### Gaps
- There are no independent Apple Silicon latency benchmarks for MediaPipe hand models under LiteRT/ORT, RTMPose-hand, YOLO26n-pose-hand, or WiLoR.
- The fasterhamer 30 FPS claim is unreplicated.
- Whether Depth Anything V2's larger variants (base/large) have official Core ML ports and latencies was not checked.

---

## 6. Rust as a learning path (nokhwa, ort, wgpu, nannou, objc2-vision)

### Takeaway
Rust is viable end-to-end on Mac in 2026: `nokhwa` for AVFoundation capture with wgpu texture output, `ort` 2.0 RC for ONNX Runtime with the CoreML EP, `wgpu` for rendering over Metal, and `nannou` 0.20 (Bevy) for creative coding. `objc2-vision` gives access to Apple Vision's `VN*` hand, face and body requests. There is no MediaPipe crate, so you port the pre/post-processing yourself. That is harder, but it teaches the most.

### Cited Findings
- **nokhwa** 0.10.11 (2026-05-15): cross-platform webcam capture with native backends (AVFoundation on macOS, working frame capture, querying and capability detection). Features `input-native` and `output-wgpu` (direct frame → `wgpu::Texture`). Low-level backends are in `nokhwa::backends::capture::*`. — [l1npengtul/nokhwa](https://github.com/l1npengtul/nokhwa); [releases](https://github.com/l1npengtul/nokhwa/releases); [lib.rs](https://lib.rs/crates/nokhwa)
- **ort** (pyke) is **still a release candidate**: v2.0.0-rc.13 (2026-07-28), documented as wrapping ONNX Runtime 1.28. The `coreml` cargo feature registers the CoreML EP with options such as compute units and subgraphs. Alternative pure-Rust backends: `ort-candle`, `ort-tract`, plus `ort-web`. — [pykeio/ort releases](https://github.com/pykeio/ort/releases); [docs.rs/ort](https://docs.rs/ort/latest/ort/); [ort execution providers](https://ort.pyke.io/perf/execution-providers)
- **Outdated**: search results still surface ort 1.13–1.16 docs (2023). Those APIs differ from 2.0. — [crates.io ort 1.16.3](https://crates.io/crates/ort/1.16.3)
- **objc2-vision** 0.3.2 (Aug 2026): auto-generated bindings to Apple's Vision framework (aarch64-apple-darwin and others), including `VNDetectHumanHandPoseRequest` and `VNDetectHumanBodyPoseRequest`. The Swift-only API (`DetectHumanHandPoseRequest`) is **not** available. — [docs.rs objc2-vision](https://docs.rs/objc2-vision/latest/objc2_vision/)
- **nannou** 0.20.0 (2026-06-22) is rebuilt as a Bevy plugin. — [nannou releases](https://github.com/nannou-org/nannou/releases)

### Inferences
- Suggested Rust stack: nokhwa (capture, NV12/YUYV → RGB yourself or via its decoders) → resize/letterbox → `ort` + CoreML EP running MediaPipe palm+landmark models converted to ONNX (or objc2-vision for Apple's hand pose) → wgpu render pass with a WGSL shader filling the finger quad and drawing a cube. This forces you to handle pixel formats, stride/row padding, CPU↔GPU upload, a threaded capture and inference pipeline, and latency. Those are the fundamentals.
- Because `ort` 2.0 is still an RC and nannou just did a major rewrite, expect API churn and thin examples. The learning curve is the steepest of all options.
- Since `objc2-vision` exposes only the legacy `VN*` API, you would miss the updated Swift-only features. The WWDC25 hand model may or may not be reachable depending on how Apple versioned it (see section 1 gaps).

### Gaps
- I did not verify whether ort's prebuilt macOS binaries include the CoreML EP or whether a source build is needed. An older doc snippet said CoreML required a "system" (self-compiled) strategy in 1.x.
- No Rust MediaPipe-style hand tracking reference implementation was found.

---

## 7. Which stack best teaches real-time video processing fundamentals; overall comparison

### Takeaway
To learn the fundamentals (pixel buffers, YCbCr color spaces, zero-copy GPU textures, shaders, latency pipelines), the best Mac path is **Swift + AVFoundation + Vision + Metal (MTKView)**, then optionally porting the tracker to **ONNX Runtime/Core ML with hand-written pre/post-processing**. **Rust (nokhwa + ort + wgpu)** teaches the same concepts cross-platform at a higher difficulty. MediaPipe C++, TouchDesigner and Unity hide the pipeline. OpenCV teaches the CPU side only.

### Cited Findings
- The zero-copy capture-to-Metal pipeline (`CVPixelBuffer` → `CVMetalTextureCache` → `MTLTexture`, 420YpCbCr8 bi-planar full range) is Apple's documented approach for real-time camera rendering. — [Apple CVMetalTextureCache](https://developer.apple.com/documentation/corevideo/cvmetaltexturecache-q3j); [MetalVideoCapture sample](https://developer.apple.com/library/archive/samplecode/MetalVideoCapture/Listings/MetalVideoCapture_AAPLRenderer_mm.html)
- Vision consumes `CMSampleBuffer` directly from the capture delegate, and developers must handle coordinate conversion (normalized, lower-left origin). — [WWDC20 10653](https://developer.apple.com/videos/play/wwdc2020/10653/)
- nokhwa exposes raw capture backends and wgpu texture output. — [nokhwa](https://github.com/l1npengtul/nokhwa)
- The TouchDesigner MediaPipe plugin runs detection in an embedded browser and returns JSON over WebSocket. — [torinmb/mediapipe-touchdesigner](https://github.com/torinmb/mediapipe-touchdesigner)
- MediaPipe desktop C++ on macOS is CPU-only. — [MediaPipe install guide](https://developers.google.com/edge/mediapipe/framework/getting_started/install)
- OpenGL on macOS is deprecated and capped at 4.1, which affects oF, Cinder and Processing's GL renderers. — [carette.xyz](https://carette.xyz/posts/opengl_and_cpp_on_m1_mac/)

### Inferences (comparison matrix; ratings are my synthesis of the cited facts, not measured)

| Stack | Hands | Face | 3D | Learning curve | Perf on Apple Silicon | Teaches low-level video |
|---|---|---|---|---|---|---|
| Swift + AVFoundation + Vision + Metal/RealityKit | 21 pts ×N, chirality, confidence | 76-pt landmarks, pitch/yaw/roll, segmentation | 3D body only (17 joints); hands 2D | Medium (Swift + Metal) | Native, OS-optimized (no published numbers) | **High** (pixel buffers, YCbCr, zero-copy textures, shaders) |
| MediaPipe C++/C API (Bazel) | 21 pts + metric world coords, gestures | 478 pts + 52 blendshapes + 4×4 matrix | Metric hand world landmarks | **High** (Bazel/toolchain) | CPU-only on macOS desktop | Medium (graph abstracts the pipeline) |
| MediaPipe Python + OpenCV | same | same | same | Low | CPU | Low–medium |
| OpenCV C++ (5.0 DNN) + ONNX models | via RTMPose/YOLO/MP-converted | YuNet (5 pts) | via solvePnP | Medium | CPU (KleidiCV), ANE via ORT unclear | Medium (CPU side only) |
| ONNX Runtime/Core ML + own pre/post | any model | any | any (DA-V2, HaMeR) | High | ANE via CoreML EP | **High** (tensors, letterboxing, NMS, decoding) |
| Rust: nokhwa + ort + wgpu (+nannou) | via ONNX or objc2-vision | same | same | **Highest** | ANE via CoreML EP; Metal via wgpu | **High** (cross-platform GPU) |
| openFrameworks + ofxMediaPipe | MP (C API) | not wrapped yet | MP world pose | Medium–high (build) | CPU MP + OpenGL 4.1 | Medium |
| TouchDesigner + Torin's plugin | MP web | MP web | limited | Low (nodes) | GPU (WebGL), 720p cap | Low |
| Unity + homuler plugin / Sentis | MP full | MP full | Unity 3D | Medium | good | Low |

- **Suggested progression for the stated goal** (a learning-oriented dev on an Apple Silicon Mac):
  1. Prototype the geometry in 1–2 days with Python MediaPipe Tasks + OpenCV. Rectangle: order the 4 points from both hands' thumb and index tips and fill it with `fillPoly` or `warpPerspective`. Cube: 3 fingertips give an origin plus two edge vectors, and the cross product gives the third.
  2. Rebuild natively: Swift, AVCaptureSession → `AVCaptureVideoDataOutput` (NV12) → Vision `DetectHumanHandPoseRequest` (2 hands) → Metal. Pass the quad corners as uniforms, run a fragment shader that applies a filter inside the quad, and render the cube with a simple Metal vertex pipeline (or RealityKit for less code). Add smoothing (One-Euro or EMA) plus pinch-style evidence counters for gesture state. Add `VNDetectFaceLandmarksRequest` and person segmentation for face and background effects.
  3. Stretch goals: swap the tracker for MediaPipe models via ONNX Runtime/Core ML to learn model I/O. Add Depth Anything V2 (~25–33 ms on ANE) for occlusion. Try HaMeR/WiLoR for a hand mesh.
  4. Optional: port to Rust (nokhwa + ort + wgpu) to learn the same pipeline without Apple's conveniences.
- Latency pipeline lesson common to every stack: run capture, inference and render on separate queues or threads, drop late frames (Vision/AVFoundation `alwaysDiscardsLateVideoFrames`-style behavior), and render the newest landmarks over the newest frame. This is inferred general practice, not from a fetched source.

### Gaps
- No head-to-head benchmark (same Mac, same camera) of Vision versus MediaPipe versus YOLO/RTMPose hand tracking exists in the sources found. Accuracy and jitter comparisons are therefore qualitative.
- I found no authoritative source on end-to-end camera-to-photon latency for any of these stacks on macOS.
