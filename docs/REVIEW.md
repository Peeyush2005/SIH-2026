# Review and future development export

`ReviewQueue(path)` stores immutable original items and append-only annotation events in SQLite. `add(item, source_group)` requires source identity and a related-recording group. `annotate(id, action=..., reviewer=..., label=..., box=...)` records supplied reviewer identity, timezone-aware timestamp and annotation version. Corrections change review events, never original predictions. Event hashes make export/import idempotent. Invalid imports are validated transactionally before they can change the destination. Reviewer identity is supplied audit metadata, not authenticated identity proof.

```python
from bluecho.inspection import ReviewQueue
q = ReviewQueue('/absolute/review.sqlite')
# Only execute this when a human has actually reviewed the item:
# q.annotate(candidate_id, action='corrected', reviewer='reviewer-id',
#            label='bottle', box=[10, 20, 60, 80])
bundle = q.export()
q.close()
```

Actions: confirmed, corrected, false_alert, missed_object, clear_region. Missed-object annotations can attach to an apparently clear-region task and supply a box. No apparently clear task is a negative ground-truth label until reviewed. Image bounds are enforced where known. Source family diversity uses round-robin group selection; known same-window overlapping boxes are flagged as possible related observations, retained separately and never asserted independent objects. Unknown repeated geographic correspondence is not associated.

Frozen training/export manifest:

```json
{"heldout_source_sha256": ["64-hex-digest"], "heldout_source_groups": ["validation-survey-family"], "development_source_groups": ["new-reviewed-survey-family"]}
```

`q.development_manifest(frozen)` excludes any held-out hash, held-out related group or group outside the explicit development allowlist. It outputs examples plus exclusion reasons and the frozen manifest hash. Broad group identity is the operator's responsibility: do not assign a new name to a related validation recording to evade the gate. Unknown groups fail closed. This is a future training/export hook only. There is no automatic pseudo-label acceptance, retraining, validation/test tuning or production weight promotion. An independently evaluated future model is required before claiming improved accuracy.

## Decision feedback in the dashboard

After saving Uncertain or False alert, an accessible confirmation explains the saved state, preservation of original predictions and what appears in reports. It offers the next unreviewed candidate, return to the saved finding, and report downloads. Uncertain boxes carry an amber outline and explicit label; false alerts carry grey dashed boxes and a False alert label. These UI decisions do not trigger training, external alerts or automatic rescans. Escape closes the confirmation; native dialog focus containment prevents accidental background actions.
