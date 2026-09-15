# Phase3 contract

Use the package, not reimplemented geometry. Existing legacy API endpoints in bluecho.api support health/jobs/review for the pipeline route; they are not a multi-route geolocation web service. New dashboard endpoints are proposed, not implemented or tested: source uploads(hash/dimensions), jobs(explicit model/modality,metadata), cancellation, evidence retrieval, candidate review and report downloads.

Package entrypoints available now: RecordingEngine.predict; geotag_saved; load_sidecar; geotag_box; ReviewQueue; CLI boxes/geotag/validate-sidecar/capabilities/doctor. Accept existing opaque8-bit decoded formats/GeoTIFF and supported XTF,30millionpixels/2GiB; XTF explicitchannel,startordinal,maxpings(0all),chunk1..512. Preserve source SHA256 and metadata hash; never silently resize uploaded pixel coordinates.

Consume results.json original-image xyxy,0..100uncalibrated scores,model identity/native labels,original.png,annotated.png,crops/contexts and quality.png. Progress JSON is emitted on stderr. Exit0 success,2input/dependency error,130cancelled. Completed outputs and recording.json partial status survive cancellation. Decoded coverage is separate from completed inference.

Map layers: detections.geojson(null allowed),footprints.geojson,tracks.geojson,processed_coverage.geojson,coverage.geojson quality,unassessed.geojson descriptions. Display location/uncertainty/class-evidence status and missing reasons. No marker for nullgeometry. Offline vectors.svg/report.html work without a basemap. Metadata-derived points remain estimates. ReviewQueue exports/imports preserve raw predictions and versioned human corrections; no automated groundtruth/retraining. Download the canonical JSON/CSV/GeoJSON with source binding.
