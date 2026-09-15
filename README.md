# BluEcho

**Local sonar inspection, detection, and evidence review.**

[Live dashboard](https://bluecho-sih-2026.vercel.app) · [Model weights](https://huggingface.co/SharonMelhi/BluEcho-SSS-Pipeline) · [PyPI package](https://pypi.org/project/bluecho-sonar/) · [Source code](https://github.com/Sharon-codes/SIH-2026) · [Documentation](https://github.com/Sharon-codes/SIH-2026/tree/main/docs) · [Report an issue](https://github.com/Sharon-codes/SIH-2026/issues)

BluEcho is a Python toolkit and local dashboard for turning sonar imagery into reviewable detection results. It brings together model inference, annotated images, human review, and structured exports in a workflow that can run offline after dependencies and model files have been prepared.

**Created for the Smart India Hackathon (SIH) 2026 by Khushi Mhamane, Sharon Melhi, Kirti Rajput, Peeyush Rampal, and Aditya Banerjee.**

The project is a research prototype. Its side-scan sonar (SSS) and forward-looking sonar (FLS) routes use separate models with different evidence and limitations; the capability table below explains what each route supports.

## What BluEcho provides

- **Sonar detection:** explicit model and sensor selection, with predictions expressed in original image coordinates.
- **Local inspection dashboard:** a bundled React interface and Python API for running inspections, examining candidates, and reviewing results.
- **Traceable human review:** persistent review history, corrected boxes, labels, and false-alert decisions while preserving original predictions.
- **Portable evidence:** annotated images, object crops, JSON/CSV, GeoJSON, and local HTML review bundles through the relevant inspection and export commands.
- **Source-bound geolocation:** coordinate enrichment when verified raster metadata or a matching sidecar supports it. Results without defensible locations retain null geometry.
- **Controlled model setup:** explicit acquisition or local import, pinned model hashes, and separate model/data licence information.

### Inspection desk, version 0.4

- **Guided human review:** contact queue, completion progress, retain/false-alert/uncertain decisions, optional advance to the next unreviewed contact, and J/K navigation. Notes, reviewers, revisions and original predictions stay attached to each contact.
- **Batch image inspections:** submit up to four images from a confirmed sensor/model combination. Inference runs sequentially; each source has separate results and failures.
- **Focused visual inspection:** an expanded workspace, display-only brightness and contrast, original-pixel bounding boxes, and an aspect-preserving local geographic view.
- **PDF inspection briefs:** download annotated sonar, included contacts, score interpretation, supported coordinates, source/model hashes and operator audit trails. JSON retains full Unicode text where the PDF's standard font cannot represent it.
- **Review-candidate export:** export reviewed annotations for further curation. This is not an exhaustive labelled dataset, field verification, or an automatic retraining loop. False alerts do not turn whole images into verified negatives.

These workflows operate in both the browser edition and the local dashboard. PDF and review exports respect the selected window, review revision and export scope. [Design comparison and implementation notes](docs/inspection-desk-0.3.md) explain the externally reviewed ideas and their limits.

## Website and on-device inference

The [BluEcho website](https://bluecho-sih-2026.vercel.app) runs **four selectable ONNX detectors inside your browser**: pipelines, forward-looking debris, crab pots, and experimental wrecks/debris. A new website layout puts model selection first, with an image-focused workspace and human review controls beside the sonar. Sonar images and review records stay in browser storage; no Python API or paid cloud inference server is required. First use downloads only the selected hash-verified model (approximately 11–38 MB) and the WebAssembly runtime. Switching models releases the previous inference session.

The web edition supports PNG, JPEG, BMP and PBM/portable images (32 MiB, up to 8 million pixels), tiled pipeline detection, image/map review, source-bound affine JSON metadata in EPSG:4326 or EPSG:3857, and PDF/JSON/CSV/GeoJSON/HTML/ZIP downloads. Keep the tab open during inference and export reports before clearing site data. Browser reports use the explicit `bluecho-browser/1.0` schema; the Python API retains its existing schema.

The **local application** provides raw XTF, TIFF/GeoTIFF, additional model routes and broader metadata support. Browser execution is a separate runtime check, not a new accuracy benchmark. Specialists accept cropped frames with aspect ratios up to 4:1; the pipeline route retains its documented strip tiling. Classes and sensor routes remain separate. These integrations do not establish detection of every hazard or higher accuracy than another project.

## Installation

The full application is tested on **Linux x86-64 with Python 3.12**. A GPU is not required for the CPU setup below. Other platforms are not verified for the complete workflow.

Create a virtual environment and install the CPU PyTorch build before the inference dependencies:

```bash
python3.12 -m venv .venv
source .venv/bin/activate

python -m pip install torch==2.4.1+cpu torchvision==0.19.1+cpu \
  --index-url https://download.pytorch.org/whl/cpu
python -m pip install --upgrade 'bluecho-sonar[inspection,inference,onnx,api]'

bluecho --version
bluecho doctor
bluecho capabilities
```

The package name is `bluecho-sonar`; the Python import and command are both `bluecho`. The base package requires only NumPy and Pillow. Optional extras provide inspection, inference, ONNX, geospatial, API, and training dependencies. Add the `geospatial` extra when working with raster georeferencing.

Large detector weights and datasets are acquired separately. The distribution includes model metadata and small fitted verifier parameters. See the [model setup guide](https://github.com/Sharon-codes/SIH-2026/blob/main/docs/MODELS.md) for acquisition, verification, licensing, and offline installation.

## Quick start

### 1. Prepare a model

For the new specialists, use `bluecho models fetch --model ghost-pot --registry "$HOME/.cache/bluecho/models"` (or `fls11-debris` / `sonarvision-sss`). Use the corresponding sensor route from the table below. [Version 0.4 model evidence](docs/specialists-0.4.md) records source attribution, measured checks and limitations.

The experimental SSS route has a pinned ONNX download of approximately 43 MiB. Review its model/data terms using `bluecho capabilities` before use:

```bash
bluecho models fetch --model sss-wreck-experimental \
  --registry "$HOME/.cache/bluecho/models"
bluecho models verify --model sss-wreck-experimental \
  --registry "$HOME/.cache/bluecho/models"
```

This route produces experimental candidates; an independent wreck benchmark is unavailable.

### 2. Inspect a local image

Replace the example paths with your own input and a new output directory:

```bash
bluecho inspect '/absolute/path/sonar.jpg' \
  --modality SSS \
  --model sss-wreck-experimental \
  --registry "$HOME/.cache/bluecho/models" \
  --output '/absolute/path/new-inspection'
```

`inspect` runs on CPU and writes model results and a separate inspection record per window. Select the route that matches the source sensor; SSS and FLS inputs are not interchangeable.

### 3. Open the dashboard

```bash
bluecho serve \
  --registry "$HOME/.cache/bluecho/models" \
  --storage "$HOME/bluecho-inspections" \
  --port 8010
```

Open **http://127.0.0.1:8010** in your browser. The frontend is included in the package, so running it does not require Node.js. The local server provides interactive API documentation at `/docs`.

See the [dashboard guide](https://github.com/Sharon-codes/SIH-2026/blob/main/docs/DASHBOARD.md) for the inspection workflow, review controls, exports, and troubleshooting.

## Models and evidence

| Model | Sensor route | Intended labels | Current evidence and setup |
| --- | --- | --- | --- |
| `sss-pipeline-v3` | `SSS_LF` | Pipeline | Evaluated on correlated development observations from one survey. Requires verified local weights and their original manifest. |
| `ghost-pot` | `SSS` | Crab-Pot | GhostVision YOLO26s, source-test sample check; new-survey accuracy unmeasured. Browser and local ONNX. |
| `fls11-debris` | `FLS_ARIS` | 11 source classes | Third-party YOLO11n: propeller, shampoo-bottle and can runtime checks; mine-labelled outputs remain unvalidated proposals. Browser and local ONNX. |
| `sonarvision-sss` | `SSS` | unknown_debris, airplane, mine, wreck | Experimental SonarVision YOLOv8n; mine proposals unvalidated. Browser and local ONNX. |
| `sss-wreck-experimental` | `SSS` | Experimental pipeline and wreck candidates | Pinned ONNX download. Independent wreck performance is unavailable; additional native labels remain unvalidated proposals. |
| `uatd-fls` | `FLS_UATD` | Ten native classes, including cylinder | Selected compatibility sample; source overlap is unknown. Pinned acquisition with restricted conversion on Linux. |
| `fls-debris-development` | `FLS_ARIS` | Ten debris classes | Trained development detector without an independent benchmark. Requires verified local import; inherited CC BY-NC-SA terms apply. |

The FLS debris labels are `can`, `bottle`, `drink-carton`, `chain`, `propeller`, `tire`, `hook`, `valve`, `shampoo-bottle`, and `standing-bottle`. A bottle label alone does not establish plastic composition. FLS cylinder support does not establish SSS cylinder detection. Verified real ghost-net detection is unavailable.

For the pipeline route, keep the original `manifest.json` beside your authorized native checkpoint, then import it:

```bash
bluecho models import --model sss-pipeline-v3 \
  --registry "$HOME/.cache/bluecho/models" \
  --local '/absolute/path/sss-v3/native.pt'

bluecho inspect '/absolute/path/pipeline.pbm' \
  --modality SSS_LF \
  --model sss-pipeline-v3 \
  --registry "$HOME/.cache/bluecho/models" \
  --output '/absolute/path/new-pipeline-inspection'
```

## Interpreting results

Detection scores are **uncalibrated model scores**, not probabilities of correct identification. Repeated views within a survey are correlated, and development results do not establish performance at new sites or across the ocean. An empty result is not proof that an area is clear.

Geolocation depends on verified source metadata and sensor assumptions. BluEcho does not invent latitude, longitude, altitude, surveyed area, or physical object identity when those inputs are absent. Image-based acoustic verifiers remain exploratory and do not establish a physics-informed neural network or foundation model.

Human review records are retained separately from automatic predictions. Reviewing an image does not trigger training or silently change the detector.

## Documentation

| Guide | Contents |
| --- | --- |
| [Dashboard](https://github.com/Sharon-codes/SIH-2026/blob/main/docs/DASHBOARD.md) | Local setup, demonstration, review, exports, and troubleshooting |
| [Models and licences](https://github.com/Sharon-codes/SIH-2026/blob/main/docs/MODELS.md) | Model acquisition, hashes, offline use, and inherited terms |
| [CLI and Python interfaces](https://github.com/Sharon-codes/SIH-2026/blob/main/docs/INTERFACES.md) | Programmatic integration and command reference |
| [Validation](https://github.com/Sharon-codes/SIH-2026/blob/main/docs/VALIDATION.md) | Evaluation evidence and limitations |
| [Review workflow](https://github.com/Sharon-codes/SIH-2026/blob/main/docs/REVIEW.md) | Persistent review records and controlled export |
| [Geolocation](https://github.com/Sharon-codes/SIH-2026/blob/main/docs/GEOLOCATION.md) | Source binding, coordinate enrichment, and missing metadata |
| [Physics assumptions](https://github.com/Sharon-codes/SIH-2026/blob/main/docs/PHYSICS.md) | Sonar geometry, altitude prerequisites, and uncertainty |
| [SSS detection workflow](https://github.com/Sharon-codes/SIH-2026/blob/main/docs/SSS_DETECTION_PHASE1.md) | Boxes, crops, structured outputs, and local HTML reports |
| [Experimental verifiers](https://github.com/Sharon-codes/SIH-2026/blob/main/docs/FINAL_IMPROVEMENT.md) | Optional learned review scores and development comparisons |

## Team · SIH 2026

BluEcho was made for the **Smart India Hackathon 2026** by:

- **Khushi Mhamane**
- **Sharon Melhi**
- **Kirti Rajput**
- **Peeyush Rampal**
- **Aditya Banerjee**

## Licence and acknowledgements

The BluEcho source code is licensed under **AGPL-3.0-or-later**. See [LICENSE](https://github.com/Sharon-codes/SIH-2026/blob/main/LICENSE).

Third-party models, datasets, and examples retain their own licences and attribution requirements. The software licence does not replace those terms. BluEcho acknowledges the researchers and maintainers whose sonar datasets, model releases, and open-source tools support this work; consult the [model documentation](https://github.com/Sharon-codes/SIH-2026/blob/main/docs/MODELS.md) and packaged manifests for source-specific details.

For reproducible bug reports, include the package version, platform, selected model and modality, the command used, and a non-sensitive description of the input. Submit reports through [GitHub Issues](https://github.com/Sharon-codes/SIH-2026/issues).
