# Phase 2 validation

Existing inference, geometry, download, mask, recovery and API tests plus new physics/review tests are run in the local release checks. See the release receipt for the final count and environment. Synthetic geometry tests demonstrate software behavior, not measured field accuracy.

Frozen replay: 674 correlated original validation frames, threshold 0.6818633675575256, IoU 0.5. Baseline and supervisor both retain 179 TP, 129 FP, 186 FN; precision 0.58117, recall 0.49041, false alerts per original frame 0.19139, mean matched IoU 0.72584. This is replay of preserved source-pixel baseline predictions, not a fresh full-model benchmark. No historical test tuning. Tile metrics are unavailable in this replay and are not conflated with original-frame metrics.

At a fixed 50-item review budget, detector score order contains 44 true matched objects and optional reason-only order contains 28. The default therefore preserves detector order within each model; reason priority remains visible and optional. No detector accuracy improvement is claimed and filtering is disabled.

Real AURORA XTF: 32 selected port pings, 9348 samples per row. The experimental SSS route returns no supported detections in this window. Measured altitude is absent and none of 32 estimated traces is reliable: ambiguity, unverified range calibration, missing physical motion bounds, and unsupported flat/level assumptions. Target location coverage is unchanged (unavailable); sensor track remains separate. Real positional accuracy and net presence are unvalidated. A first return is not manufactured into altitude.

The release validation directory records per-stage CPU startup, inference, geometry and RSS for specified image/window sizes. These are host-specific samples, not hardware-independent real-time claims. Model checksums and original defaults are preserved. New independent FLS, wreck, real-net, material and geographic benchmarks remain unavailable. No training ran in this phase.
