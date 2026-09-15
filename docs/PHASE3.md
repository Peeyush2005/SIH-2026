# Phase 3 website integration contract (no website implemented)

Reuse the existing API/RecordingEngine rather than creating a second inference stack. An upload must produce an immutable local source ID, SHA256, dimensions, declared modality and storage reference. Metadata uploads are source-bound and versioned. Do not forward recordings to external AI services.

Jobs take source ID, explicit model IDs, modality, channel/window bounds, registry ID and optional verified metadata. Progress events expose stage, current/total and model ID. Job states are queued/running/completed/partial_failure/failed/cancelled. Persist finished windows on cancellation and display unassessed coverage explicitly.

Per-window downloads include unchanged results.json (2.0.0), inspection.json (inspection-1.0), source-pixel overlays/crops, raw bottom trace candidates/accepted/invalid segments, sensor track and target GeoJSON, review bundle and report. Overlay coordinates are original pixel edges; use an explicit display transform in the browser. WGS84 GeoJSON is longitude, latitude. Null locations remain null and sensor tracks never masquerade as object positions. Show provenance, geometry reasons and unknown uncertainty alongside any estimated footprint.

Review actions append supplied identity/time/version events for confirmed labels, corrected boxes, false alerts, missed objects and clear regions. Original detections and prior corrections stay inspectable. Include apparent negatives and diverse source groups. User corrections do not retrain or modify production weights. Expose development export with frozen held-out exclusions and the export receipt.

Warnings must distinguish experimental/unvalidated classes, unknown material, ambiguous bottom, incomplete metadata and sensor-model transfer. Do not claim real ghost nets, measured physical object dimensions or exact coordinates. Existing legacy API routes remain compatible; website authentication, upload quotas and deployment are future work.
