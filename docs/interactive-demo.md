# Real sonar demo

Version 0.6.0 replaces all procedural scenes with six genuine sonar inputs: SubPipe pipeline and seabed samples, Marine Debris FLS propeller/shampoo-bottle source examples, and two NOAA H12907 side-scan mosaic windows.

The dataset builder runs the installed CPU detectors and freezes their actual outputs. Images, results, model hashes, source hashes and timestamps are published together. The UI fetches and verifies those files, then lets operators review, correct and export them. The banner explicitly says saved detector results: opening a demo does not run a model again. Uploads continue to execute the normal inference workflow. Predicted labels may be false alerts; the NOAA examples are not confirmed wreck discoveries. The propeller source also produces a hook prediction, which is retained rather than hidden.

There is no procedural image generation, score randomisation or artificial geographic anchor in the current demo. Legacy synthetic demo jobs are excluded from the active browser library; their stored data is not overwritten. The six scene cards use previews of their real source images. Surprise me excludes the active sample. Real inputs do not have fake generated variations.

## Geolocation

NOAA H12907 GeoTIFF windows preserve their source NAD83/UTM zone 15N (EPSG:26915) affine transforms. The Python engine generates the original geographic results; Proj4js performs the same conversion for reviewer box corrections in the browser. A corrected example agrees with PyProj to less than 0.1 metre numerically. This checks implementation agreement, not field position accuracy. Survey footprints remain visible even for zero-detection results. No object marker is invented for an empty result.

SubPipe and tank examples have no verified per-image geographic metadata in these selected files. Their coordinates remain null, and Map explicitly says location metadata is needed. The tank class label does not imply a location or material composition.

## Sources and redistribution

See `frontend/public/real-demo/ATTRIBUTION.md`: SubPipe CC BY 4.0; Marine Debris FLS CC BY-NC-SA 4.0 for this noncommercial SIH demonstration; NOAA H12907 CC0 1.0, not for navigation. The data licenses are distinct from the software and model licenses. No gated or ambiguous-author images are bundled.

Only lossless RGB decoding to PNG is used for the full images. Pixel arrays are asserted equal to the decoded original files. JPEG previews alone are resized. The FLS input SHA-256 hashes additionally match the corresponding images in the acquired original dataset. `catalog.json` lists every image/result/context hash, and exported results retain source, license and inference provenance.

## Executed workflow

```powershell
$env:PYTHONPATH='src'
python scripts/build_real_demo.py --samples <existing-samples> --noaa <existing-GeoTIFF-windows> --registry <model-registry> --output frontend/public/real-demo --work <new-empty-evidence-directory>
$env:VITE_BROWSER_ENGINE='1'
npm.cmd run build --prefix frontend
node frontend/real-demo-tests.mjs
node frontend/workflow-tests.mjs
$env:VITE_BROWSER_ENGINE='0'
npm.cmd run build --prefix frontend
# Use BLUECHO_URL for the local API server.
node frontend/real-demo-tests.mjs
```

`docs/real-demo-verification.json` records executed checks. Local full inference reports and screenshots are retained under `E:/Hackathon/execution/real_demo_20260915`. Existing source imagery was not overwritten or redownloaded. This release adds no independent benchmark or new training claim.

## Layout refinement in 0.6.1

The main demo picker and Surprise me now use four SubPipe/FLS examples. The two Gulf survey cards are removed from this entry flow; existing saved NOAA reports and their georeferencing remain readable. Report scope sits above an aligned export-button grid. Viewer, review, navigation and demo action groups have consistent heights and spacing. `frontend/alignment-tests.mjs` checks the four-card picker, report downloads and button geometry at 1536, 1024, 768 and 390 pixels.

## Georeferenced example in 0.6.2

The featured picker includes one Georeferenced survey sample (NOAA H12907, east window). Its 1024-pixel image retains the source NAD83 / UTM 15N affine transform. Map and exports use WGS84 estimates derived from that transform. The saved wreck-labelled prediction is unconfirmed, with possible false-alert geometry; neither hazard identity nor position error has field verification. Noaa0 remains outside the picker. All original real-demo asset hashes are preserved. The alignment and real-demo checks cover the five-sample picker.

## Expanded debris library

Eleven public scenes include eight FLS images with all ten debris source labels, pipeline and empty-source examples, and one georeferenced NOAA survey. The collection selector and horizontally scrolling gallery keep the workspace compact. Six new FLS scenes were built with `build_real_demo.py --append-debris`, preserving all original image/result hashes. Every new scene completed real local inference; no score or prediction was invented.

On localhost only, an explicitly prepared `window.BLUECHO_LOCAL_DEMOS` catalog can extend the gallery with approved-access images in a separate private static bundle. The public website ignores that catalog, and the public source does not contain private imagery. GhostVision's dataset metadata says CC BY-SA 4.0 while its card says GPL; this phase keeps its imagery local pending clarification. Real ghost-net detection remains unsupported.

Opening a sample again reuses its saved inspection when its source-result hash matches, preserving review decisions. New source versions receive separate inspections. A direct `?demo=noaa1` link opens the georeferenced sample; the parameter is consumed so reload resumes the saved review.
