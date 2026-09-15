# Interactive demo and workspace refresh

Version 0.5.0 adds **Try demo** to the ocean homepage and empty inspection workspace. Reports also offers **Explore a demo**.

## Explore without setup

A click generates a sonar-like canvas and opens the normal inspection controls. Choose Pipeline corridor, Scattered returns or Interrupted coverage. Shuffle regenerates a scene with a new cryptographic random seed; the deterministic scene renderer preserves that seed in provenance. Select contacts, pan and zoom, adjust display contrast, review or correct boxes, view the fictional map, record scan requests and export reports. Reviews survive reload through browser IndexedDB. No model or dataset download is needed for the demo.

These are procedural interface fixtures. Images, contacts, scores and geographic coordinates are simulated. The image has a baked-in simulation watermark; the workspace, map and exported results explicitly identify the demo. They are not model predictions, measured accuracy or real survey observations. Real-source inference still requires an appropriate model and sensor selection. Demo results cannot accept real geotagging metadata.

Demo jobs and sources have reserved IDs and explicit provenance. The local edition routes only those jobs through the browser fixture store; real inspections continue through its Python API. Demo history is limited to twelve scenes and can be cleared from Reports without removing uploaded inspections. Clearing browser site data also removes demo history. Structured exports retain the simulation flags; PDF and HTML include visible disclosures.

## A consistent working interface

Reports now provides filename search, upload/demo/attention filters and readable inspection rows, with batch processing tucked into a disclosure. Models groups specialists by sonar type and presents scope, classes, source links and model selection. The inspection viewer, contact review, filters and report downloads use the same ocean palette and responsive layout. The homepage retains its sonar animation, motion control, problem, solution and features without numeric marketing claims.

## Executed verification

See `demo-verification.json`. Both production build modes compile with TypeScript. Headless Chrome exercised demo creation, no model downloads, review persistence, random regeneration, coverage, map selection, exports, search, sensor filters and mobile layout in browser and local editions. The browser workflow also ran two real pipeline images sequentially, tested review/PDF exports and confirmed demo clearing preserves real jobs. The local API regression checked real inference, image geometry, metadata, corrections, all exports and partial XTF cancellation. Local evidence and screenshots are under `E:/Hackathon/execution/demo_20260915`; raw survey examples are not added to this repository.

Commands actually executed from the repository (PowerShell):

```powershell
$env:VITE_BROWSER_ENGINE='1'
npm.cmd run build --prefix frontend
node frontend/demo-tests.mjs
node frontend/workflow-tests.mjs
node frontend/minimal-website-tests.mjs
$env:VITE_BROWSER_ENGINE='0'
npm.cmd run build --prefix frontend
$env:BLUECHO_URL='http://127.0.0.1:8013'
node frontend/demo-tests.mjs
# Local API regression additionally requires BLUECHO_DEMO_ROOT and BLUECHO_EVIDENCE.
node frontend/tests.mjs
```

`BLUECHO_URL`, `BLUECHO_EVIDENCE`, `BLUECHO_DEMO_ROOT` and `CHROME` allow separate server, evidence, sample and browser paths. Native detector weights and their validation evidence are unchanged by this release.
