import provider


def test_provider_rename_drift():
    provider.MUTATE = "rename"

    payload = provider.payload()

    assert "total" not in payload
    assert payload["grand_total"] == "42.50"
