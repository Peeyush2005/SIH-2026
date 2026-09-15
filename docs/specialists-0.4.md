# BluEcho 0.4: broader model coverage and a rebuilt inspection website

Four model routes now execute in the browser, with the same three new specialists
also available through the Python registry. This release integrates pretrained
models; it does not represent new BluEcho training or a competitive accuracy win.

The website uses a minimal homepage with the problem, our solution and a single
upload area. Statistics and model cards are removed. Sensor/model selection
appears after upload; optional batch tools sit under Reports. A large sonar
workspace keeps human review controls beside the image. Source context and provenance
remain accessible in a disclosure panel. Batch inspection, retained/false-alert/
uncertain decisions, box corrections, review history, PDF briefs and structured
exports remain functional. Model downloads are pinned and hash checked. One model
session is resident at a time; sonar images are not sent to inference servers.

## Models and actual classes

| Route | Sensor | Source labels | Evidence |
|---|---|---|---|
| Pipeline | SSS low frequency | Pipeline | Original correlated development model and frozen threshold unchanged. Browser regression preserves the native sample result. |
| GhostVision | SSS | Crab-Pot | Fixed source-test sample: low recall; detailed results below. |
| FLS11 | FLS ARIS | mine, can, bottle, drink-carton, chain, propeller, tire, hook, valve, shampoo-bottle, standing-bottle | Three labelled author examples exercise propeller, shampoo-bottle and can. Runtime compatibility only. |
| SonarVision | SSS | unknown_debris, airplane, mine, wreck | Author sonar example produces a wreck-labelled prediction; no independent correctness or accuracy established. |

`mine` outputs remain **unvalidated proposals**, including in CSV, JSON, PDF,
GeoJSON and evidence ZIP exports. The presence of a class name does not establish
hazard identity. `unknown_debris` is an existing trained category, not a universal
anomaly detector. Bottle classes do not establish glass/plastic composition. Real
net detection and ocean-wide performance remain unsupported. These are separate
sensor-specific models, not a single detector with 16 validated classes.

## Frozen artifacts and attribution

| Model | Pinned source | SHA-256 |
|---|---|---|
| GhostVision YOLO26s | [PINGEcosystem/gv-yolo26](https://huggingface.co/PINGEcosystem/gv-yolo26/tree/818d51e9900efa3bd155dafb369145426fd6aa65) | `0deec99405d2f85602e9947c90f46110dddb8d85669223c1ee35308f75cd318d` |
| SonarVision YOLOv8 | [Dinoman1221/sonarvision-yolov8-esi-v6](https://huggingface.co/Dinoman1221/sonarvision-yolov8-esi-v6/tree/f83895e4ae398030dc6dcbb9e98fe71e950d6db7) | `33a620674479e6251a3fb487e2b6a47dca777e3d3dd51d49c77fec6b2043ba72` |
| FLS11 ONNX conversion | [BluEcho-FLS11-ONNX](https://huggingface.co/SharonMelhi/BluEcho-FLS11-ONNX/tree/0236bd3c550f0f2caf28a25a307e6ace13ec1b24) | `385b4e1185e478ec7ae90fa3091586273ca956aa957cbba1dbb96eaeae351dc2` |

FLS11 originates from **Bhoumik Chandra Bagh**,
[riku-1825/Under_Water_Sonar_Mines_Debris_Detection_And_Segmentation](https://github.com/riku-1825/Under_Water_Sonar_Mines_Debris_Detection_And_Segmentation/tree/07dfc61685c2ea63485ba7444280789b638ce749).
The original checkpoint SHA-256 is
`b6d82043f04c24ab66637f04cea0ffc2263a57cea9b01c0a7e15d55149274cff`.
The author's MIT notice is retained on the Hugging Face mirror. Conversion used
restricted `weights_only=True` loading with installed Torch/Ultralytics classes,
then a fresh YOLO11n architecture with a strict state dictionary. No third-party
Python source was executed. `scripts/export_fls11.py` records the procedure.

GhostVision's model card specifies CC BY-SA 4.0; its ONNX metadata records
Ultralytics AGPL-3.0. SonarVision's author card specifies MIT and its graph records
AGPL-3.0. FLS11 also inherits Ultralytics terms. Underlying FLS dataset sources
include noncommercial Marine Debris FLS and a mine dataset whose original terms
could not be independently retrieved. No datasets are republished, and this is
not a clearance for commercial deployment. The gated GhostVision dataset card
also contains conflicting CC BY-SA metadata and a GPL paragraph; local evaluation
preserves that evidence and does not redistribute its images or annotations.

## Geometry and runtime checks

- Pipeline strip tiling and threshold remain unchanged.
- GhostVision uses the inspected 640-square graph input and end-to-end
  `[1,300,6]` xyxy/score/class output; its `class_names.txt` verifies `Crab-Pot`.
- FLS11 uses RGB, 640-square centered letterbox and native 11-class YOLO output.
- SonarVision uses BGR, 256-square centered letterbox, matching its author code.
- Specialists preserve aspect ratio and use 114 padding. Inputs above 4:1 must
  be cropped deliberately; these routes do not silently squash sonar strips.
- Fixed specialist confidence is 0.25, class-correct NMS IoU is 0.5, maximum
  detections 300. These thresholds are not newly validation-optimized.

FLS11 native versus exported raw output differs by at most about 0.000855 on
three source examples. Browser versus native FLS predictions have matching counts,
maximum box difference 0.064 pixels and score difference 0.045 percentage points.
The author wreck example has a browser/native box difference below 0.053 pixels
and score difference below 0.382 percentage points. These are runtime checks,
not held-out accuracy measurements. Models retain separate class maps and scores.

## GhostVision source-test sample

After the user obtained access, the checker selected **32 records before any
predictions**, using seed 42 and uniform sampling from sorted unambiguous records
in the author's `test` metadata. Dataset revision:
`b6a36ec00c9bb0070f30be4c1dd6cbe139423cd4`. Labels are absolute xywh,
verified against the source schema, image bounds and stored area. Five selected
images have no Crab-Pot labels. Ambiguous Maybe-Crab-Pot records are excluded
before sampling. This does not turn other unlabelled objects into verified
background for unrelated classes.

| Metric | Actual result |
|---|---:|
| Original images / Crab-Pot labels | 32 / 39 |
| TP / FP / FN at score 0.25 and IoU 0.5 | 4 / 3 / 35 |
| Precision / recall | 57.14% / 10.26% |
| AP50 / mAP50–95 | 34.99% / 13.68% |
| False positives per original image | 0.09375 |
| Median CPU image inference, excluding first input | 135.6 ms |

AP uses a score sweep down to 0.001 and 101-point interpolated precision with
class-correct one-to-one matching. It is separate from operational-threshold
precision/recall. Timing includes image loading, preprocessing, inference and
postprocessing in the local Python adapter, Windows 11, Intel Core i5-1335U, ONNX Runtime 1.24.4 (local check; package pins 1.20.1), four CPU threads, 31 timed images
after one initial image; it is not a browser or onboard benchmark.

The result exposes low recall. No threshold, preprocessing or checkpoint was
changed after this check. Filename prefixes include Rec09/Rec9, Rec14 and Rec8;
Rec09 and Rec9 may be the same recording. Training overlap and independence
between physical objects, recordings or surveys are unaudited. No confidence
interval or new-site generalisation claim is made. Aggregate machine-readable
results are in `ghost-pot-sample-check.json`; gated raw data remains local.

## Reproduce and continue

```bash
bluecho models fetch --model ghost-pot --registry ./models
bluecho models verify --model ghost-pot --registry ./models
bluecho inspect ./sonar.jpg --modality SSS --model ghost-pot \
  --registry ./models --output ./new-inspection
# Other model IDs: fls11-debris (FLS_ARIS), sonarvision-sss (SSS).

# HF_TOKEN must be supplied privately by an account with approved dataset access.
python scripts/check_ghost_pots.py download --output ./private-ghost-check --count 32
python scripts/check_ghost_pots.py evaluate --output ./private-ghost-check --registry ./models
```

The next model bottleneck is recall and independent evaluation, not another class
name in the interface. Any model/threshold revision requires a development cycle
using validation data and a fresh untouched holdout. For FLS11, audit source
splits and class geometry before presenting full per-class accuracy. For genuine
nets, obtain labelled real sonar and appropriate weights before exposing support.
