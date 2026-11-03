# Python stack for real-time webcam hand/face tracking, gestures and 3D AR overlay on macOS Apple Silicon (state as of 2026-09-27)

Method note: besides web and GitHub sources, several claims below were checked by hand in this session on the target platform: Apple M2 Pro, macOS 26.6.2 (build 25G83), CPython 3.12.6, arm64. I installed packages with `uv` into throwaway venvs and ran the code. These appear as "[Local test, this session]". Benchmarks feed one static 640x480 image repeatedly in VIDEO mode, so they measure inference only (no camera capture, no drawing), with tracking active after the first frames. Versions and dates come from the PyPI JSON API, queried 2026-09-27.

## 1. MediaPipe in Python: legacy "Solutions" vs. Tasks API, versions, macOS/GPU, outputs, FPS

### Takeaway
The legacy `mp.solutions.*` API is **gone**. It was removed from the pip package in 0.10.30 (Dec 2025), and support had already ended on 2023-03-01. All new code has to use the MediaPipe Tasks API (`mediapipe.tasks.python.vision.HandLandmarker / FaceLandmarker / GestureRecognizer / PoseLandmarker / HolisticLandmarker`). On Apple Silicon the current wheel is **1.0.1 (2026-08-14)**, and it has a serious regression: the CPU path aborts for every landmarker. There are two workarounds:
- Use the GPU (Metal) delegate with SRGBA input. This works and is very fast (~3–5 ms/frame).
- Pin `mediapipe==1.0.0` or `0.10.35`, where the CPU path works (~24 ms hands, ~8 ms face).

### Cited Findings
**Versions and packaging**
- Latest PyPI release is `mediapipe 1.0.1` (uploaded 2026-08-14). Earlier: 1.0.0 (2026-07-27), 0.10.35 (2026-04-27), 0.10.33 (2026-03-18), 0.10.32 (2026-01-22), 0.10.31 (2025-12-18), 0.10.30 (2025-12-16), 0.10.21 (2025-02-06). PyPI still marks the package "Development Status :: 3 - Alpha" — [PyPI mediapipe](https://pypi.org/project/mediapipe/)
- From 0.10.30 on, the macOS wheels are a single `py3-none-macosx_11_0_arm64.whl`: pure-Python bindings over a C library, not tied to a CPython ABI. No macOS x86_64 (Intel) wheel is published for ≥0.10.30. Up to 0.10.21 the wheels were per-CPython (cp39–cp312) `universal2` + `x86_64` — [PyPI mediapipe release files](https://pypi.org/project/mediapipe/#files)
- The Python layer was rewritten on ctypes over the MediaPipe Tasks C API. The 0.10.32 notes include: "Add ctypes structures for Landmark", "Update HandLandmarker to use the C API", "Migrate FaceLandmarker to use C API", "Migrate GestureRecognizers (Python) to use C API", "Removed … HolisticLandmarker from Python (for now), Protobuf dependencies from MediaPipe Python Package and also Python Tasks runners", "Re-add GPU support to Python API", "Improve Python Wheel on Mac and Windows", "Enables ml drift metal delegate as inference calculator backend" — [MediaPipe v0.10.32 release notes](https://github.com/google-ai-edge/mediapipe/releases/tag/v0.10.32)
- 0.10.33 (2026-03-23) notes: "Re-add Holistic Landmarker to Python", "Add support for FULL_RANGE face detection task" — [MediaPipe releases](https://github.com/google-ai-edge/mediapipe/releases)
- 1.0.0 (2026-07-28) notes include "Remove MacOS prebuilts", "Enforce namespacing conventions for MediaPipe Tasks C and Python APIs", "Add EXIF orientation support to MpImageCreateFromFile and the Python Task API", and removal of the Python GenAI components. Despite the "Remove MacOS prebuilts" line, PyPI still ships the macOS arm64 wheel for 1.0.0 and 1.0.1 — [MediaPipe v1.0.0 release](https://github.com/google-ai-edge/mediapipe/releases/tag/v1.0.0); [PyPI](https://pypi.org/project/mediapipe/#files)
- `mediapipe 1.0.1` requires `absl-py~=2.3, numpy, sounddevice~=0.5, flatbuffers~=25.9, opencv-contrib-python, matplotlib`. Classifiers list Python 3.9–3.12, but `requires_python` is unset and the wheel is `py3-none` — [PyPI mediapipe JSON](https://pypi.org/pypi/mediapipe/json)
- A user ran 1.0.1 on Python 3.14.5 and noted "1.0.1 is currently the only mediapipe wheel available for Python 3.14" — [GitHub issue #6356](https://github.com/google-ai-edge/mediapipe/issues/6356)
- Docs moved from ai.google.dev/edge/mediapipe to developers.google.com/edge/mediapipe; ai.google.dev URLs now return 301 — [developers.google.com MediaPipe guide](https://developers.google.com/edge/mediapipe/solutions/guide)

**Legacy Solutions: deprecated, then removed**
- "We have ended support for the MediaPipe Legacy Solutions listed below as of March 1, 2023." Hands, Face Mesh, Face Detection, Iris, Pose, Holistic, Selfie Segmentation and others were "upgraded" to Tasks equivalents — [MediaPipe Solutions guide](https://developers.google.com/edge/mediapipe/solutions/guide)
- The legacy Hands doc carries: "As of March 1, 2023, this solution was upgraded to a new MediaPipe Solution" — [legacy hands.md](https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/hands.md)
- A maintainer (schmidt-sebastian) wrote on 2025-12-23: "We have removed support for MediaPipe Solutions. Please migrate to MediaPipe Tasks". Another Google responder said "The Solutions API has been removed from MediaPipe version 0.10.30 onwards." The trigger was an issue titled "mediapipe 0.10.31 for python does not contain mediapipe.solutions" — [issue #6192](https://github.com/google-ai-edge/mediapipe/issues/6192)
- Duplicate reports of `AttributeError: module 'mediapipe' has no attribute 'solutions'` kept arriving through 2026 (e.g. [#6200](https://github.com/google-ai-edge/mediapipe/issues/6200), [#6241](https://github.com/google-ai-edge/mediapipe/issues/6241), [#6261](https://github.com/google-ai-edge/mediapipe/issues/6261)). The suggested workaround in #6261 is to pin `mediapipe==0.10.21` with Python ≤3.12 — [issue #6261](https://github.com/google-ai-edge/mediapipe/issues/6261)
- Drawing helpers came back in the Tasks namespace in 0.10.32: "We have just added DrawingUtils to 0.10.32. Please refer to the updated notebooks" — [issue #6192 comment](https://github.com/google-ai-edge/mediapipe/issues/6192)
- Import check on each version:
  - 1.0.1: `mp.solutions` does not exist. Top-level attributes are only `Image`, `ImageFormat`, `tasks`.
  - 0.10.35: `hasattr(mp,'solutions')` is False.
  - 0.10.21: it is True.

  — [Local test, this session]

**Tasks API surface (1.0.1)**
Introspected in [Local test, this session]:
- `mediapipe.tasks.python.vision` exports:
  - `FaceDetector`, `FaceLandmarker`, `GestureRecognizer`, `HandLandmarker`, `HolisticLandmarker`, `PoseLandmarker`
  - `ImageSegmenter`, `InteractiveSegmenter`, `ObjectDetector`, `ImageClassifier`, `ImageEmbedder`
  - `RunningMode`, `drawing_utils`, `drawing_styles`
  - `HandLandmarksConnections`, `FaceLandmarksConnections`, `PoseLandmarksConnections`
- `BaseOptions.Delegate` = {CPU, GPU}.
- `RunningMode` = {IMAGE, VIDEO, LIVE_STREAM}.
- `HandLandmarkerOptions(base_options, running_mode=IMAGE, num_hands=1, min_hand_detection_confidence=0.5, min_hand_presence_confidence=0.5, min_tracking_confidence=0.5, result_callback=None)`
- `FaceLandmarkerOptions(..., num_faces=1, min_face_detection_confidence, min_face_presence_confidence, min_tracking_confidence, output_face_blendshapes=False, output_facial_transformation_matrixes=False, result_callback)`
- `GestureRecognizerOptions(..., num_hands, canned_gesture_classifier_options, custom_gesture_classifier_options, result_callback)`
- `vision.drawing_utils.draw_landmarks(image: np.ndarray, landmark_list, connections, landmark_drawing_spec, connection_drawing_spec)`
- `drawing_styles.get_default_hand_landmarks_style()` / `get_default_hand_connections_style()` / face-mesh styles

**Running modes (official docs)**
- IMAGE uses `detect(mp_image)`. VIDEO uses `detect_for_video(mp_image, frame_timestamp_ms)`. LIVE_STREAM uses `detect_async(mp_image, frame_timestamp_ms)` with `result_callback(result, output_image, timestamp_ms)` — [Hand Landmarker Python guide](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python)
- Video and live-stream modes need timestamps. In LIVE_STREAM, "If the detection function is called when the Hand Landmarker task is busy processing another frame, the task will ignore the new input frame" — [Hand Landmarker Python guide](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python)
- Confirmed by [Local test, this session] on 1.0.1 GPU: 300 `detect_async` calls submitted in 0.69 s produced 116 callbacks; the other 184 frames were silently dropped.

**Hand outputs**
- The bundle is "a palm detection model and a hand landmarks detection model". It outputs 21 hand-knuckle keypoints, handedness, and world landmarks.
- In VIDEO/LIVE_STREAM, "Hand Landmarker only re-triggers the palm detection model if the hand landmarks model no longer identifies the presence of hands or fails to track the hands".
- Model input 192x192 / 224x224, float16. Official Pixel 6 latency: 17.12 ms CPU / 12.27 ms GPU.

  — [Hand Landmarker overview](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker)
- Normalized landmarks: x,y in [0,1] by image width/height; z is depth relative to the wrist. World landmarks are "real-world 3D coordinates in meters" — [Hand Landmarker Python guide](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python)
- The legacy doc adds detail:
  - World landmarks have "the origin at the hand's approximate geometric center".
  - For z: "the smaller the value the closer the landmark is to the camera. The magnitude of z uses roughly the same scale as x".
  - "handedness is determined assuming the input image is mirrored, i.e., taken with a front-facing/selfie camera with images flipped horizontally. If it is not the case, please swap the handedness output".

  — [legacy hands.md](https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/hands.md)
- Example output (1.0.1, 2 hands): 21 normalized + 21 world landmarks per hand.
  - Handedness: `[('Right',0.86),('Left',0.92)]`
  - Index tip normalized: `x=0.729, y=0.418, z=-0.033`
  - Index tip world: `x=0.085, y=0.012, z=-0.021` (meters)

  — [Local test, this session]

**Face outputs**
- "478 3-dimensional face landmarks", "52 blendshape scores", and a facial transformation matrix that transforms "face landmarks from a canonical face model to the detected face" for effects rendering.
- The bundle has three models: BlazeFace short-range detector, FaceMesh-V2 (256x256), and a blendshape model; float16.

  — [Face Landmarker overview](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker)
- Confirmed on 1.0.1: 478 landmarks, 52 blendshapes (first names `_neutral, browDownLeft, browDownRight, browInnerUp, browOuterUpLeft`), and a matrix of shape (4,4) — [Local test, this session]

**Gesture Recognizer**
- Canned gestures: `None, Closed_Fist, Open_Palm, Pointing_Up, Thumb_Down, Thumb_Up, Victory, ILoveYou`.
- Pipeline: hand-landmark bundle, then gesture embedding model, then classifier. Can be customized with Model Maker (`.task` format). Output also includes landmarks, world landmarks and handedness.
- Pixel 6 latency: 16.76 ms CPU / 20.87 ms GPU.

  — [Gesture Recognizer overview](https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer)

**Model files**
Downloaded and used in the local test:
- `https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task` (7.8 MB)
- `.../face_landmarker/face_landmarker/float16/latest/face_landmarker.task` (3.8 MB)
- `.../gesture_recognizer/gesture_recognizer/float16/latest/gesture_recognizer.task` (8.4 MB)

— [Local test, this session]

**macOS 1.0.1 CPU crash (critical)**
- Every Tasks Vision graph that contains `TensorsToDetectionsCalculator` (FaceDetector, FaceLandmarker, HandLandmarker, PoseLandmarker) aborts with SIGABRT at graph open on macOS CPU:
  `Check failed: service_ Service is unavailable` in `-[DrishtiMetalHelper initWithCalculatorContext:]`.
- The reporter hit it on an M5 with Python 3.14.5; a commenter reproduced it on an M2 Pro with 3.12.9.
- Bisected: 0.10.35 OK, 1.0.0 OK, 1.0.1 aborts. The issue was closed 2026-09-17 via commit 32d0e5b, but no release after 1.0.1 exists on PyPI as of 2026-09-27.

— [issue #6356](https://github.com/google-ai-edge/mediapipe/issues/6356); [PyPI](https://pypi.org/project/mediapipe/)
- Reproduced here on 1.0.1 for HandLandmarker, FaceLandmarker and GestureRecognizer: CPU delegate, default IMAGE mode, VIDEO mode, SRGB and SRGBA all abort — [Local test, this session]

**GPU (Metal) delegate on macOS**
- `BaseOptions(delegate=BaseOptions.Delegate.GPU)` works on macOS arm64 in both 0.10.35 and 1.0.1. It logs "Created TensorFlow Lite delegate for Metal".
- It requires `mp.ImageFormat.SRGBA` input. On 1.0.1, SRGB input with GPU aborts with `unsupported ImageFrame format: 1`.
- LIVE_STREAM + GPU works on 1.0.1.

— [Local test, this session]

**Measured latency on an Apple M2 Pro**
640x480, VIDEO mode, 200-iteration average, [Local test, this session]:

| mediapipe | Task | CPU (XNNPACK) | GPU (Metal, SRGBA) |
|---|---|---|---|
| 0.10.35 | HandLandmarker (2 hands) | 23.9 ms (~42 fps) | 4.25 ms (~235 fps) |
| 0.10.35 | FaceLandmarker | 7.5 ms (~133 fps) | 4.4 ms (~227 fps) |
| 0.10.35 | GestureRecognizer (2 hands) | 24.2 ms (~41 fps) | 5.0 ms (~201 fps) |
| 0.10.21 (legacy-era wheel, Tasks API) | Hand / Face | 23.7 ms / 8.0 ms | not tested |
| 1.0.1 | Hand (2 hands) | crash | 3.16 ms (~317 fps) |
| 1.0.1 | Face (blendshapes + matrix) | crash | 4.79 ms (~209 fps) |
| 1.0.1 | Gesture (2 hands) | crash | 4.96 ms (~202 fps) |

### Inferences
- Recommended pin for a Mac demo today, in order of preference:
  1. `mediapipe==1.0.0` or `0.10.35`, which have a working CPU path; add the GPU delegate optionally.
  2. `1.0.1` with GPU delegate only, feeding `cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)` into `mp.Image(image_format=mp.ImageFormat.SRGBA, data=...)`.
  3. Upgrade to the next release (>1.0.1) once it ships, since the fix has already merged.
- Avoid 0.10.21 (the last version with `mp.solutions`) except to run old tutorials. It is capped at CPython ≤3.12 and frozen.
- Either CPU or GPU leaves plenty of headroom for 30 fps webcam input. Hand CPU ~24 ms keeps up with 30 fps but not 60. The GPU delegate gives >200 fps inference, so capture and rendering become the bottleneck.
- VIDEO mode (synchronous `detect_for_video` with a monotonically increasing ms timestamp) is the simplest pattern for a demo. The result belongs to the exact frame being drawn, so overlays don't lag or misalign. LIVE_STREAM gives async non-blocking behavior, but results arrive on a callback thread, may be for an older frame, and busy frames are dropped.
- For the rectangle-between-two-hands demo:
  - Normalized landmarks 4 (thumb tip) and 8 (index tip) of each hand, times (w,h), give four 2D pixel points for `cv2.fillPoly`.
  - Handedness labels assume a mirrored image. Call `cv2.flip(frame,1)` before inference, or swap labels.
- For the 3D cube defined by 3 fingertips:
  - World landmarks are metric but hand-centric, with the origin at the hand center, not at the camera. They give hand shape/orientation but not camera-space position.
  - Getting camera-space placement needs either `cv2.solvePnP` between world and image landmarks with approximate camera intrinsics, or treating normalized x,y plus relative z as a pseudo-3D frame.

  (The solvePnP approach is used in the sherbondy gist cited in section 7.)
- The face transformation matrix (4x4) is what you need to anchor 3D objects on the face, e.g. glasses or a hat, in a perspective renderer.

### Gaps
- No official Google statement found on Python version support for the py3-none wheels. The PyPI classifiers (3.9–3.12) look stale.
- No official MediaPipe benchmarks for macOS/Apple Silicon. Only the local measurements above; real webcam end-to-end FPS was not measured.
- Unclear whether "Remove MacOS prebuilts" in the 1.0.0 notes will eventually affect pip wheels.
- No release date announced for the fixed version after 1.0.1.

## 2. OpenCV (opencv-python) for capture, drawing, filters on macOS; limits for 3D

### Takeaway
OpenCV 5.0 (released 2026-06-06; wheels `5.0.0.93`, 2026-07-02, macOS 13+ arm64, abi3 wheel for CPython ≥3.7) is the default for capture (AVFoundation backend), 2D drawing, masks, color filters and perspective warps. It can do "fake 3D": project the 8 cube vertices with `cv2.projectPoints` and draw faces with `fillPoly`. It has no real rasterizer: no depth buffer, lighting or textured meshes.

### Cited Findings
- OpenCV 5.0.0 was released 2026-06-06, timed with CVPR 2026. There is a 4.x to 5.x migration guide. "OpenCV 5.0 is a big release and a foundation"; the new graph engine landed CPU-first — [OpenCV 5 overview](https://opencv.org/opencv-5/); [OpenCV-5 wiki](https://github.com/opencv/opencv/wiki/OpenCV-5)
- `opencv-python` and `opencv-contrib-python` 5.0.0.93 (2026-07-02) ship `cp37-abi3-macosx_13_0_arm64` and `macosx_14_0_x86_64` wheels — [PyPI opencv-python](https://pypi.org/project/opencv-python/)
- `mediapipe 1.0.1` depends on `opencv-contrib-python` — [PyPI mediapipe JSON](https://pypi.org/pypi/mediapipe/json)
- The opencv-python README says to install only one of its package variants per environment — [opencv-python on PyPI](https://pypi.org/project/opencv-python/)
- `cv2.__version__ == '5.0.0'` on arm64.
  - Camera backends: `GSTREAMER, AVFOUNDATION, FFMPEG, UEYE`.
  - `cv2.FaceDetectorYN` and `cv2.FaceRecognizerSF` exist.
  - `fillPoly`, `warpPerspective`, `getPerspectiveTransform`, `solvePnP`, `projectPoints`, `addWeighted`, `applyColorMap` all exist.

  — [Local test, this session]
- On macOS you can force the backend with `cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)`.
  - On a denied permission OpenCV prints "OpenCV: not authorized to capture video (status 0), requesting...".
  - The host app (Terminal, iTerm, VS Code, etc.) must be granted access under System Settings → Privacy & Security → Camera.
  - `tccutil reset Camera` resets the authorization.
  - `OPENCV_AVFOUNDATION_SKIP_AUTH=1` skips OpenCV's own authorization request.

  — [opencv-python issue #291](https://github.com/opencv/opencv-python/issues/291); [opencv issue #16255](https://github.com/opencv/opencv/issues/16255)
- Camera access can fail when Python is launched from some third-party terminals/IDE apps but work in Terminal.app. Example: the Codex app terminal — [openai/codex issue #17361](https://github.com/openai/codex/issues/17361)
- `cv2.imshow` on macOS must be called from the main thread, because Apple UI frameworks are main-thread only. Calling it from worker threads causes "Unknown C++ exception" / NSWindow assertions — [opencv issue #22602](https://github.com/opencv/opencv/issues/22602); [OpenCV Q&A](https://answers.opencv.org/question/83523/python-opencv-31-imshow-fail-when-called-in-different-thread/)

### Inferences
- 2D shape demos need nothing beyond OpenCV + MediaPipe:
  - Colored quad between the hands: `cv2.fillPoly` on an overlay, then `cv2.addWeighted` for transparency.
  - Filter restricted to the region: build a mask with `fillPoly`, then `np.where(mask, filtered, frame)` with `cv2.applyColorMap`, blur, `cv2.Canny`, grayscale, etc.
  - Warping an image or video into the quad: `getPerspectiveTransform` + `warpPerspective` + mask.
- A pseudo-3D cube works in OpenCV alone. Define 3D vertices from the fingertip landmarks, e.g. base edge from index-tip to thumb-tip and height from a third finger. Project with `cv2.projectPoints` or directly with normalized coords, then painter's-sort faces by depth and `fillPoly`. Beyond that (lighting, textures, correct occlusion, smooth anti-aliasing) you need a GPU renderer (section 3).
- The 2026may YuNet model is specifically "OpenCV 5.x compatible" (section 5).

### Gaps
- No source found on typical built-in MacBook/Continuity Camera frame rates and resolutions through `CAP_AVFOUNDATION`, or on the reliability of `CAP_PROP_BUFFERSIZE` there. Not measured, because camera access wasn't exercised in this session.
- I didn't review the OpenCV 5 migration guide for Python-API breaking changes (e.g. module moves) in detail. The basic drawing/geometry APIs above exist in 5.0.0.

## 3. Real 3D rendering over the webcam frame in Python on macOS

### Takeaway
On macOS, OpenGL is frozen at 4.1 core (deprecated since 10.14, now running on top of Metal). Anything OpenGL-based still works, but only up to GL 4.1.
- **moderngl + glfw** (or moderngl-window) is the simplest and most documented route for an AR overlay: a full-screen textured quad for the webcam frame plus a perspective-projected mesh.
- **pygfx on wgpu-py** runs natively on Metal and is the forward-looking choice. It is pre-1.0 and its API still changes.
- pyrender is stale. Open3D, vispy, Panda3D and Ursina work but are less natural for "webcam as background + custom perspective camera".

### Cited Findings
- Apple deprecated OpenGL in macOS 10.14 Mojave and froze it at 4.1 core. OpenGL 4.1 is implemented on top of Metal on Apple Silicon. Tutorials that request 4.5/4.6 contexts fail on Macs — [AppleInsider, 2018-06-28](https://appleinsider.com/articles/18/06/28/why-macos-mojave-requires-metal----and-deprecates-opengl); [Apple retired OpenGL guide](https://developer.apple.com/library/archive/documentation/GraphicsImaging/Conceptual/OpenGL-MacProgGuide/UpdatinganApplicationtoSupportOpenGL3/UpdatinganApplicationtoSupportOpenGL3.html)
- `moderngl 5.12.0` on this M2 Pro:
  - `create_standalone_context(require=330)` gives `GL_VERSION "4.1 Metal - 90.5"`, `GL_RENDERER "Apple M2 Pro"`, `version_code 410`.
  - `require=450` raises `ValueError: Requested OpenGL version 450, got version 410`.

  — [Local test, this session]
- moderngl packaging and activity:
  - `moderngl` 5.12.0 was released 2024-10-17, with wheels cp38–cp313 including `macosx_11_0_arm64`. There is no cp314 wheel.
  - `moderngl-window` 3.1.1 was released 2025-01-19.
  - The repo is active (pushed 2026-07-11, ~2.3k stars, MIT).

  — [PyPI moderngl](https://pypi.org/project/moderngl/); [PyPI moderngl-window](https://pypi.org/project/moderngl-window/); [GitHub moderngl](https://github.com/moderngl/moderngl)
- wgpu-py and pygfx versions:
  - `wgpu` 0.32.0 was released 2026-07-19 and requires Python ≥3.11. It has arm64 macOS wheels.
  - `pygfx` 0.17.0 was released 2026-07-19 and requires Python ≥3.10 (pure Python).
  - `fastplotlib` 0.7.0, built on pygfx, was released 2026-09-24.

  — [PyPI wgpu](https://pypi.org/project/wgpu/); [PyPI pygfx](https://pypi.org/project/pygfx/); [PyPI fastplotlib](https://pypi.org/project/fastplotlib/)
- On the M2 Pro, `wgpu.gpu.request_adapter_sync()` reports the `Apple M2 Pro`, backend `Metal`, `IntegratedGPU` — [Local test, this session]
- pygfx is "built on wgpu, enabling superior performance and reliability compared to OpenGL-based solutions". It has cameras, geometries (incl. box), materials, and texture resources — [pygfx docs](https://docs.pygfx.org/stable/)
- pygfx status and setup:
  - README status: "We're currently working towards version 1.0, which means that the API can change with each version. We expect to reach 1.0 near July 2026 … you should probably pin the Pygfx version". As of 2026-09-27 the latest release is still 0.17.0, so 1.0 has not shipped.
  - Install is `pip install -U pygfx glfw`. It needs "some window to render to": glfw, jupyter_rfb, PyQt/PySide or wx.
  - Repo pushed 2026-09-07, ~877 stars, BSD-2.

  — [pygfx GitHub README](https://github.com/pygfx/pygfx); [PyPI pygfx](https://pypi.org/project/pygfx/)
- Other rendering packages (PyPI data as of 2026-09-27):

| Package | Latest (date) | Notes |
|---|---|---|
| `pyrender` | 0.1.45 (2021-02-18) | Last release in 2021; repo last pushed 2025-02-07 |
| `open3d` | 0.20.0 (2026-09-16) | cp310–cp314 macOS arm64 wheels |
| `vispy` | 0.17.0 (2026-09-08) | cp310–cp315 arm64 wheels |
| `panda3d` | 1.10.16 (2025-12-25) | universal2 wheels |
| `ursina` | 8.3.0 (2025-12-06) | Requires Python ≥3.12 |
| `glfw` | 2.10.2 (2026-07-21) | Bundles an arm64 GLFW |
| `PyOpenGL` | 3.1.10 (2025-08-18) | |
| `pygame` | 2.6.1 (2024-09-29) | Wheels up to cp313 |
| `trimesh` | 5.1.0 (2026-08-31) | |

  — [PyPI pyrender](https://pypi.org/project/pyrender/); [GitHub pyrender](https://github.com/mmatl/pyrender); [PyPI open3d](https://pypi.org/project/open3d/); [PyPI vispy](https://pypi.org/project/vispy/); [PyPI panda3d](https://pypi.org/project/panda3d/); [PyPI ursina](https://pypi.org/project/ursina/); [PyPI glfw](https://pypi.org/project/glfw/); [PyPI PyOpenGL](https://pypi.org/project/PyOpenGL/); [PyPI pygame](https://pypi.org/project/pygame/); [PyPI trimesh](https://pypi.org/project/trimesh/)
- Community AR/3D demos in practice use the older route of PyGame + PyOpenGL (legacy fixed-function GL):
  - JAYP752/Hand-gesture-3d-control: MediaPipe Tasks API + PyGame 2.6 + PyOpenGL 3.1 cube.
  - sherbondy gist: MediaPipe → solvePnP world space → OpenGL via PyGame.

  — [JAYP752/Hand-gesture-3d-control](https://github.com/JAYP752/Hand-gesture-3d-control); [sherbondy gist](https://gist.github.com/sherbondy/58bdd1d8983d9ba96043fea57f9e7429)

### Inferences
- **Best-fit options:**
  1. **moderngl (+ glfw, or moderngl-window)**, GLSL 330/410.
     - Each frame: upload the camera BGR frame to a texture with `texture.write(frame.tobytes())`, draw a full-screen quad with depth test off, then draw the cube/parallelepiped with a perspective matrix (e.g. pyrr/numpy) and depth test on.
     - Mature, small, and works on macOS within GL 4.1. Stay on Python ≤3.13 because there is no cp314 wheel yet.
  2. **pygfx + rendercanvas/glfw** on Metal via wgpu.
     - Update a `gfx.Texture` each frame for the background (e.g. a screen-space image or a background plane); `gfx.Mesh(gfx.box_geometry(...), material)` with a `PerspectiveCamera`.
     - Future-proof on macOS, but pin the version because of pre-1.0 API churn.
- **Legacy option:** PyGame + PyOpenGL. Good enough for quick demos and matches many tutorials, but uses deprecated fixed-function OpenGL. Avoid tutorials requesting GL ≥4.2.
- **Less suitable:**
  - Open3D and vispy are built for scientific/point-cloud visualization. The webcam-background + custom-intrinsics pipeline is possible but awkward.
  - Panda3D and Ursina are game engines. Feeding a webcam texture is doable (Panda3D has texture `setRamImage`), but they own the main loop.
  - pyrender is effectively unmaintained since 2021. Avoid it for new work.
- **Matching the virtual camera to the webcam:**
  - Use a perspective projection whose vertical FOV roughly matches the webcam (~55–70° is typical for laptop cameras; calibrate with `cv2.calibrateCamera` for accuracy).
  - Or skip true 3D placement: build the model directly in normalized device coordinates from the landmarks (x,y from image coords, z from MediaPipe's relative z scaled like x).
- **Alternative to rendering on screen:** render offscreen to an FBO and read the pixels back into NumPy (moderngl `fbo.read()`), composite with OpenCV and show via `cv2.imshow`. Simpler windowing, but costs a GPU→CPU readback each frame.

### Gaps
- Did not verify Open3D 0.20 offscreen rendering support on macOS, or whether Panda3D 1.10.16 has any Metal backend (believed OpenGL-only).
- No benchmark of moderngl vs pygfx per-frame texture-upload latency at 1280x720 on Apple Silicon.
- Did not check pygame-ce (the community fork) availability/status.

## 4. Helper libraries (cvzone etc.) vs. MediaPipe directly

### Takeaway
cvzone 2.0.0 (PyPI, 2026-06-08) was quietly migrated to the MediaPipe Tasks API and gives convenient pixel-space lists, `fingersUp()` and `findDistance()`. It is thin and CPU-only (no delegate option), it silently ignores some constructor arguments, and its GitHub repo lags PyPI. On mediapipe 1.0.1/macOS it therefore hits the CPU crash. For this project, use MediaPipe Tasks directly and copy the few cvzone helpers you need.

### Cited Findings
- `cvzone` release history: 2.0.0 on 2026-06-08, after 1.6.1 on 2023-09-09. It requires only `opencv-python` and `numpy` (mediapipe is not a declared dependency). MIT — [PyPI cvzone](https://pypi.org/project/cvzone/)
- The GitHub repo cvzone/cvzone (~1.3k stars) was last pushed 2024-05-10, and its `HandTrackingModule.py` still uses `mp.solutions.hands` — [GitHub cvzone](https://github.com/cvzone/cvzone)
- The cvzone 2.0.0 wheel imports `mediapipe.tasks.python.vision` in HandTrackingModule, FaceMeshModule, FaceDetectionModule, PoseModule and SelfiSegmentationModule.
  - `HandDetector` auto-downloads `hand_landmarker/float16/1/hand_landmarker.task` into the CWD.
  - It creates `HandLandmarkerOptions(base_options=BaseOptions(model_asset_path=...), num_hands=maxHands, running_mode=VIDEO)`. There is no delegate, and `detectionCon`/`minTrackCon`/`modelComplexity` are accepted but not passed.
  - It exposes `findHands(img, draw, flipType)`, `fingersUp(hand)` and `findDistance(p1,p2,img)`. Each hand is a dict with `lmList` (pixel x,y,z), `bbox`, `center`, `type`.

  — [Local inspection of cvzone-2.0.0 wheel, this session](https://pypi.org/project/cvzone/2.0.0/#files)

### Inferences
- cvzone is good for learning or a quick prototype that follows Murtaza's Workshop (computervision.zone) videos. Its tutorials written before 2026 target cvzone 1.x + `mp.solutions` and break with current mediapipe.
- Downsides for this project:
  - No GPU delegate, so it crashes with mediapipe 1.0.1 on macOS.
  - Hard-coded model version.
  - Discards world landmarks.
  - Integer pixel z is not metric.
- Using `HandLandmarker` directly costs ~30 lines more and gives world landmarks, handedness scores, delegate choice and timestamp control.

### Gaps
- Could not find a published changelog or source repo for cvzone 2.0.0. The analysis is from the wheel contents.
- No other actively maintained Python MediaPipe wrapper found that adds real value (only small community wrappers).

## 5. Alternative models from Python on a Mac, and trade-offs vs. MediaPipe

### Takeaway
For hand keypoints on a Mac, nothing in Python matches MediaPipe HandLandmarker's combination of ready weights, 21 3D keypoints, handedness, tracking and speed.
- **Apple Vision via PyObjC** (native, ANE/GPU) is the closest platform-native alternative, but needs Objective-C bridging code.
- **rtmlib (RTMPose/RTMW via ONNX Runtime + CoreML EP)** is the best non-Google option.
- **Ultralytics YOLO26-pose** needs you to train hand keypoints yourself (dataset CC BY-NC-SA; library AGPL-3.0).
- For faces: **OpenCV YuNet** for detection, **InsightFace** (models non-commercial only) for recognition/analysis, **dlib** (sdist only, compile required) as legacy.

### Cited Findings
**ONNX Runtime and CoreML**
- `onnxruntime` 1.30.0 was released 2026-09-10 and requires Python ≥3.11. It ships `macosx_14_0_arm64` wheels (cp311–cp314) — [PyPI onnxruntime](https://pypi.org/project/onnxruntime/)
- On this Mac, `ort.get_available_providers()` returns `['CoreMLExecutionProvider','AzureExecutionProvider','CPUExecutionProvider']` — [Local test, this session]
- CoreML EP: "Official macOS Python wheels include CoreML support by default".
  - Usage: `providers=[('CoreMLExecutionProvider', {"ModelFormat":"MLProgram","MLComputeUnits":"ALL"})]`.
  - `MLComputeUnits` can be CPUAndNeuralEngine, CPUAndGPU, ALL or CPUOnly.
  - Other options: `RequireStaticInputShapes` and `ModelCacheDirectory`. MLProgram needs macOS 12+.
  - Operator coverage has restrictions.

  — [ONNX Runtime CoreML EP docs](https://onnxruntime.ai/docs/execution-providers/CoreML-ExecutionProvider.html)
- `onnxruntime-silicon`, a formerly popular third-party build, is stale: last release 1.16.3 on 2024-01-19 — [PyPI onnxruntime-silicon](https://pypi.org/project/onnxruntime-silicon/)

**RTMPose via rtmlib (and MMPose)**
- `rtmlib` 0.0.16 was released 2026-08-04 (repo ~681 stars, Apache-2.0).
  - It does "pose estimation based on RTMPose and ViTPose models WITHOUT any dependencies like mmcv, mmpose, mmdet".
  - Backends are opencv / onnxruntime / openvino; `device` is 'cpu', 'cuda' or 'mps'.
  - Solutions include `Wholebody` and `Hand`.

  — [GitHub Tau-J/rtmlib](https://github.com/Tau-J/rtmlib); [PyPI rtmlib](https://pypi.org/project/rtmlib/)
- rtmlib's `device='mps'` with the onnxruntime backend maps to `CoreMLExecutionProvider` when available, else CPU (`rtmlib/tools/base.py`) — [rtmlib base.py](https://github.com/Tau-J/rtmlib/blob/main/rtmlib/tools/base.py)
- `mmpose` was last released as 1.3.2 on 2024-07-12 — [PyPI mmpose](https://pypi.org/project/mmpose/)

**Ultralytics YOLO**
- `ultralytics` 8.4.164 was released 2026-09-27 (repo ~62k stars, AGPL-3.0; Enterprise license available) — [PyPI ultralytics](https://pypi.org/project/ultralytics/); [GitHub ultralytics](https://github.com/ultralytics/ultralytics)
- YOLO26 was "released January 2026".
  - Pose variants are `yolo26{n,s,m,l,x}-pose.pt`.
  - It supports NMS-free end-to-end inference.
  - It exports to CoreML/ONNX/TensorRT/TFLite/OpenVINO.

  — [Ultralytics YOLO26 docs](https://docs.ultralytics.com/models/yolo26)
- CoreML export produces an `.mlpackage` (ML Program) that runs on CPU/GPU/ANE; pose export is supported — [Ultralytics CoreML integration](https://docs.ultralytics.com/integrations/coreml)
- The Ultralytics Hand Keypoints dataset has 26,768 images (18,776 train / 7,992 val) and 21 keypoints per hand, "annotated using Google MediaPipe". Its license is CC BY-NC-SA 4.0, and the training example starts from `yolo26n-pose.pt`. The page does not confirm official pretrained hand-keypoint weights — [Ultralytics hand-keypoints dataset](https://docs.ultralytics.com/datasets/pose/hand-keypoints/)

**Apple Vision via PyObjC**
- `VNDetectHumanHandPoseRequest` is available on macOS 11.0+. The newer Swift-only `DetectHumanHandPoseRequest` needs macOS 15.0+ — [Apple docs: VNDetectHumanHandPoseRequest](https://developer.apple.com/documentation/vision/vndetecthumanhandposerequest)
- `maximumHandCount` controls multi-hand detection — [createwithswift](https://www.createwithswift.com/detecting-hand-pose-with-the-vision-framework/)
- `pyobjc-framework-Vision` 12.2.2 was released 2026-08-11, with universal2 wheels for cp310–cp315 (incl. free-threaded 3.13t/3.14t) — [PyPI pyobjc-framework-Vision](https://pypi.org/project/pyobjc-framework-Vision/)
- Web search turned up only Swift examples, not Python ones — [WWDC20 "Detect Body and Hand Pose with Vision"](https://developer.apple.com/videos/play/wwdc2020/10653/)

**Face alternatives**
- YuNet ([opencv_zoo YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet)):
  - "a light-weight, fast and accurate face detection model". WIDER Face AP is 0.834/0.824/0.708 (easy/medium/hard).
  - It outputs a bbox + 5 landmarks for faces of roughly 10x10–300x300 px. MIT license.
  - Variants: `face_detection_yunet_2026may.onnx` (dynamic input, "OpenCV 5.x compatible"), plus the 2023mar fp32/int8/int8bq models.
  - Accessed from Python as `cv2.FaceDetectorYN`, which exists in cv2 5.0.0 ([Local test, this session]).
- InsightFace ([PyPI insightface](https://pypi.org/project/insightface/)):
  - `insightface` 2.0 was released 2026-09-08 and requires Python ≥3.10. It runs on ONNX Runtime with "automatic CoreML/CUDA/CPU selection, and reusable CoreML compilation caches".
  - "The library code is released under the MIT License … The pretrained models provided with this library are for non-commercial research only".
- `dlib` 20.0.1 (2026-03-29) has no wheels on PyPI (sdist only), so it compiles locally with CMake — [PyPI dlib](https://pypi.org/project/dlib/)

### Inferences
- **Hand tracking ranking for this Mac project:**
  1. MediaPipe HandLandmarker (GPU delegate), with ready weights, 21 3D + world landmarks and handedness.
  2. Apple Vision hand pose via PyObjC. Native and likely efficient, but you convert `CVPixelBuffer`/`CGImage` and handle Objective-C objects from Python, and the output is 2D-only (no depth).
  3. rtmlib (RTMW whole-body or the Hand solution) via ORT+CoreML. 2D keypoints and typically a separate detector stage; more setup, heavier.
  4. YOLO26-pose trained on hand-keypoints. 2D only, you must train it, and the licensing is restrictive (AGPL + CC BY-NC-SA data).
- **Face:** for face mesh / AR anchoring (478 points + 4x4 pose matrix + blendshapes), MediaPipe FaceLandmarker has no real Python equivalent in this list. YuNet is best for fast plain face boxes and 5 landmarks. InsightFace is for identity/recognition (non-commercial model license). dlib's 68-point model is legacy and painful to install.
- Using ORT + CoreML EP is worthwhile only when you bring your own ONNX model (RTMPose, YOLO ONNX, YuNet ONNX). Enable `ModelCacheDirectory` to avoid slow recompilation on each start.

### Gaps
- No Mac benchmarks found for rtmlib Hand/RTMW with CoreML EP, YOLO26-pose on MPS/CoreML, or Apple Vision hand pose from Python. I found no numeric comparisons with MediaPipe on Apple Silicon.
- Could not find an authoritative Python/PyObjC example of `VNDetectHumanHandPoseRequest` on live webcam frames. Its joint count and 3D capability were not verified from Apple docs in this session; only 2D normalized points are assumed.
- Did not confirm whether Ultralytics publishes official pretrained hand-keypoint weights.

## 6. Performance pitfalls in Python real-time loops, and fixes

### Takeaway
The main latency sources are:
- blocking `cap.read()`;
- stale buffered frames;
- MediaPipe CPU inference (~24 ms for two hands);
- GPU→CPU copies;
- macOS main-thread GUI rules.

The standard fixes:
- read the camera on a dedicated thread, keeping only the latest frame;
- run inference synchronously in VIDEO mode, or use LIVE_STREAM with the latest-result pattern;
- use the GPU delegate;
- keep all imshow/window/GL calls on the main thread;
- downscale inference input.

The MediaPipe/OpenCV/ORT native code releases the GIL in C++, so a capture thread plus a main loop is usually enough; multiprocessing is rarely needed.

### Cited Findings
- PyImageSearch's classic advice (Dec 21, 2015): the "secret" to higher FPS is to move frame reading "to a separate thread". The post reports FPS gains such as 379% on their test setup, and introduced the threaded `WebcamVideoStream`/`VideoStream` in `imutils`. These figures are old (2015) — [PyImageSearch: Increasing webcam FPS](https://pyimagesearch.com/2015/12/21/increasing-webcam-fps-with-python-and-opencv/)
- In LIVE_STREAM, MediaPipe ignores frames submitted while busy ([Hand Landmarker Python guide](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python)). Observed: 184 of 300 frames dropped when submitted faster than inference ([Local test, this session]).
- VIDEO/LIVE_STREAM need timestamps and use tracking to skip palm detection — [Hand Landmarker Python guide](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python)
- The official Python Raspberry Pi sample uses LIVE_STREAM with `detect_async(mp_image, time.time_ns() // 1_000_000)`, `cv2.flip(image,1)`, `cv2.cvtColor(BGR2RGB)`, and draws in the main loop — [mediapipe-samples hand_landmarker/raspberry_pi/detect.py](https://github.com/google-ai-edge/mediapipe-samples/blob/main/examples/hand_landmarker/raspberry_pi/detect.py)
  - The same file still imports `mp.solutions.hands/drawing_utils` and `mediapipe.framework.formats.landmark_pb2`, so it breaks on mediapipe ≥0.10.30 (verified via the GitHub API contents).
- `cv2.imshow` must stay on the main thread on macOS — [opencv issue #22602](https://github.com/opencv/opencv/issues/22602)
- Measured GPU delegate latency is ~3–5 ms vs ~24 ms CPU for hands (section 1 table) — [Local test, this session]
- The latency of Python hand tracking has been discussed upstream — [mediapipe issue #5789 "Reducing Latency for Hand-Tracking Solution in Python"](https://github.com/google-ai-edge/mediapipe/issues/5789) (title only; I didn't read the content).

### Inferences
- **Recommended loop shape:**
  1. Thread A: `cap.read()` in a loop, storing only the newest frame (overwrite, don't queue).
  2. Main thread:
     - take the latest frame and flip it;
     - convert BGR→RGBA (GPU) or RGB (CPU);
     - `detect_for_video(img, ts_ms)` with monotonically increasing `ts_ms`, e.g. `int(time.monotonic()*1000)`;
     - compute geometry;
     - render (OpenCV draw or GL upload + draw);
     - `imshow` / swap buffers.
- For LIVE_STREAM, store the result in a variable under a lock from the callback. The callback runs on a MediaPipe thread (release 0.10.32 notes: "Ensure all callbacks are invoked on a valid Python thread"). Draw with the latest result, and accept a one-frame misalignment.
- **Jitter:** landmarks jitter frame to frame. Apply a One-Euro or exponential filter to the fingertip points before building shapes, especially for the 3D cube, where small errors in 3 points strongly rotate the solid.
- **Other practical tips:**
  - Request 1280x720 (or 640x480) from the camera and keep inference input at 640x480 or less; MediaPipe resizes internally to 192–256 px.
  - Avoid `np.copy` on full frames.
  - Reuse GL textures (`texture.write`) instead of recreating them each frame.
  - Print FPS with `time.perf_counter()`.
- Don't use `multiprocessing` for inference unless needed: pickling frames across processes adds latency. Free-threaded CPython 3.13t/3.14t is not needed for this workload, and most of this stack (moderngl, mediapipe native lib) is not verified on it.
- **Install hygiene:** use one venv with Python 3.12 (every package in this stack has arm64 wheels for it) and only one OpenCV variant. mediapipe pulls in `opencv-contrib-python`, so don't also install `opencv-python`, or cvzone's dependency will add it.

### Gaps
- No authoritative 2025–2026 measurement found of `cv2.VideoCapture` latency or buffer depth with AVFoundation on Apple Silicon, or of the threaded vs non-threaded gain on modern Macs.
- Did not verify MediaPipe's thread-safety for concurrent `detect_for_video` calls from multiple threads. The docs describe a single-stream usage pattern.

## 7. Tutorials, official examples, GitHub repos

### Takeaway
Most hand-tracking tutorials online (Murtaza's Workshop/cvzone videos, PyImageSearch/LearnOpenCV-era posts, most "virtual painter" repos) use `mp.solutions` and are **outdated since Dec 2025**. Use them only for ideas and geometry, and port the code to the Tasks API. Current, correct references:
- the official MediaPipe Python notebooks, updated for 0.10.32+ `drawing_utils`;
- the Tasks-API Python guides on developers.google.com;
- a few recent Tasks-API community repos.

### Cited Findings
- Official Python notebooks exist at [google-ai-edge/mediapipe-samples](https://github.com/google-ai-edge/mediapipe-samples):
  - `examples/hand_landmarker/python/hand_landmarker.ipynb`
  - `examples/gesture_recognizer/python/gesture_recognizer.ipynb`
  - `examples/face_landmarker/python/[MediaPipe_Python_Tasks]_Face_Landmarker.ipynb`
  - `examples/pose_landmarker/python/[MediaPipe_Python_Tasks]_Pose_Landmarker.ipynb`
- The maintainers point to the notebooks for the new DrawingUtils usage — [issue #6192](https://github.com/google-ai-edge/mediapipe/issues/6192)
- Webcam scripts also exist at `examples/{hand_landmarker,face_landmarker,gesture_recognizer,pose_landmarker}/raspberry_pi/*.py`. The hand one still uses `mp.solutions` for drawing (outdated) — [mediapipe-samples](https://github.com/google-ai-edge/mediapipe-samples)
- Official Tasks guides:
  - [Hand Landmarker Python](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python)
  - [Face Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker)
  - [Gesture Recognizer](https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer)
- Community repos:
  - [JAYP752/Hand-gesture-3d-control](https://github.com/JAYP752/Hand-gesture-3d-control): MediaPipe "latest Tasks API" + PyGame + PyOpenGL 3D cube manipulated by hand. Tiny repo (1 star, pushed 2025-12-26).
  - [Bibashsitoula0/hand-ar-portal](https://github.com/Bibashsitoula0/hand-ar-portal): Tasks-API `HandLandmarker` with OpenCV; neon skeleton, gesture recognition, air-drawing, and "a two-hand portal mode with live video filters". This is close to the "rectangle between two hands filled with a filter" idea. Tiny repo (0 stars, pushed 2026-09-26); Python 3.11+.
  - [evch1204/hand_tracker](https://github.com/evch1204/hand_tracker): "Hand tracking 3d cube controller using MediaPipe and OpenCV" (pushed 2025-12-15).
  - [sherbondy gist](https://gist.github.com/sherbondy/58bdd1d8983d9ba96043fea57f9e7429): "Google Mediapipe Hand Tracking to World Space using OpenCV solvePnP, rendered in OpenGL using PyGame". This is the key technique for camera-space 3D placement of hand-defined geometry.
- Topic listings for discovery: [GitHub topic hand-tracking](https://github.com/topics/hand-tracking); [GitHub topic mediapipe (Python, recently updated)](https://github.com/topics/mediapipe?l=python&o=desc&s=updated)
- Background reading:
  - [PyImageSearch threaded webcam FPS (2015)](https://pyimagesearch.com/2015/12/21/increasing-webcam-fps-with-python-and-opencv/)
  - [cvzone](https://github.com/cvzone/cvzone) / computervision.zone (Murtaza's Workshop) course material, built on cvzone 1.x and `mp.solutions` up to 2024.
  - Rendering examples: [pygfx example gallery](https://docs.pygfx.org/stable/_gallery/index.html) and the [moderngl repo](https://github.com/moderngl/moderngl) examples.

### Inferences
- Suggested learning path:
  1. Start from the official hand_landmarker notebook and Python guide for the API.
  2. Replace notebook image I/O with a `cv2.VideoCapture` loop.
  3. Borrow `fingersUp`/distance helpers from cvzone 2.0.0.
  4. Use hand-ar-portal as a reference for two-hand region filters.
  5. Use the sherbondy gist and JAYP752 for the 3D step, but port their PyGame/PyOpenGL fixed-function rendering to moderngl or pygfx for a cleaner modern pipeline on macOS.
- Treat any tutorial containing `mp.solutions.hands.Hands(...)`, `results.multi_hand_landmarks` or `landmark_pb2` as pre-2026 legacy code.

### Gaps
- Did not locate a current (2025–2026) LearnOpenCV or PyImageSearch article that uses the Tasks API for hand tracking + AR. Their older posts, e.g. on OpenCV+OpenGL AR, were not fetched/verified in this session.
- No well-known, highly-starred, maintained Python repo found that does exactly "3D parallelepiped from 3 fingertips with a real GPU renderer over the webcam". Existing examples are small personal projects.
