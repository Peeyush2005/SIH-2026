# BluEcho local inspection dashboard

Phase 3 adds a same-origin React interface, CPU job queue and persistent review to the existing engine. See [Dashboard quick start and five-minute demo](https://github.com/Sharon-codes/SIH-2026/blob/main/docs/DASHBOARD.md). This is release 0.1.4 of `bluecho-sonar`.

# BluEcho sonar inspection

BluEcho wraps the existing RecordingEngine with a deterministic, CPU physics-aware inspection supervisor and a persistent review queue. The package includes a local inspection dashboard. It does not include a new foundation model or trigger training.

Python 3.12 on Linux x86-64 is the tested platform. Other Python versions are currently excluded. No large detector checkpoints, datasets, private recordings or credentials are included in the wheel. Small fitted verifier parameters and model metadata are included. Core import/help require only NumPy and Pillow; inference and geospatial libraries are optional.

## Install and run

Use a fresh environment. Install CPU Torch explicitly **before** the inference extra: the upstream Ultralytics dependency otherwise allows a platform-default Torch distribution, which can include CUDA libraries.

```bash
python3.12 -m venv sonar-env
. sonar-env/bin/activate
python -m pip install torch==2.4.1+cpu torchvision==0.19.1+cpu --index-url https://download.pytorch.org/whl/cpu
python -m pip install 'bluecho-sonar[inspection,inference,onnx]==0.1.4'
bluecho --version
bluecho doctor
bluecho capabilities
```

For an offline installation, use the exact release wheel: `python -m pip install '/absolute/path/bluecho_sonar-0.1.4-py3-none-any.whl[inspection,inference,onnx]'`. To run the dashboard, also install the `api` extra: `python -m pip install 'bluecho-sonar[api]==0.1.4'`.

A cold installation has a pinned direct-source experimental SSS inference route:

```bash
bluecho models fetch --model sss-wreck-experimental --registry "$HOME/.cache/bluecho/models"
bluecho models verify --model sss-wreck-experimental --registry "$HOME/.cache/bluecho/models"
bluecho inspect '/absolute/path/sonar.jpg' --modality SSS --model sss-wreck-experimental --registry "$HOME/.cache/bluecho/models" --output '/absolute/fresh/inspection'
```

The download is about 43 MiB. It verifies the pinned SHA256 before loading. Review the inherited model/data terms in `bluecho capabilities`. Native labels `ghost_net`, `mine_cylinder` and `crab_pot` remain **unvalidated proposals**, never validated real nets/cylinders. The frozen threshold and preprocessing are unchanged.

For the existing pipeline, import your authorized Phase 1 native weight with its original `manifest.json` alongside it:

```bash
bluecho models import --model sss-pipeline-v3 --registry "$HOME/.cache/bluecho/models" --local '/absolute/phase1/registry/sss-v3/native.pt'
bluecho inspect '/absolute/path/pipeline.pbm' --modality SSS_LF --model sss-pipeline-v3 --registry "$HOME/.cache/bluecho/models" --output '/absolute/fresh/pipeline'
```

The four existing routes remain available via `bluecho.phase1.engine.RecordingEngine`. Existing `bluecho predict`, `batch`, `model-info` and `api` arguments are compatibility wrappers. The original `python -m bluecho.phase1.cli --help` commands remain supported. New `bluecho inspect` runs on CPU and writes both unchanged `results.json` and a separate `inspection.json` per window.

## Capabilities

| Model ID | Modality | Capability and evidence | Acquisition |
|---|---|---|---|
| sss-pipeline-v3 | SSS_LF | Pipeline; frozen correlated validation, default preserved | Verified local native import + original manifest |
| uatd-fls | FLS_UATD | Ten native classes including cylinder; selected compatibility sample, overlap unknown | Pinned download + Linux bubblewrap restricted conversion |
| sss-wreck-experimental | SSS | Experimental pipeline/wreck; no independent wreck benchmark | Pinned ONNX download |
| fls-debris-development | FLS_ARIS | Trained detector: can, bottle, drink-carton, chain, propeller, tire, hook, valve, shampoo-bottle, standing-bottle; no independent benchmark | Verified local import; inherited CC BY-NC-SA terms |
| ghost-net-real | â€” | Unavailable | No verified real-net model |

Bottle appearance does not establish plastic material. FLS fan geometry and SSS slant geometry are distinct. No weights changed and no accuracy improvement is claimed.

## Inspection and review

```bash
bluecho inspect '/absolute/path/recording.xtf' --channel 0 --max-pings 32 --nav-crs EPSG:4326 --model sss-wreck-experimental --registry '/absolute/models' --output '/absolute/fresh/xtf'
bluecho review seed --database '/absolute/review.sqlite' --input '/absolute/fresh/pipeline/inspection.json' --source-group 'survey-recording-family' --output '/absolute/review.json'
bluecho review export --database '/absolute/review.sqlite' --output '/absolute/review.json'
bluecho review import --database '/absolute/second.sqlite' --input '/absolute/review.json' --output '/absolute/roundtrip.json'
```

The XTF CRS above is a user-supplied interpretation, not a datum discovered from NavUnits. Default bottom tracking cannot promote first returns to altitude without verified calibration, flat seabed, level sensor and a physical motion bound. In the available real recording all altitude estimates remain unreliable and all target locations unavailable. Navigation is preserved separately.

Review bundles contain unreviewed detections and some apparently clear regions. They do not invent human reviews. Use the Python ReviewQueue API to append confirmed/corrected/false-alert/missed-object/clear-region events, then export/import. A frozen source/group exclusion manifest is mandatory for development export; no training is triggered.

See [physics assumptions](https://github.com/Sharon-codes/SIH-2026/blob/main/docs/PHYSICS.md), [review workflow](https://github.com/Sharon-codes/SIH-2026/blob/main/docs/REVIEW.md), [package interfaces](https://github.com/Sharon-codes/SIH-2026/blob/main/docs/INTERFACES.md), [offline/model terms](https://github.com/Sharon-codes/SIH-2026/blob/main/docs/MODELS.md), [validation](https://github.com/Sharon-codes/SIH-2026/blob/main/docs/VALIDATION.md), and [Phase 3 integration contract](https://github.com/Sharon-codes/SIH-2026/blob/main/docs/PHASE3.md). Source is AGPL-3.0-or-later; model/data licenses are separate.

## Final bounded improvement cycle

The original v3 default remains unchanged. Small supervised logistic verifiers were actually fitted on existing training-source candidates. Generic and additional acoustic-feature comparisons use the same single-survey development-validation observations; no independent generalization confirmation exists. These are acoustic image proxies, not a PINN or a trained foundation model. See docs/FINAL_IMPROVEMENT.md.

`bluecho pipeline-review image.pbm --manifest /absolute/registry/sss-v3/manifest.json --mode baseline --output /absolute/baseline.json` uses the original operating point. Explicit `--mode generic` or `--mode acoustic --range-axis x` requires `--threshold` and exposes exploratory learned scores alongside unchanged boxes/raw scores. Missing range orientation or truncated lateral context falls back to the generic verifier. It is never applied to FLS.

## SSS detection handoff â€” Team BluMatrix / SIH26-26057

`bluecho boxes` generates automatic boxes, crops, JSON/CSV and a local HTML inspection report. See docs/SSS_DETECTION_PHASE1.md. ENGINE_DELIVERY is complete after release checks; REQUIRED_SSS_CLASS_COVERAGE is incomplete: pipe evaluated on correlated development data, wreck experimental, SSS cylinder and real nets unavailable. FLS routes remain supplemental.

## Source-bound geolocation

`bluecho geotag results.json --source original.tif --sidecar metadata.json --output fresh-report` repositions saved predictions without inference. `bluecho validate-sidecar metadata.json --source original.tif --width 1024 --height 1024` validates binding. See docs/GEOLOCATION.md. Unlocated candidates remain in GeoJSON with null geometry. Actual NOAA candidate-to-coordinate demonstration is not confirmed wreck detection or validated field accuracy.
