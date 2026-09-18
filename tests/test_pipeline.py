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


def test_cli_apply_and_rollback(tmp_path, monkeypatch):
    import json
    from graft import cli

    monkeypatch.setattr(cli, "ROOT", tmp_path)

    v1 = tmp_path / "v1.json"
    v2 = tmp_path / "v2.json"

    v1.write_text(json.dumps({
        "version": 1,
        "fields": {
            "total": {
                "path": "$.total",
                "transform": "identity"
            }
        }
    }))

    v2.write_text(json.dumps({
        "version": 2,
        "fields": {
            "total": {
                "path": "$.grand_total",
                "transform": "identity"
            }
        }
    }))

    class Args:
        provider = "orders"
        mapping = str(v1)

    cli.cmd_apply(Args)

    assert json.loads(
        (tmp_path / "mappings" / "orders" / "current.json").read_text()
    )["version"] == 1

    Args.mapping = str(v2)
    cli.cmd_apply(Args)

    assert json.loads(
        (tmp_path / "mappings" / "orders" / "current.json").read_text()
    )["version"] == 2

    class RollbackArgs:
        provider = "orders"

    cli.cmd_rollback(RollbackArgs)

    assert json.loads(
        (tmp_path / "mappings" / "orders" / "current.json").read_text()
    )["version"] == 1


def test_apply_same_version_is_idempotent(tmp_path, monkeypatch):
    import json
    from graft import cli

    monkeypatch.setattr(cli, "ROOT", tmp_path)

    mapping = tmp_path / "candidate.json"
    mapping.write_text(json.dumps({
        "version": 2,
        "fields": {
            "total": {
                "path": "$.grand_total",
                "transform": "identity"
            }
        }
    }))

    class Args:
        provider = "orders"

    Args.mapping = str(mapping)

    cli.cmd_apply(Args)
    first = (tmp_path / "mappings" / "orders" / "current.json").read_text()

    cli.cmd_apply(Args)
    second = (tmp_path / "mappings" / "orders" / "current.json").read_text()

    versions = list((tmp_path / "mappings" / "orders").glob("v*.json"))

    assert first == second
    assert len(versions) == 1
    assert versions[0].name == "v2.json"
