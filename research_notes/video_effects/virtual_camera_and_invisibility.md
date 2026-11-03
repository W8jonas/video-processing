# Virtual camera and gesture-driven invisibility: technical findings

Verified against primary sources on 2026-11-02. This is research for the staged
plan in `docs/roadmap_video_effects.md`, not a working camera/Meet integration.

## Local baseline

Read-only inspection found macOS 26.6.2, arm64, CPython 3.12.6, MediaPipe 0.10.35,
and opencv-contrib-python 4.11.0. OBS was absent at `/Applications/OBS.app`,
`/Applications/OBS Studio.app` and `~/Applications/OBS.app`; other locations were
not exhaustively searched. pyvirtualcam was absent from the project environment.
No new packages, models, extensions or applications were installed.

The user confirmed successful live control of the four ESP8266 LEDs. That
validates the previous experiment functionally, not a measured accuracy rate or
the latency of this proposed video pipeline.

## Virtual-camera routing

The current [pyvirtualcam README](https://github.com/letmaik/pyvirtualcam#macos-obs)
documents macOS support through OBS. On macOS 13+, pyvirtualcam 0.14+ uses OBS
30+. Its setup starts/stops the virtual camera once in OBS and closes OBS before
Python becomes the producer. One OBS camera instance cannot simultaneously be
used for Python output and a further OBS camera-output chain. Its
[API](https://letmaik.github.io/pyvirtualcam/) supports BGR input, an appropriate
interface for OpenCV frames, and requires configured dimensions/pixel format.

[OBS documentation](https://obsproject.com/kb/virtual-camera-troubleshooting)
describes camera-extension approval and the modern component's macOS
compatibility. The [virtual-camera guide](https://obsproject.com/kb/virtual-camera-guide)
describes publishing an OBS scene/source. The
[macOS capture source](https://obsproject.com/kb/macos-screen-capture-source)
can capture a single application window using ScreenCaptureKit.

Two distinct viable experiments follow from those documented capabilities:

1. Python publishes directly through pyvirtualcam to the installed OBS virtual
   device, with OBS not producing concurrently.
2. OBS captures a clean Python preview window and publishes the scene itself;
   this route does not use pyvirtualcam as a simultaneous producer.

These are proposed integration routes, not locally validated combinations.
[Google Meet help](https://support.google.com/meet/answer/10409699?hl=en)
documents selecting the camera in video settings. Validate discovery, permissions,
orientation and the received image in an actual meeting. Sharing a screen is
not required for the virtual-device route. A clean preview should exclude the
local control panel and any segmentation debug views.

## Segmentation and matting candidates

| Candidate | Source-supported capability | Proposed role / uncertainty |
|---|---|---|
| MediaPipe Image Segmenter, SelfieSegmenter | Person/background categories; square and landscape variants; confidence/category masks | First baseline using the existing Tasks stack; local model compatibility and mask quality still untested |
| Background Matting V2 | Requires an additional empty-background image; provides foreground/alpha matting | Particularly relevant to the requested clean-background setup; runtime and performance on this Mac untested |
| Robust Video Matting | Human-video matting with temporal memory; no clean-background image required by the network | Later alternative if temporal edges/fine detail justify additional runtime work; our compositor still needs a replacement background |

Sources: [MediaPipe model overview](https://developers.google.com/edge/mediapipe/solutions/vision/image_segmenter),
[Python API guide](https://developers.google.com/edge/mediapipe/solutions/vision/image_segmenter/python),
[Background Matting V2](https://github.com/PeterL1n/BackgroundMattingV2),
[Robust Video Matting](https://github.com/PeterL1n/RobustVideoMatting).

The MediaPipe guide lists background/person model categories and confidence
outputs, but implementation must inspect the chosen model's metadata and actual
output channels. Do not assume a particular channel index without checking.
The published Google benchmark is on Pixel 6. The matting repositories publish
Nvidia-GPU results; none establishes performance on the local Apple Silicon Mac.
Background Matting V2 also distinguishes model throughput from its complete
video conversion scripts. Any runtime choice needs a local full-pipeline test.

## Engineering inferences and boundaries

- Capturing a fixed clean plate makes a first static-background disappearance
  possible even before segmentation: publish that entire plate while invisible.
  It also freezes all background motion, so this is an explicit initial demo.
- Selective invisibility replaces only the person mask with the corresponding
  pixels from the clean plate. It preserves the current frame elsewhere but
  cannot show a live view of background currently hidden behind the person.
- Camera movement, exposure changes and moved furniture can misalign the saved
  plate. Require recapture initially; do not silently refresh it with the person
  present, which would bake their image into the background.
- Segmentation is not automatically a high-quality alpha matte. Hair, hand edges,
  occlusion, shadows and temporal flicker need scene-specific testing.
- Hand tracking must consume original frames while the output is invisible.
  Otherwise the gesture needed to return can disappear from its own input.
- Keep camera acquisition independent from output scheduling. If processing
  falls behind, prefer dropping stale frames over accumulating latency.

No published demo or synthetic mask test will establish real-world success in
the user's room. The roadmap separates virtual-device validation, clean-plate
capture, simple replacement, selective composition, gestures and quality work.

## Implementation verification: selective composition

On 2026-11-02, stage 4 was implemented with the official version-1 landscape
model. Local SHA-256:
`490e9ea734313e0de10fa0cd9e3c6133e36ea4db2b7a49bde9ef019f72796b8e`.
MediaPipe 0.10.35 returned labels `['selfie']` and a single float32 confidence
mask shaped `(height, width, 1)`. The implementation verifies metadata rather
than assuming the overview's conceptual two categories imply two output tensors.

The real model was run on Google's
[portrait sample](https://storage.googleapis.com/mediapipe-assets/portrait.jpg),
resized to 384×480, using CPU on macOS arm64. A synthetic replacement background
verified unchanged original pixels wherever the refined mask is zero and
replacement pixels wherever it is one. Intermediate pixels are blended. This
was an image inference/composition check, not a webcam benchmark or room test.

The local pipeline saturates confidence between 0.2 and 0.6, dilates by a
configurable radius (default three source-frame pixels), and feathers edges.
These are prototype engineering choices, not model guarantees. No temporal
filtering or shadow removal is implemented. Every recognized person can be
removed; there is no identity selection. Hair and thin fingers need local review.
119 automated tests passed across the repository, including selective output,
live background changes, mask metadata, and original-frame hand inference.
