from graft.inferencer import infer

def f(body): return {"body":body}

def test_nested_schema_and_presence():
    s=infer([f({"a":{"b":1},"items":[{"price":"2.00"}]}),f({"a":{"b":2},"items":[]})])
    assert s["paths"]["$.a.b"]["types"]==["integer"]
    assert s["paths"]["$.a.b"]["presence_rate"]==1.0
    assert "$.items[*].price" in s["paths"]

def test_fingerprint_numeric_string_overlap():
    a=infer([f({"x":"42.5"})]); b=infer([f({"y":42.5})])
    assert set(a["paths"]["$.x"]["value_fingerprint"]) & set(b["paths"]["$.y"]["value_fingerprint"])


def test_infer_mixed_types_records_all_types():
    from graft.inferencer import infer

    fixtures = [
        {
            "body": {
                "amount": 10,
            }
        },
        {
            "body": {
                "amount": "20",
            }
        },
        {
            "body": {
                "amount": 30.5,
            }
        },
    ]

    schema = infer(fixtures)

    assert set(schema["paths"]["$.amount"]["types"]) == {
        "integer",
        "string",
        "number",
    }


def test_infer_nullable_field_preserves_concrete_type():
    from graft.inferencer import infer

    fixtures = [
        {"body": {"status": "active"}},
        {"body": {"status": None}},
        {"body": {"status": "inactive"}},
    ]

    schema = infer(fixtures)

    field = schema["paths"]["$.status"]

    assert field["types"] == ["null", "string"]
    assert field["nullable"] is True
    assert field["presence_rate"] == 1.0


def test_infer_missing_field_tracks_presence_rate():
    from graft.inferencer import infer

    fixtures = [
        {"body": {"status": "active"}},
        {"body": {}},
        {"body": {"status": "inactive"}},
        {"body": {}},
    ]

    schema = infer(fixtures)

    field = schema["paths"]["$.status"]

    assert field["types"] == ["string"]
    assert field["nullable"] is False
    assert field["presence_rate"] == 0.5


def test_infer_empty_array_records_array_path():
    from graft.inferencer import infer

    fixtures = [
        {"body": {"items": []}},
        {"body": {"items": []}},
    ]

    schema = infer(fixtures)

    assert schema["paths"]["$.items"]["types"] == ["array"]
    assert "$.items[*]" in schema["paths"]
    assert schema["paths"]["$.items[*]"]["types"] == []


def test_infer_nested_object_paths():
    from graft.inferencer import infer

    fixtures = [
        {
            "body": {
                "customer": {
                    "id": 101,
                    "name": "Alice"
                }
            }
        }
    ]

    schema = infer(fixtures)

    assert schema["paths"]["$.customer"]["types"] == ["object"]
    assert schema["paths"]["$.customer.id"]["types"] == ["integer"]
    assert schema["paths"]["$.customer.name"]["types"] == ["string"]


def test_infer_nested_array_objects_with_missing_field():
    from graft.inferencer import infer

    fixtures = [
        {
            "body": {
                "orders": [
                    {"id": 101, "total": 10.5},
                    {"id": 102},
                ]
            }
        }
    ]

    schema = infer(fixtures)

    assert schema["paths"]["$.orders"]["types"] == ["array"]
    assert schema["paths"]["$.orders[*].id"]["types"] == ["integer"]
    assert schema["paths"]["$.orders[*].total"]["types"] == ["number"]
    assert schema["paths"]["$.orders[*].total"]["presence_rate"] == 0.5


def test_infer_array_field_presence_across_multiple_fixtures():
    from graft.inferencer import infer

    fixtures = [
        {
            "body": {
                "orders": [
                    {"id": 1, "total": 10},
                    {"id": 2},
                ]
            }
        },
        {
            "body": {
                "orders": [
                    {"id": 3, "total": 30},
                    {"id": 4, "total": 40},
                ]
            }
        },
    ]

    schema = infer(fixtures)

    field = schema["paths"]["$.orders[*].total"]

    assert field["types"] == ["integer"]
    assert field["presence_rate"] == 0.75


def test_infer_nested_wildcard_presence_rate():
    from graft.inferencer import infer

    fixtures = [
        {
            "body": {
                "orders": [
                    {"customer": {"email": "a@example.com"}},
                    {"customer": {}},
                ]
            }
        },
        {
            "body": {
                "orders": [
                    {"customer": {"email": "b@example.com"}},
                    {"customer": {"email": "c@example.com"}},
                ]
            }
        },
    ]

    schema = infer(fixtures)

    field = schema["paths"]["$.orders[*].customer.email"]

    assert field["types"] == ["string"]
    assert field["presence_rate"] == 0.75


def test_infer_caps_value_fingerprints():
    from graft.inferencer import infer

    fixtures = [
        {"body": {"value": f"value-{i}"}}
        for i in range(1100)
    ]

    schema = infer(fixtures)

    fingerprints = schema["paths"]["$.value"]["value_fingerprint"]

    assert len(fingerprints) == 1000


def test_infer_fingerprints_are_order_independent():
    from graft.inferencer import infer

    first = infer([
        {"body": {"value": "alpha"}},
        {"body": {"value": "beta"}},
        {"body": {"value": "gamma"}},
    ])

    second = infer([
        {"body": {"value": "gamma"}},
        {"body": {"value": "alpha"}},
        {"body": {"value": "beta"}},
    ])

    assert first["paths"]["$.value"]["value_fingerprint"] == \
        second["paths"]["$.value"]["value_fingerprint"]


def test_infer_schema_has_valid_version():
    from graft.inferencer import infer

    schema = infer([
        {"body": {"id": 1}}
    ])

    assert isinstance(schema["version"], int)
    assert schema["version"] == 1


def test_infer_empty_input_returns_valid_schema():
    from graft.inferencer import infer

    schema = infer([])

    assert schema["version"] == 1
    assert schema["fixture_count"] == 0
    assert schema["paths"] == {}


def test_infer_null_body_records_root_as_nullable():
    from graft.inferencer import infer

    schema = infer([
        {"body": None}
    ])

    root = schema["paths"]["$"]

    assert root["types"] == ["null"]
    assert root["nullable"] is True
    assert root["presence_rate"] == 1.0


def test_infer_boolean_is_not_integer():
    from graft.inferencer import infer

    schema = infer([
        {"body": {"active": True}},
        {"body": {"active": False}},
    ])

    field = schema["paths"]["$.active"]

    assert field["types"] == ["boolean"]
    assert field["nullable"] is False


def test_infer_boolean_is_not_integer():
    from graft.inferencer import infer

    schema = infer([
        {"body": {"active": True}},
        {"body": {"active": False}},
    ])

    field = schema["paths"]["$.active"]

    assert field["types"] == ["boolean"]
    assert field["nullable"] is False


def test_infer_array_type_is_preserved():
    from graft.inferencer import infer

    schema = infer([
        {"body": {"items": [1, 2, 3]}}
    ])

    assert schema["paths"]["$.items"]["types"] == ["array"]
    assert schema["paths"]["$.items[*]"]["types"] == ["integer"]


def test_infer_mixed_array_element_types():
    from graft.inferencer import infer

    schema = infer([
        {
            "body": {
                "items": [1, "two", 3.5, True, None]
            }
        }
    ])

    field = schema["paths"]["$.items[*]"]

    assert field["types"] == [
        "boolean",
        "integer",
        "null",
        "number",
        "string",
    ]
    assert field["nullable"] is True


def test_infer_nested_mixed_array_elements():
    from graft.inferencer import infer

    schema = infer([
        {
            "body": {
                "groups": [
                    {"values": [1, 2]},
                    {"values": ["three", "four"]},
                ]
            }
        }
    ])

    field = schema["paths"]["$.groups[*].values[*]"]

    assert field["types"] == ["integer", "string"]
    assert field["nullable"] is False


def test_infer_field_changing_between_object_and_array():
    from graft.inferencer import infer

    schema = infer([
        {"body": {"data": {"id": 1}}},
        {"body": {"data": [{"id": 2}]}},
    ])

    field = schema["paths"]["$.data"]

    assert field["types"] == ["array", "object"]


def test_infer_empty_object_records_object_without_children():
    from graft.inferencer import infer

    schema = infer([
        {"body": {"metadata": {}}}
    ])

    assert schema["paths"]["$.metadata"]["types"] == ["object"]
    assert "$.metadata" in schema["paths"]
    assert "$.metadata[*]" not in schema["paths"]


def test_infer_deeply_nested_object_paths():
    from graft.inferencer import infer

    schema = infer([
        {
            "body": {
                "account": {
                    "profile": {
                        "contact": {
                            "email": "user@example.com"
                        }
                    }
                }
            }
        }
    ])

    assert schema["paths"]["$.account"]["types"] == ["object"]
    assert schema["paths"]["$.account.profile"]["types"] == ["object"]
    assert schema["paths"]["$.account.profile.contact"]["types"] == ["object"]
    assert schema["paths"]["$.account.profile.contact.email"]["types"] == ["string"]


def test_infer_special_json_keys():
    from graft.inferencer import infer

    schema = infer([
        {
            "body": {
                "user-id": 101,
                "first_name": "Kavya",
                "display name": "Kavya Shree",
            }
        }
    ])

    assert schema["paths"]["$.user-id"]["types"] == ["integer"]
    assert schema["paths"]["$.first_name"]["types"] == ["string"]
    assert schema["paths"]["$.display name"]["types"] == ["string"]


def test_infer_unicode_json_keys_and_values():
    from graft.inferencer import infer

    schema = infer([
        {
            "body": {
                "नाम": "काव्या",
                "શહેર": "અમદાવાદ",
                "status": "सक्रिय",
            }
        }
    ])

    assert schema["paths"]["$.नाम"]["types"] == ["string"]
    assert schema["paths"]["$.શહેર"]["types"] == ["string"]
    assert schema["paths"]["$.status"]["types"] == ["string"]


def test_unicode_value_fingerprints_are_deterministic():
    from graft.inferencer import infer

    values = ["કાવ્યા", "काव्या", "અમદાવાદ", "東京"]

    first = infer([
        {"body": {"value": value}}
        for value in values
    ])

    second = infer([
        {"body": {"value": value}}
        for value in reversed(values)
    ])

    first_fp = first["paths"]["$.value"]["value_fingerprint"]
    second_fp = second["paths"]["$.value"]["value_fingerprint"]

    assert first_fp == second_fp
    assert len(first_fp) == len(values)
    assert len(set(first_fp)) == len(values)
