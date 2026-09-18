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
