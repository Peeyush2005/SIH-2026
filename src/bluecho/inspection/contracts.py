"""Stable inspection schema and semantic preservation checks."""
from typing import TypedDict,NotRequired
from importlib.resources import files
import json

class Position(TypedDict):
    coordinates: list[float] | None
    status: str
    reason_codes: list[str]
    uncertainty: dict
    altitude_provenance: str
    crs: NotRequired[str]

class InspectionReport(TypedDict):
    schema_version: str
    source_sha256: str
    raw_result_sha256: str
    raw_result: dict
    candidates: list[dict]
    associations: list[dict]
    clear_region_tasks: list[dict]
    ranking_policy: str
    ranked_candidate_ids: list[str]
    accuracy_claim: str


def validate_inspection(report):
    import jsonschema
    from .review import canonical
    import hashlib
    jsonschema.Draft202012Validator(json.loads(files('bluecho.inspection').joinpath('inspection-1.0.schema.json').read_text())).validate(report)
    raw=report['raw_result'];originals=raw['detections']+raw['unvalidated_proposals']
    if [c['original_prediction'] for c in report['candidates']]!=originals:raise ValueError('Raw predictions changed')
    if report['raw_result_sha256']!=hashlib.sha256(json.dumps(raw,sort_keys=True,allow_nan=False).encode()).hexdigest():raise ValueError('Raw result hash mismatch')
    ids=[c['candidate_id'] for c in report['candidates']]
    if sorted(ids)!=sorted(report['ranked_candidate_ids']) or len(set(ids))!=len(ids):raise ValueError('Ranking must preserve all candidate identities')
    for c in report['candidates']:
        if c['source_sha256']!=report['source_sha256']:raise ValueError('Source identity mismatch')
