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

Retain candidate, False alert, Uncertain, Save note and Save correction immediately open a modal while saving. Other page controls cannot be used until the save finishes and the reviewer dismisses the modal. A synchronous guard prevents duplicate submissions. A failed save shows its error and returns the reviewer to the form; it does not claim success.

After saving, the confirmation explains the action and offers the next unreviewed candidate, the saved finding or its inspection report. Review controls stay disabled on that finding until **Edit saved review** is selected. This lock is derived from saved history, so it survives reloads. Editing appends to the history and does not erase earlier decisions. A note preserves the existing decision and does not complete an unreviewed finding. Escape dismisses a completed or failed confirmation, but cannot interrupt a pending save.

**Reports** is a read-only view with source imagery, a review summary, individual findings, available metadata positions, notes and review history, follow-up guidance and exports. Opening an item in Reports & history goes to this report rather than the inspector. **Open finding in inspector** returns to the corresponding candidate. Recording windows are reported separately; report downloads identify the current window and review revision.

Uncertain boxes carry an amber outline and explicit label; false alerts carry grey dashed boxes and a False alert label. These UI decisions do not trigger training, external alerts or automatic rescans.
