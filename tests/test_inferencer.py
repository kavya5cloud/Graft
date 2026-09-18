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
