from graft.provider import HTTPProvider


def test_http_provider_fetch_returns_normalized_response(monkeypatch):
    class FakeResponse:
        status = 200
        headers = {"content-type": "application/json"}

        def read(self):
            return b'{"id": "ord_1", "total": "42.50"}'

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        "graft.provider.urllib.request.urlopen",
        lambda request: FakeResponse(),
    )

    response = HTTPProvider().fetch("http://example.test/orders/1")

    assert response["status"] == 200
    assert response["headers"]["content-type"] == "application/json"
    assert response["body"] == {
        "id": "ord_1",
        "total": "42.50",
    }

def test_cli_record_uses_provider_response(tmp_path, monkeypatch):
    import json
    from graft import cli

    monkeypatch.setattr(cli, "ROOT", tmp_path)

    class FakeProvider:
        def fetch(self, url):
            assert url == "http://example.test/orders/1"
            return {
                "status": 200,
                "headers": {"content-type": "application/json"},
                "body": {"id": "ord_1"},
            }

    monkeypatch.setattr(cli, "get_provider", lambda name: FakeProvider())

    class Args:
        provider = "orders"
        endpoint = "orders"
        url = "http://example.test/orders/1"
        reset = False
        transport = "http"

    cli.cmd_record(Args)

    fixtures = list(
        (tmp_path / "fixtures" / "orders" / "orders").glob("*.json")
    )

    assert len(fixtures) == 1

    recorded = json.loads(fixtures[0].read_text())
    assert recorded["status"] == 200
    assert recorded["body"] == {"id": "ord_1"}


def test_get_provider_returns_http_provider():
    from graft.provider import HTTPProvider, get_provider

    provider = get_provider("http")

    assert isinstance(provider, HTTPProvider)


def test_get_provider_rejects_unknown_provider():
    import pytest
    from graft.provider import get_provider

    with pytest.raises(ValueError, match="Unknown provider"):
        get_provider("unknown")


def test_cli_record_rejects_unknown_transport(tmp_path, monkeypatch, capsys):
    import pytest
    from graft import cli

    monkeypatch.setattr(cli, "ROOT", tmp_path)

    class Args:
        provider = "orders"
        endpoint = "orders"
        url = "http://example.test/orders/1"
        reset = False
        transport = "nope"

    with pytest.raises(SystemExit, match="Unknown provider: nope"):
        cli.cmd_record(Args)


def test_register_contract_persists_provider_endpoint():
    import json
    from graft.registry import register_contract

    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)

        path = register_contract(
            root,
            "orders",
            "orders",
            "snapshots/orders/orders.json",
        )

        registry = json.loads(path.read_text())

        assert registry["orders/orders"] == {
            "provider": "orders",
            "endpoint": "orders",
            "schema": "snapshots/orders/orders.json",
        }


def test_register_contract_is_idempotent():
    import json
    import tempfile
    from pathlib import Path
    from graft.registry import register_contract

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)

        register_contract(
            root,
            "orders",
            "orders",
            "snapshots/orders/orders.json",
        )

        register_contract(
            root,
            "orders",
            "orders",
            "snapshots/orders/orders.json",
        )

        registry = json.loads(
            (root / ".graft" / "contracts.json").read_text()
        )

        assert list(registry) == ["orders/orders"]
        assert len(registry) == 1
