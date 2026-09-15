# BluEcho local inspection dashboard · 0.1.4

Team BluMatrix · SIH26-26057. The dashboard is a local review application over the existing RecordingEngine. No model training, altered thresholds or automatic learning occurs.

## Install and start

Tested on Linux x86-64, Python 3.12.14, Node 20.11.1 (build only), Chrome 153, CPU. Other operating systems and Python versions are not verified. Install the supplied wheel; production PyPI publication is blocked pending publisher access. Do not assume this version can be installed from PyPI yet.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install torch==2.4.1+cpu torchvision==0.19.1+cpu --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install './dist/bluecho_sonar-0.1.4-py3-none-any.whl[inspection,inference,onnx,geospatial,api]'
.venv/bin/python -m pip check
.venv/bin/bluecho doctor
.venv/bin/bluecho serve --registry '/path/to/verified registry' --storage '/path/to/inspection data' --port 8011
```

Open http://127.0.0.1:8011. The built frontend is included in the wheel: no Node runtime, CDN, online map or API key is required. The same server supplies the API. `/api/v1/health` is the health check. `/docs` provides interactive OpenAPI; `/openapi.json` is its schema. Imports and CLI help do not download weights or start inference.

For the supplied handoff example, append `--examples /absolute/path/to/demo/examples.json`. Paths inside that manifest resolve relative to it. The manifest is an administrator file, never a browser upload. Its source identity is inspected again before each run. “Run example” does actual inference; “Open saved example” copies clearly labelled saved evidence. User uploads never reuse example predictions.

Use Ctrl-C to stop a foreground server. Jobs continue when a browser closes but cannot run after the backend or computer stops. A restart marks queued/active jobs failed with an interruption message and preserves exported windows; automatic resume is not supported. Create a new inspection explicitly. For a persistent local session, run the command through your existing systemd user service or another local process supervisor. No cloud runtime is included.

## Prepare cached weights and offline dependencies

Follow [MODELS.md](MODELS.md) and the packaged model manifests. There are no model weights in the wheel or source archive. Administrative acquisition commands verify pinned hashes and preserve specialist conversion restrictions:

```bash
.venv/bin/bluecho models fetch --model sss-wreck-experimental --registry '/path/to/verified registry'
.venv/bin/bluecho models verify --model sss-wreck-experimental --registry '/path/to/verified registry'
```

For models with redistribution/acquisition restrictions, use the documented direct-source or local-path import flow. Do not use arbitrary checkpoint code, unrestricted unpickling or uploaded model files. Fetch once while connected, verify all required routes, then disconnect. Download the CPU dependency wheels to a wheelhouse while connected if installation must also occur offline; `pip download` must use the explicit CPU torch versions above, followed by package extras with the normal package index. Verify `pip check` after offline installation. The included locked runtime list records the actual tested environment rather than promising a GPU-free resolution with unspecified torch versions.

## Five-minute demonstration

1. **0:00–1:00** New inspection → choose `pipeline_positive.pbm` from your existing Phase1 samples. Confirm **SSS_LF**, choose **sss-pipeline-v3**, Start inspection. One automatic pipeline box is expected for this exact verified sample. For a portable handoff with no Phase1 inputs, Run the included NOAA example using the verified wreck route instead.
2. **1:00–2:00** Click a box or candidate row; zoom, drag to pan, Fit image. Coordinates are original pixel edges. Cyan shows automatic boxes; violet shows reviewer corrections, with the original box dashed. Scores are uncalibrated model scores, not probabilities of correct identification.
3. **2:00–3:00** Open the NOAA example in a live run. Map uses genuine raster metadata; inspect the large boundary-spanning boxes as possible false alerts. No wreck discovery is claimed. Toggle points, footprints, tracks, processed extent and quality independently. Unassessed regions without supported geometry remain descriptions. No online basemap is needed; the vector display fits longitude/latitude axes independently and is not a navigation chart.
4. **3:00–4:00** Add a reviewer/note, mark uncertain or false alert, then correct a box with original `x1,y1,x2,y2`. The backend recomputes its geography. Refresh and inspect history. A stale tab receives HTTP409 instead of overwriting another review. Reviews do not establish field verification and never change production weights.
5. **4:00–5:00** Export all candidates as JSON/CSV/GeoJSON or portable HTML/evidence ZIP. Current revision is recorded. For XTF, select channel, starting ordinal, limit (0 = all remaining) and window size. Cancel during processing: only successfully exported windows remain. Other channels and unprocessed pings remain unassessed.

## User guide and boundaries

- Inputs: decoded PNG/JPEG/BMP/PBM/TIFF, georeferenced TIFF and supported port/starboard XTF. Content is validated. No SL2 or raw ARIS decoder. Maximum 2 GiB source, 30 million decoded pixels, metadata 32 MiB, 1–512 pings/window. FLS development fan images must be at most672pixels/side; there is no silent resize. An image extension does not establish modality.
- One active CPU worker, eight queued/active jobs maximum, one cached model. Linux worker virtual address limit8GiB; the demonstrated service additionally has a4GiB RSS cgroup limit and400% CPU quota. Queue limits and cancellation prevent parallel model accumulation. Source quota500 plus3GiB free-space guard. Local administrators manage old storage; no automatic evidence deletion.
- Missing geographic prerequisites preserve detections with null positions. XTF first return is not assumed vertical altitude. The supplied real recording still lacks defensible altitude/attitude/navigation prerequisites; no increased position coverage is claimed. The dashboard does not rerun bottom-tracker experiments or manufacture altitude.
- Location estimates and approximate box footprints come from Python geotagging. Metres describe mapped image extent, not actual object dimensions or height. Position uncertainty is unknown without an explicit error model. Synthetic geometry checks are software tests, not measured field accuracy.
- Review supports retaining candidates, false alerts, uncertainty, notes, labels and boxes. Original predictions are immutable; SQLite events record identity, revision, timestamp and old/new values. Human corrections are not relabelled as automatic predictions. Empty regions can be flagged “Needs another scan” with a reason. No autonomous mission planning or automatic training ingestion occurs.
- Display score filtering only hides returned candidates. It cannot recover proposals discarded at the unchanged inference threshold. Export defaults to all candidates; displayed-only scope is explicit. False alerts remain in exports with their review status.
- Portable HTML downloads as a ZIP containing local images, crops, vectors, review records and immutable original predictions. Unzip before opening `report.html`. JSON/CSV/GeoJSON use the same current revision. Export is per selected window; source/window references and recording extent are included. Download each completed window needed from a partial recording.
- Back up the entire storage directory after stopping the server: `application.sqlite`, `sources`, `jobs`, `exports`. Do not copy only SQLite if evidence images are needed. Restart with the same storage path to recover history. Review exports are additive evidence; automatic review import into a different source/session is deliberately not exposed in the browser.

## Capability matrix

| Route | Modality | State and evidence |
|---|---|---|
| sss-pipeline-v3 | SSS_LF | Runnable; limited earlier correlated-frame validation:179TP,129FP,186FN/674frames, precision58.12%,recall49.04%. Unchanged. |
| sss-wreck-experimental | SSS | Runnable; author-image overlap unknown, no independent accuracy claim. Other native class proposals remain unvalidated. |
| uatd-fls | FLS_UATD | Runnable supplemental cylinder/source classes; source overlap unknown. |
| fls-debris-development | FLS_ARIS decoded | Runnable trained10-class development detector; no independent benchmark. Bottle shape does not identify plastic. |
| SSS cylinder | SSS | Unavailable validated capability. FLS does not fill the gap. |
| Real entangled nets | SSS | Unavailable. Generic/unvalidated proposals are not confirmed ghost-net detections. |

## API and schema migration

Versioned `/api/v1` wraps the installed package; the legacy pipeline API and existing CLI remain intact. `bluecho serve` is new. Use `/openapi.json` for exact request fields. Source/job IDs are opaque; clients cannot supply arbitrary filesystem paths or model URLs.

Upload `/sources` multipart, optionally `/sources/{id}/metadata`, then POST `/jobs` with explicit model IDs/modality/extent. Poll `/jobs/{id}`; consume actual stage, elapsed time and completed-window list. POST `/jobs/{id}/cancel` requests cooperative cancellation. GET `/jobs/{id}/windows/{window}` returns the canonical current view, and its `/evidence/{relative_name}` serves only managed image assets. POST `/review/{candidate}` and `/rescan` require current revision. POST `/geotag` accepts a source-bound JSON sidecar and creates a new no-inference job preserving current corrections/history. POST `/export` requires revision, format, scope and optional displayed IDs.

Automatic engine output remains schema2.0.0. The dashboard produces backward-shaped schema2.1.0 with explicitly allowed review states, `original_prediction`, review history/revision and job state. Both schemas are packaged and validated. Immutable originals remain schema2.0.0. Consumers that pinned2.0's `review_state="unreviewed"` must opt into2.1 for reviewed results. No detector output, threshold, original coordinate convention or score interpretation changes.

## Safety and troubleshooting

This prototype binds127.0.0.1 only. Local-host validation and same-origin write checks block ordinary cross-origin browser writes. This is not a multi-user security boundary. Do not expose it publicly without authentication, session isolation, HTTPS and server quotas. No public deployment is provisioned.

- **Weights missing/dependency missing:** follow model setup; `bluecho doctor`, `models verify`, and `pip check`. “Ready” reflects files/dependencies; cryptographic verification happens when loading.
- **Modality error:** confirm the sonar sensor; SSS_LF pipeline preprocessing is not interchangeable with arbitrary SSS or FLS.
- **Metadata rejected:** inspect sourceSHA256, dimensions, modality, CRS and source/window binding. Detection works without geography.
- **Review changed:** refresh, inspect current history and reapply the intended edit.
- **Interrupted/failed:** completed windows remain available. Worker errors appear without a traceback; administrator `jobs/<id>/worker.log` contains local diagnostics. Retry as a new job after resolving the actual cause.
- **No detections:** show quality, preserve the source and record scan concerns. Do not interpret it as verified clearance.
- **Port occupied:** select another loopback `--port`; use that same origin in the browser.

## Attribution and release status

Preserve the project AGPL-3.0-or-later license. See [MODELS.md](MODELS.md), catalog manifests and acquisition evidence for independent model/data terms. The portable NOAA window derives from NOAA survey H12907 (CC0/public US-government survey data); it is a georeferencing example, not object ground truth. Other author/UATD/SubPipe samples remain in the user's original workspace; the public source release does not redistribute them or restricted weights.

Local builds and tests are reported separately from remote CI. GitHub write attempt:403 Resource not accessible by integration. Authorize repository Contents write for the integration or configure local authenticated Git access for Sharon-codes/SIH-2026, then push the prepared branch without overwriting history. PyPI:PUBLISH_BLOCKED; configure a securely stored replacement credential for the owned project or a pending Trusted Publisher for owner Sharon-codes, repository SIH-2026, workflow release.yml, environment pypi. Never paste tokens into chat. A404 name lookup is not proof of registrability. No remote release/publication is claimed.
