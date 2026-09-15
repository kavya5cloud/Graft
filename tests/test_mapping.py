import pytest
from graft.mapping import apply_mapping, validate_mapping

def test_nested_array_path():
    body={"line_items":[{"price":"20.00"},{"price":"22.50"}]}
    assert apply_mapping(body,{"version":1,"fields":{"prices":{"path":"$.line_items[*].price"}}})=={"prices":["20.00","22.50"]}

def test_unknown_transform_rejected():
    with pytest.raises(ValueError): validate_mapping({"version":1,"fields":{"x":{"path":"$.x","transform":"shell"}}})
