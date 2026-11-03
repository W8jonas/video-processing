# Static-pose prototype: A/S and U/V disambiguation

Checked locally on 2026-10-20. This implementation experiment extends the Python
prototype documented in `README.md`; it is not a linguistic validation of Libras.

## Observations

The user reported alternating predictions for A/S and U/V during live use.
The existing `data/poses.jsonl` contained 65 A, 16 S, 33 U, and 34 V enrollment
frames, all from one application session. Other letters were also enrolled.
No independent live-test frames or accuracy labels were available for analysis.

The local enrollment features separated these pairs geometrically. In the
stored wrist-to-middle-knuckle scale, the 10th–90th percentile of the thumb-tip
distance to the index knuckle was 0.396–0.549 for A and 0.590–0.611 for S.
Index-to-middle fingertip separation was 0.192–0.224 for U and 0.583–0.658 for V.
These are user-specific observations, not universal letter thresholds.

## Implementation

When the two leading whole-hand candidates form A/S or U/V, rerank them using
equal contributions from whole-hand RMS distance and local descriptor RMS
distance. A/S descriptors measure thumb joints 3 and 4 against knuckles 5, 9,
and 17. U/V descriptors measure fingertip separation and the angle between the
index and middle finger directions. Local descriptors tolerate image-plane roll.

Distances are computed jointly against individual templates, then averaged over
the closest three templates per class. Retain whole-hand distance rejection and
ambiguity checks against a third candidate. No stored samples or feature schema
were changed. The UI exposes the best candidates and rejection reason.

## Verification and limits

All 21 automated tests passed, including synthetic orientation distractors and
rejection of identical U/V examples. Existing labels remain unknown when there
is insufficient separation; stabilization does not retain an ambiguous letter.

As a diagnostic only, replaying the same 148 enrollment frames after a synthetic
10-degree image-plane rotation yielded 108 label agreements and 40 rejections
with the original metric, versus 148 agreements with the refinement. At 20
degrees, the original metric produced 76 agreements, 66 rejections, and 6 other
labels; the refinement produced 76 agreements and 72 rejections. These replays
reuse enrollment data, include the original templates, and **are not accuracy
measurements or independent validation**. They only exercise sensitivity to a
controlled perturbation. Live retesting of both pairs is still required.
