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


def test_valid_decimal_coercion_is_deterministic():
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

    result = apply_mapping({"amount": "42.50"}, mapping)

    assert result["amount"] == "42.50"


def test_transforms_preserve_null_values():
    from graft.mapping import apply_mapping

    transforms = [
        "identity",
        "to_decimal",
        "to_int",
        "to_string",
        "iso_datetime",
        "unix_to_iso",
    ]

    for transform in transforms:
        mapping = {
            "version": 2,
            "fields": {
                "value": {
                    "path": "$.value",
                    "transform": transform
                }
            }
        }

        result = apply_mapping({"value": None}, mapping)

        assert result["value"] is None


def test_missing_array_path_returns_empty_list():
    from graft.mapping import apply_mapping

    mapping = {
        "version": 2,
        "fields": {
            "amounts": {
                "path": "$.items[*].amount",
                "transform": "identity"
            }
        }
    }

    result = apply_mapping({}, mapping)

    assert result["amounts"] == []


def test_empty_array_path_returns_empty_list():
    from graft.mapping import apply_mapping

    mapping = {
        "version": 2,
        "fields": {
            "amounts": {
                "path": "$.items[*].amount",
                "transform": "identity"
            }
        }
    }

    result = apply_mapping({"items": []}, mapping)

    assert result["amounts"] == []


def test_mixed_array_elements_preserve_positions():
    from graft.mapping import apply_mapping

    mapping = {
        "version": 2,
        "fields": {
            "amounts": {
                "path": "$.items[*].amount",
                "transform": "identity"
            }
        }
    }

    body = {
        "items": [
            {"amount": 10},
            {},
            {"amount": 30}
        ]
    }

    result = apply_mapping(body, mapping)

    assert result["amounts"] == [10, None, 30]


def test_array_transform_applies_per_element():
    from graft.mapping import apply_mapping

    mapping = {
        "version": 2,
        "fields": {
            "amounts": {
                "path": "$.items[*].amount",
                "transform": "to_int"
            }
        }
    }

    body = {
        "items": [
            {"amount": "10"},
            {"amount": "20"},
            {"amount": "30"}
        ]
    }

    result = apply_mapping(body, mapping)

    assert result["amounts"] == [10, 20, 30]


def test_array_transform_preserves_null_elements():
    from graft.mapping import apply_mapping

    mapping = {
        "version": 2,
        "fields": {
            "amounts": {
                "path": "$.items[*].amount",
                "transform": "to_int"
            }
        }
    }

    body = {
        "items": [
            {"amount": "10"},
            {"amount": None},
            {"amount": "30"}
        ]
    }

    result = apply_mapping(body, mapping)

    assert result["amounts"] == [10, None, 30]
