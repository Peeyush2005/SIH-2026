# BluEcho dashboard redesign · 0.2.0

Built for Smart India Hackathon 2026 by Khushi Mhamane, Sharon Melhi, Kirti Rajput, Peeyush Rampal, and Aditya Banerjee.

## Delivered workflow

The website now has a navy navigation rail, a light survey workspace, guided image upload and model selection, a linked image/map view, a searchable anomaly table, persistent review history, and prominent report downloads. Actual job counts replace illustrative statistics. Coordinates use the correct N/S/E/W hemispheres. Unsupported target classes are explicitly identified.

The local Python application preserves its existing input routes, queue, cancellation, metadata handling and JSON/CSV/GeoJSON/HTML/ZIP export contracts. The redesign fixes a stale asynchronous response that could otherwise display the previous job's results after switching inspections. Windows support now includes a platform-specific download lock, atomic-file promotion retry, and sampled worker RSS enforcement in place of Linux-only imports. The Linux training supervisor remains Linux-specific.

## Vercel edition

Vercel serves the application and ONNX Runtime Web assets. Image inference runs in the browser using ONNX Runtime Web 1.30.0, WASM CPU, one thread. First use downloads the exact ONNX model from Hugging Face commit `36055030359ec3c750c4446889c67fe10c5e7271`; SHA256 is verified before execution and on cache reuse. Inputs remain on the user's device. Images, results and review history are stored in IndexedDB. A browser refresh interrupts active inference and labels that job incomplete; completed inspections remain available. Clear site data to remove the workspace; download reports first.

The browser supports PNG/JPEG/BMP and PBM containers with P1/P4/P5/P6 content (P5/P6 require maxval 255). It rejects other depths rather than silently changing intensity. Limits are 32 MiB per source, eight million pixels, 48 tiles, twenty sources, and four queued jobs. TIFF/GeoTIFF, raw XTF and supplementary detectors remain local-app features.

The only web model is `sss-pipeline-v3`, class `Pipeline`. Browser preprocessing reproduces the frozen 640-pixel/480-stride tiling, RGB114 padding, RGB/255 conversion, tile NMS IoU0.7/max100, source NMS IoU0.5 and threshold0.6818633675575256. Adjacent segments are not reconstructed into full physical objects. A near-black row screen provides descriptive image-quality regions; it does not diagnose speckle, shadows, heave, pitch or roll, and it does not alter detector input.

Source-bound affine JSON metadata supports EPSG:4326 and EPSG:3857. Source SHA256, dimensions, modality, transform and coordinate range are validated. Latitude/longitude remain null without supported metadata. Physical dimensions remain unavailable in the browser; pixel box dimensions are always reported. The map is an offline vector view with independently fitted axes, not a navigation chart. Geometry tests using synthetic metadata are not field-position validation.

Browser exports use `bluecho-browser/1.0`; they do not claim conformance to the broader Python result schema. JSON/CSV/GeoJSON and ZIP exports preserve review revision and source/model identity. HTML ZIPs include original/annotated images and local evidence assets. Confidence percentages are uncalibrated model scores.

## Executed verification

- Local backend: dashboard tests and hosted-session access tests passed (5 tests).
- Actual local browser workflow: 14 checks passed, including pipeline inference, SVG alignment, missing geography, NOAA source metadata, review persistence and corrections, five exports, quality requests, zero detections, invalid input, XTF cancellation, saved-example distinction, mobile sizing, and offline browser request blocking.
- Actual browser WASM workflow: 8 checks passed, including a real pipeline image, native comparison, no API/image-upload requests, IndexedDB review persistence, search, exports, synthetic affine map binding, mobile sizing and a real negative image.
- Native/browser pipeline-example score: 70.03985643386841 vs 70.03982067108154 out of100. Maximum box-coordinate difference: 0.0000457763671875 pixels. Both produce one candidate at the unchanged threshold. The negative example produces zero candidates.

This is limited software/runtime parity on existing examples, not new validation/test performance. No shipwreck, cylinder, net, new-site or onboard real-time claim follows from these checks.

## Publication and runtime constraint

Native and ONNX pipeline weights were published at [SharonMelhi/BluEcho-SSS-Pipeline](https://huggingface.co/SharonMelhi/BluEcho-SSS-Pipeline) and remote hashes verified. Original preprocessing/parity manifests, licence and available training source accompany the weights. Other specialist weights remain local because their redistribution evidence is unresolved.

Hugging Face rejected creation of a CPU Docker Space with HTTP402: this account requires a PRO subscription for that runtime. No subscription or compute purchase was made. The Vercel edition therefore uses working browser inference and has no dependency on a hosted Python API. The optional Docker deployment files remain prepared under `deploy/hf-space/`; they are not a running service.

## Build

```bash
npm ci --prefix frontend
npm run build --prefix frontend                 # local Python dashboard assets
VITE_BROWSER_ENGINE=1 npm run build --prefix frontend  # standalone website
```

`vercel.json` selects the standalone browser build. Vercel is connected to the GitHub repository. The local app remains available through `bluecho serve` with its local registry and storage paths.
