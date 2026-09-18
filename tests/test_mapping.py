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
