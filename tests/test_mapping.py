import pytest
from graft.mapping import apply_mapping, validate_mapping

def test_nested_array_path():
    body={"line_items":[{"price":"20.00"},{"price":"22.50"}]}
    assert apply_mapping(body,{"version":1,"fields":{"prices":{"path":"$.line_items[*].price"}}})=={"prices":["20.00","22.50"]}

def test_unknown_transform_rejected():
    with pytest.raises(ValueError): validate_mapping({"version":1,"fields":{"x":{"path":"$.x","transform":"shell"}}})


def test_nested_and_array_paths():
    from graft.mapping import apply_mapping

    body = {
        "customer": {"email": "a@example.com"},
        "line_items": [
            {"price": "20.00"},
            {"price": "22.50"}
        ]
    }

    mapping = {
        "version": 2,
        "fields": {
            "customer_email": {
                "path": "$.customer.email",
                "transform": "identity"
            },
            "line_items": {
                "path": "$.line_items[*].price",
                "transform": "identity"
            }
        }
    }

    result = apply_mapping(body, mapping)

    assert result["customer_email"] == "a@example.com"
    assert result["line_items"] == ["20.00", "22.50"]


def test_unsupported_transform_is_rejected():
    import pytest
    from graft.mapping import validate_mapping

    malformed = {
        "version": 2,
        "fields": {
            "total": {
                "path": "$.total",
                "transform": "llm_magic"
            }
        }
    }

    with pytest.raises(ValueError):
        validate_mapping(malformed)


def test_malformed_json_path_is_rejected():
    import pytest
    from graft.mapping import validate_mapping

    malformed = {
        "version": 2,
        "fields": {
            "total": {
                "path": "$.orders[",
                "transform": "identity"
            }
        }
    }

    with pytest.raises(ValueError):
        validate_mapping(malformed)


def test_malformed_default_transform_is_rejected():
    import pytest
    from graft.mapping import validate_mapping

    malformed = {
        "version": 2,
        "fields": {
            "total": {
                "path": "$.total",
                "transform": "default("
            }
        }
    }

    with pytest.raises(ValueError):
        validate_mapping(malformed)


def test_valid_default_transform_is_supported():
    from graft.mapping import apply_mapping

    mapping = {
        "version": 2,
        "fields": {
            "status": {
                "path": "$.status",
                "transform": "default(unknown)"
            }
        }
    }

    assert apply_mapping({}, mapping)["status"] == "unknown"
    assert apply_mapping({"status": "active"}, mapping)["status"] == "active"


def test_invalid_integer_coercion_fails_loudly():
    import pytest
    from decimal import InvalidOperation
    from graft.mapping import apply_mapping

    mapping = {
        "version": 2,
        "fields": {
            "count": {
                "path": "$.count",
                "transform": "to_int"
            }
        }
    }

    with pytest.raises((ValueError, TypeError)):
        apply_mapping({"count": "not-a-number"}, mapping)


def test_invalid_datetime_coercion_fails_loudly():
    import pytest
    from graft.mapping import apply_mapping

    mapping = {
        "version": 2,
        "fields": {
            "created_at": {
                "path": "$.created_at",
                "transform": "iso_datetime"
            }
        }
    }

    with pytest.raises((ValueError, TypeError)):
        apply_mapping({"created_at": "not-a-datetime"}, mapping)


def test_unix_timestamp_to_iso_is_deterministic():
    from graft.mapping import apply_mapping

    mapping = {
        "version": 2,
        "fields": {
            "created_at": {
                "path": "$.created_at",
                "transform": "unix_to_iso"
            }
        }
    }

    result = apply_mapping({"created_at": 0}, mapping)

    assert result["created_at"] == "1970-01-01T00:00:00+00:00"


def test_invalid_decimal_coercion_fails_loudly():
    import pytest
    from decimal import InvalidOperation
    from graft.mapping import apply_mapping

    mapping = {
        "version": 2,
        "fields": {
            "amount": {
                "path": "$.amount",
                "transform": "to_decimal"
            }
        }
    }

    with pytest.raises(InvalidOperation):
        apply_mapping({"amount": "not-a-decimal"}, mapping)
