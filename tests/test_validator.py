from pathlib import Path
from graft.validator import check_invariant

def test_sum_invariant():
    body={"line_items":[{"amount":"20.00"},{"amount":"22.50"}],"total":"42.50"}
    assert check_invariant("sum($.line_items[*].amount) == $.total", body, {})


def test_mapping_versions_are_distinct():
    import json

    v1 = json.loads(Path("mappings/orders/v1.json").read_text())
    v2 = json.loads(Path("mappings/orders/v2.json").read_text())

    assert v1["version"] == 1
    assert v2["version"] == 2
    assert v1 != v2


def test_malformed_mapping_is_rejected():
    import pytest
    from graft.mapping import validate_mapping

    malformed = {
        "version": 2,
        "fields": {
            "total": {
                "transform": "identity"
            }
        }
    }

    with pytest.raises(ValueError):
        validate_mapping(malformed)


def test_validator_rejects_candidate_that_produces_null():
    from graft.validator import validate

    old_mapping = {
        "version": 1,
        "fields": {
            "total": {
                "path": "$.total",
                "transform": "identity"
            }
        }
    }

    candidate_mapping = {
        "version": 2,
        "fields": {
            "total": {
                "path": "$.missing",
                "transform": "identity"
            }
        }
    }

    fixtures = [
        {
            "body": {
                "total": 42.5
            }
        }
    ]

    result = validate(
        old_mapping,
        candidate_mapping,
        fixtures
    )

    assert result["valid"] is False
    assert any("candidate produced null" in e for e in result["errors"])
