# Models, licenses and offline use

The packaged catalog is authoritative for IDs, native class order, architecture, geometry, preprocessing, frozen thresholds, score semantics, checksums and validation scope. `bluecho capabilities` prints it without loading a model. It contains no weights. Native v3 and FLS hashes are preserved; ONNX hashes are retained in their original manifests. Third-party downloads are pinned by full SHA256 and source revision. No remote AI service is involved.

- v3: existing pipeline baseline, inherited Ultralytics AGPL and SubPipe CC BY 4.0 provenance (OceanScan MST / REMARO). Local weight import requires original manifest beside native.pt. Native inference works after import. Optional ONNX use requires separately importing the original ONNX artifact with its original manifest hash.
- FLS development: trained detector, MarineDebrisFLS Zenodo 15101686 CC BY-NC-SA 4.0, inherited model terms. Local authorized weights only; not relabeled permissive or uploaded as release assets.
- UATD: pinned original research checkpoint; redistribution permission unclear. Linux bubblewrap isolates a strict `weights_only=True` conversion against an explicit architecture/global allowlist. The source digest and derived digest are both recorded. No unrestricted unpickling fallback exists. Requires the pinned Torch/Ultralytics environment and bubblewrap. Already converted files can be reused with their trusted local registry and conversion receipt.
- Drishti: pinned source ONNX, author MIT notice does not resolve all inherited model/data terms. Direct-source download only; no bundled public weight. Synthetic ghost_net remains unvalidated. No actual net detector is advertised.

Prefetch online with `bluecho models fetch ...`, then `bluecho models verify ...`. Copy the entire resulting registry (including catalog entry and conversion receipt where applicable) to the offline host. Install the tested wheel and CPU dependency wheels from an explicit wheelhouse. Run the same `bluecho inspect` command with the relocated registry; no original workspace path is needed. Missing/incompatible files and checksum failures stop clearly. Download completion uses atomic promotion; resumable partial downloads and HTML/error payload rejection are inherited from the verified downloader.

The Linux CPU environment was provisioned with explicit torch 2.4.1+cpu and torchvision 0.19.1+cpu. Ultralytics also installs an NVIDIA management-library Python binding (`nvidia-ml-py`); this is not a CUDA runtime. Check the release footprint receipt for the actual dependency inventory. Bare `[inference]` installation is not promised CUDA-free unless CPU Torch is selected first.

## Added in version 0.4

`ghost-pot`, `fls11-debris` and `sonarvision-sss` have pinned direct ONNX acquisition and browser support. See [specialist evidence and source licences](specialists-0.4.md). These routes retain separate sensors and class maps. Crab-pot source-sample recall is low; mine outputs remain unvalidated proposals. No third-party model is presented as newly trained by BluEcho.
