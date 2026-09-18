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


def test_current_pointer_matches_existing_version(tmp_path, monkeypatch):
    import json
    from graft import cli

    monkeypatch.setattr(cli, "ROOT", tmp_path)

    mapping = tmp_path / "candidate.json"
    mapping.write_text(json.dumps({
        "version": 3,
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

    provider_dir = tmp_path / "mappings" / "orders"
    current = json.loads((provider_dir / "current.json").read_text())

    assert current["version"] == 3
    assert (provider_dir / "v3.json").exists()


def test_rollback_uses_previous_existing_version_when_gap_exists(tmp_path, monkeypatch):
    import json
    from graft import cli

    monkeypatch.setattr(cli, "ROOT", tmp_path)

    provider_dir = tmp_path / "mappings" / "orders"
    provider_dir.mkdir(parents=True)

    v1 = {
        "version": 1,
        "fields": {
            "total": {
                "path": "$.total",
                "transform": "identity"
            }
        }
    }

    v3 = {
        "version": 3,
        "fields": {
            "total": {
                "path": "$.grand_total",
                "transform": "identity"
            }
        }
    }

    (provider_dir / "v1.json").write_text(json.dumps(v1))
    (provider_dir / "v3.json").write_text(json.dumps(v3))
    (provider_dir / "current.json").write_text(json.dumps(v3))

    class Args:
        provider = "orders"

    cli.cmd_rollback(Args)

    current = json.loads(
        (provider_dir / "current.json").read_text()
    )

    assert current["version"] == 1


def test_rollback_fails_with_only_one_version(tmp_path, monkeypatch):
    import json
    import pytest
    from graft import cli

    monkeypatch.setattr(cli, "ROOT", tmp_path)

    provider_dir = tmp_path / "mappings" / "orders"
    provider_dir.mkdir(parents=True)

    v1 = {
        "version": 1,
        "fields": {
            "total": {
                "path": "$.total",
                "transform": "identity"
            }
        }
    }

    (provider_dir / "v1.json").write_text(json.dumps(v1))
    (provider_dir / "current.json").write_text(json.dumps(v1))

    class Args:
        provider = "orders"

    with pytest.raises(SystemExit, match="no previous version"):
        cli.cmd_rollback(Args)

    current = json.loads(
        (provider_dir / "current.json").read_text()
    )

    assert current["version"] == 1

def test_apply_updates_current_atomically(tmp_path, monkeypatch):
    import graft.cli as cli

    root = tmp_path
    monkeypatch.setattr(cli, "ROOT", root)

    provider_dir = root / "mappings" / "orders"
    provider_dir.mkdir(parents=True)

    old = {
        "version": 1,
        "fields": {
            "id": {"path": "$.id", "transform": "identity"}
        },
    }

    new = {
        "version": 2,
        "fields": {
            "id": {"path": "$.order_id", "transform": "identity"}
        },
    }

    (provider_dir / "v1.json").write_text(
        __import__("json").dumps(old)
    )
    (provider_dir / "current.json").write_text(
        __import__("json").dumps(old)
    )

    candidate = root / "candidate.json"
    candidate.write_text(__import__("json").dumps(new))

    args = type("Args", (), {
        "provider": "orders",
        "mapping": str(candidate),
    })()

    cli.cmd_apply(args)

    assert (provider_dir / "v2.json").exists()
    assert __import__("json").loads(
        (provider_dir / "current.json").read_text()
    )["version"] == 2

def test_rollback_uses_version_below_active_pointer(tmp_path, monkeypatch):
    import json
    from graft import cli

    monkeypatch.setattr(cli, "ROOT", tmp_path)

    provider_dir = tmp_path / "mappings" / "orders"
    provider_dir.mkdir(parents=True)

    for version in (1, 2, 4):
        mapping = {
            "version": version,
            "fields": {
                "id": {
                    "path": f"$.id_{version}",
                    "transform": "identity",
                }
            },
        }
        (provider_dir / f"v{version}.json").write_text(json.dumps(mapping))

    (provider_dir / "current.json").write_text(
        (provider_dir / "v4.json").read_text()
    )

    class Args:
        provider = "orders"

    cli.cmd_rollback(Args)

    current = json.loads(
        (provider_dir / "current.json").read_text()
    )

    assert current["version"] == 2

def test_apply_and_rollback_write_audit_trail(tmp_path, monkeypatch):
    import json
    from graft import cli

    monkeypatch.setattr(cli, "ROOT", tmp_path)

    provider_dir = tmp_path / "mappings" / "orders"
    provider_dir.mkdir(parents=True)

    v1 = {
        "version": 1,
        "fields": {"id": {"path": "$.id", "transform": "identity"}},
    }
    v2 = {
        "version": 2,
        "fields": {"id": {"path": "$.order_id", "transform": "identity"}},
    }

    candidate = tmp_path / "candidate.json"
    candidate.write_text(json.dumps(v2))

    class Args:
        provider = "orders"
        mapping = str(candidate)

    cli.cmd_apply(Args)

    cli.cmd_apply(Args)

    (provider_dir / "v1.json").write_text(json.dumps(v1))
    cli.cmd_rollback(Args)

    audit = tmp_path / ".graft" / "audit.jsonl"
    events = [
        json.loads(line)
        for line in audit.read_text().splitlines()
    ]

    assert [event["action"] for event in events] == [
        "apply",
        "apply",
        "rollback",
    ]
    assert events[0]["version"] == 2
    assert events[2]["from_version"] == 2
    assert events[2]["to_version"] == 1

def test_cli_audit_displays_audit_events(tmp_path, monkeypatch, capsys):
    from graft import cli
    from graft.audit import record_audit

    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli, "STATE", tmp_path / ".graft")

    record_audit(
        tmp_path,
        "apply",
        "orders",
        version=2,
        mapping="mappings/orders/v2.json",
    )

    class Args:
        pass

    cli.cmd_audit(Args)

    output = capsys.readouterr().out

    assert '"action": "apply"' in output
    assert '"provider": "orders"' in output
    assert '"version": 2' in output


def test_snapshot_registers_contract(tmp_path, monkeypatch):
    import json
    from graft import cli

    monkeypatch.setattr(cli, "ROOT", tmp_path)

    fixture_dir = tmp_path / "fixtures" / "orders" / "orders"
    fixture_dir.mkdir(parents=True)

    fixture_dir.joinpath("fixture.json").write_text(
        json.dumps({
            "body": {
                "order_id": "ord_1",
                "total": "42.50",
            }
        })
    )

    class Args:
        provider = "orders"
        endpoint = "orders"

    cli.cmd_snapshot(Args)

    registry = json.loads(
        (tmp_path / ".graft" / "contracts.json").read_text()
    )

    assert registry["orders/orders"]["provider"] == "orders"
    assert registry["orders/orders"]["endpoint"] == "orders"
    assert registry["orders/orders"]["schema"] == "snapshots/orders/orders.json"


def test_check_detects_drift_from_latest_fixture(tmp_path, monkeypatch):
    import json
    from graft import cli

    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli, "STATE", tmp_path / ".graft")

    fixture_dir = tmp_path / "fixtures" / "orders" / "orders"
    fixture_dir.mkdir(parents=True)

    from graft.inferencer import _fingerprint_value

    fingerprint = _fingerprint_value("42.50")

    old_schema = {
        "version": 1,
        "paths": {
            "$": {
                "types": ["object"],
                "nullable": False,
                "presence_rate": 1.0,
                "value_fingerprint": [],
            },
            "$.total": {
                "types": ["string"],
                "nullable": False,
                "presence_rate": 1.0,
                "value_fingerprint": [fingerprint],
            }
        },
    }

    fixture = {
        "body": {
            "grand_total": "42.50",
        }
    }

    old_path = tmp_path / "old.json"
    old_path.write_text(json.dumps(old_schema))
    (fixture_dir / "latest.json").write_text(json.dumps(fixture))

    class Args:
        provider = "orders"
        endpoint = "orders"
        old = str(old_path)

    cli.cmd_check(Args)

    diff_result = json.loads(
        (tmp_path / ".graft" / "last_diff.json").read_text()
    )

    assert diff_result["changes"]
    assert diff_result["changes"][0]["kind"] == "RENAMED"


def test_check_detects_drift_from_latest_fixture(tmp_path, monkeypatch):
    import json
    from graft import cli

    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli, "STATE", tmp_path / ".graft")

    fixture_dir = tmp_path / "fixtures" / "orders" / "orders"
    fixture_dir.mkdir(parents=True)

    from graft.inferencer import _fingerprint_value

    fingerprint = _fingerprint_value("42.50")

    old_schema = {
        "version": 1,
        "paths": {
            "$": {
                "types": ["object"],
                "nullable": False,
                "presence_rate": 1.0,
                "value_fingerprint": [],
            },
            "$.total": {
                "types": ["string"],
                "nullable": False,
                "presence_rate": 1.0,
                "value_fingerprint": [fingerprint],
            }
        },
    }

    fixture = {
        "body": {
            "grand_total": "42.50",
        }
    }

    old_path = tmp_path / "old.json"
    old_path.write_text(json.dumps(old_schema))
    (fixture_dir / "latest.json").write_text(json.dumps(fixture))

    class Args:
        provider = "orders"
        endpoint = "orders"
        old = str(old_path)

    cli.cmd_check(Args)

    diff_result = json.loads(
        (tmp_path / ".graft" / "last_diff.json").read_text()
    )

    assert diff_result["changes"]
    assert diff_result["changes"][0]["kind"] == "RENAMED"


def test_check_resolves_registered_contract_without_old_path(tmp_path, monkeypatch):
    import json
    from graft import cli
    from graft.registry import register_contract

    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli, "STATE", tmp_path / ".graft")

    fixture_dir = tmp_path / "fixtures" / "orders" / "orders"
    fixture_dir.mkdir(parents=True)

    schema_path = tmp_path / "snapshots" / "orders" / "orders.json"
    schema_path.parent.mkdir(parents=True)

    schema = {
        "version": 1,
        "paths": {
            "$": {
                "types": ["object"],
                "nullable": False,
                "presence_rate": 1.0,
                "value_fingerprint": [],
            },
            "$.total": {
                "types": ["string"],
                "nullable": False,
                "presence_rate": 1.0,
                "value_fingerprint": [],
            },
        },
    }

    schema_path.write_text(json.dumps(schema))
    register_contract(tmp_path, "orders", "orders", schema_path)

    (fixture_dir / "latest.json").write_text(
        json.dumps({"body": {"grand_total": "42.50"}})
    )

    class Args:
        provider = "orders"
        endpoint = "orders"
        old = None

    cli.cmd_check(Args)

    diff_result = json.loads(
        (tmp_path / ".graft" / "last_diff.json").read_text()
    )

    assert "$.total" in {
        change.get("path")
        for change in diff_result["changes"]
        if change["kind"] == "REMOVED"
    }
