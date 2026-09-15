# BluEcho inspection desk 0.3

## Repository review, 15 September 2026

This was a source inspection, not a comparative accuracy benchmark. Neither external project's code nor weights were incorporated. All new implementation is original BluEcho code.

- [Marine Anomaly Intelligence](https://github.com/vineeth29/SIH26057-Marine-Anomaly-Intelligence/tree/4e7d3b7f2656137ef36f2ebca7437745858e0e67): reviewed README, MIT licence, detection and reporting pages, and evaluation report. Useful product ideas include explicit operator decisions and PDF delivery. Its reported scores were not reproduced on BluEcho data.
- [DeepScan-AI](https://github.com/pathaksidharth06-rgb/DeepScan-AI/tree/c60dd6c9150e8be2ba6e6f8080a24213409430f1): reviewed README, backend prediction/batch/feedback code, analysis, insights and batch components. Its backend defines 11 class names, including Boulder; Unknown Anomaly is described separately in the README. Batch submission, persistent review and annotation-candidate export are useful workflows. No licence was identified in the repository metadata/root during this review, so no source or assets were reused. The presence of a taxonomy does not independently establish accuracy or training provenance.

## Eleven product capabilities, with explicit scope

| Capability | BluEcho implementation and boundary |
|---|---|
| 1. Image ingestion | Browser PNG/JPEG/BMP/portable images; additional raw XTF/TIFF support in local app |
| 2. Multi-image workflow | New batch submission, up to four files, sequential jobs with individual status/errors |
| 3. AI detection | Existing frozen, hash-verified pipeline ONNX detector in browser; separate local routes |
| 4. Quality inspection | Existing quality-region display; new display-only brightness/contrast preserves inference input |
| 5. Image inspection | Original coordinates, pan/zoom, selectable contacts and expanded focus workspace |
| 6. Human decisions | Persistent retain, false-alert, uncertain, note, corrected label/box actions |
| 7. Guided review | New contact queue, review progress, optional next-unreviewed selection, J/K navigation |
| 8. Review data export | New versioned annotation-candidate JSON with source hash, geometry, original prediction and audit history |
| 9. Geolocation | Source-bound metadata estimates; new local map projection preserves aspect ratio; absent coordinates remain absent |
| 10. Survey evidence delivery | New PDF brief alongside existing JSON/CSV/GeoJSON/HTML/evidence ZIP |
| 11. Local history and provenance | Persistent per-source jobs/revisions, model/source hashes and honest model-coverage display |

The public model remains Pipeline-only. This release adds no nets, materials, wreck accuracy, physical-object identity, hazard calibration, ecological risk scoring or new training results. Human agreement is not labelled as model accuracy. Review exports need exhaustive annotation checks, grouping, independent holdouts and licence checks before a future training cycle.

## Interaction and implementation

The existing marine navy/teal identity is retained with larger controls and clearer contact-review hierarchy. Focus view hides surrounding navigation; Exit focus or Escape restores it. J/K navigation is disabled inside editing controls and with command modifiers. Brightness/contrast affect only the displayed SVG image. Reports use the original image and current boxes.

Batch submission requires a shared sensor/model choice; do not mix sonar modalities or frequency channels in one batch. Raw XTF batches are excluded. Existing engine quotas can reject individual jobs; successful submissions remain in history. Sources without metadata can be enriched individually after inspection.

PDF and curation exports fetch the current result and refuse a stale review revision. Export scope applies to contacts in the selected window; quality counts refer to that window. The PDF includes complete available contact audit entries and an image with current boxes. Unsupported characters in the standard PDF font become question marks, disclosed in the brief; original text is retained in JSON. The PDF is an inspection brief, not a certified survey or field sign-off.

The map uses a common scale in a local longitude/cos(latitude) and latitude approximation, with longitude wrapping around its reference point. This corrects independent-axis distortion, but is not a global navigation projection. No position is invented for missing metadata.

## Verification

- Existing browser suite: real positive/negative inference, native score/box parity, no source-upload/API traffic, review persistence, search, structured/evidence exports, synthetic source-bound geometry, mobile width.
- New `frontend/workflow-tests.mjs`: two real batch images, display geometry invariance, focus exit, reviewed curation export, real-image PDF download, export scope, persisted review progress and mobile layout.
- Generated PDF parsed and rendered locally with PyMuPDF; source, score, reviewer and decision checked.
- Both Vite build modes compile with TypeScript. Python dashboard/session tests remain applicable; full Python tests run in Linux CI.

Local test fixtures require prepared sonar samples; they are not bundled or uploaded with the package. Override `BLUECHO_URL`, `BLUECHO_DEMO_ROOT`, `BLUECHO_EVIDENCE`, and `CHROME` to run the browser suites elsewhere. The workflow suite targets the browser build. Synthetic metadata checks validate software geometry only.

Dependencies: jsPDF 4.2.1 (MIT) generates PDFs locally and is loaded when needed. Its licence is preserved in frontend licences. The detector weights, operating threshold, tiling and preprocessing are unchanged.
