# Stable Python and CLI interfaces

`from bluecho import RecordingEngine, InspectionSupervisor` lazily exposes the existing engine and new supervisor. `RecordingEngine(registry, device='cpu', cache_models=1)` retains Phase 1 behavior and schema 2.0.0. `InspectionSupervisor(engine).inspect(source, out, model_ids=[...], modality=..., ...)` wraps it. `assess(result, metadata=None, bottom=None)` preserves a deep copy of raw predictions. `batch(inputs, out, **kwargs)` writes incremental per-item PASS/ERROR results; cancellation retains completed outputs. No cross-modality/model score averaging or suppression occurs. Detector score order within each model is default; `ranking='reasons'` is optional and did not improve the recorded review-yield diagnostic.

Source schemas ship inside the wheel: `bluecho/phase1/schemas/result-2.0.0.schema.json`, `sidecar-1.0.schema.json`, and `bluecho/inspection/inspection-1.0.schema.json`. `validate_inspection` additionally enforces original prediction preservation, source identity and ranking completeness. Typed Position and InspectionReport interfaces are in `inspection.contracts`. Review export is version 1.0 with immutable items and hashed events.

Metadata must match source SHA256 and original image dimensions. Ping rows additionally match sample count, side, original ping ID and timestamp. Strict physics adds `flat_seabed_verified`, `level_sensor_verified` and per-ping `altitude_provenance`, `altitude_status`, optional verified `sensor_offset`, and `error_bounds`. These are explicit assertions supplied by the acquisition owner, not inferred facts. Legacy outputs remain separate so stricter null positions do not silently rewrite old schema behavior.

Use `track_bottom(raw, pings, source_sha256=..., config=BottomConfig(...))` for raw ndarray windows; `bluecho bottom samples.npz --metadata metadata.json --output bottom.json` runs conservative defaults. Manual correction input includes source_sha256, raw_array_sha256 from the original trace, and corrections with row/sample; save the original trace and review provenance. `position(x,y,metadata)` returns strict location/uncertainty. `interpolate_navigation` explicitly bounds timestamp gaps. `assess_quality` remains available from `bluecho.phase1.quality`. `export_result` retains the original JSON/CSV/GeoJSON/report exports.

New CLI returns 0 on completion, 2 for input/dependency errors, 130 on cancellation. Legacy batch continues its documented per-item result contract. `inspect` emits structured progress to stderr; result JSON is stdout. Optional dependency errors tell users which extras to install. Imports, help, doctor and capabilities never load weights or contact providers. Explicit outputs and registry paths work outside the checkout and with spaces. Atomic JSON writes and bounded registry caches are preserved.

`associate_aligned(reports, correspondence)` supports explicit verified translation-only common pixel frames, bounded registration error and conservative box overlap. Unknown registration, modality mismatch or errors large relative to the object are skipped. Links report inconsistent aligned labels without deleting candidates, averaging scores, confirming identity or counting them as independent objects. General image registration/geographic object association is not inferred automatically.

Batch example:

```python
from bluecho import RecordingEngine, InspectionSupervisor
supervisor = InspectionSupervisor(RecordingEngine('/absolute/models'))
rows = supervisor.batch(['/absolute/first.png', '/absolute/second.png'],
                        '/absolute/fresh/batch', model_ids=['sss-wreck-experimental'], modality='SSS')
assert all(row['status'] in ('PASS', 'ERROR') for row in rows)
```
