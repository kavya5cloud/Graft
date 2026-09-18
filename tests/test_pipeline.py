import json
from pathlib import Path

from graft.differ import diff
from graft.healer import propose
from graft.mapping import apply_mapping


def test_full_drift_heal_and_rollback_pipeline(tmp_path):
    old_schema = {
        "paths": {
            "$.total": {
                "types": ["number"],
                "nullable": False,
                "presence_rate": 1.0,
                "value_fingerprint": ["42.5", "17.0"]
            }
        }
    }

    new_schema = {
        "paths": {
            "$.grand_total": {
                "types": ["number"],
                "nullable": False,
                "presence_rate": 1.0,
                "value_fingerprint": ["42.5", "17.0"]
            }
        }
    }

    old_mapping = {
        "version": 1,
        "fields": {
            "total": {
                "path": "$.total",
                "transform": "identity"
            }
        }
    }

    drift = diff(old_schema, new_schema)

    assert drift["changes"]
    assert drift["changes"][0]["kind"] == "RENAMED"

    candidate = propose(
        old_mapping,
        drift,
        old_schema,
        new_schema
    )

    assert candidate["version"] == 2
    assert candidate["fields"]["total"]["path"] == "$.grand_total"

    payload = {
        "grand_total": 42.5
    }

    result = apply_mapping(payload, candidate)

    assert result["total"] == 42.5

    v1 = tmp_path / "v1.json"
    v2 = tmp_path / "v2.json"

    v1.write_text(json.dumps(old_mapping))
    v2.write_text(json.dumps(candidate))

    current = v2
    assert json.loads(current.read_text())["version"] == 2

    current = v1
    assert json.loads(current.read_text())["version"] == 1
