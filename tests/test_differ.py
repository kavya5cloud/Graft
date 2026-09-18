from graft.differ import diff

def schema(paths): return {"paths": paths}
def p(types, vals, rate=1.0, nullable=False): return {"types":types,"value_fingerprint":vals,"presence_rate":rate,"nullable":nullable}

def test_identical_types_renamed_simultaneously():
    old=schema({"$.first_name":p(["string"],["A","B"]),"$.last_name":p(["string"],["X","Y"])})
    new=schema({"$.given_name":p(["string"],["A","B"]),"$.surname":p(["string"],["X","Y"])})
    rs=[x for x in diff(old,new)["changes"] if x["kind"]=="RENAMED"]
    assert {(x["old"],x["new"]) for x in rs}=={("$.first_name","$.given_name"),("$.last_name","$.surname")}
    assert all(x["confidence"]>=0.9 for x in rs)

def test_renamed_and_retyped_at_once():
    old=schema({"$.total":p(["string"],["42.5","10.0"])})
    new=schema({"$.grand_total":p(["number"],["42.5","10.0"])})
    rs=[x for x in diff(old,new)["changes"] if x["kind"]=="RENAMED"]
    assert rs and rs[0]["confidence"]>=0.9

def test_genuine_removal_not_forced():
    old=schema({"$.shipping":p(["string"],["Ahmedabad","Delhi"]),"$.total":p(["string"],["42.5"])})
    new=schema({"$.total":p(["string"],["42.5"])})
    assert {x["path"] for x in diff(old,new)["changes"] if x["kind"]=="REMOVED"}=={"$.shipping"}

def test_name_only_is_not_enough():
    old=schema({"$.foo":p(["string"],["A","B"])})
    new=schema({"$.foobar":p(["string"],["X","Y"])})
    assert not any(x["kind"]=="RENAMED" for x in diff(old,new)["changes"])


def test_rename_plus_retype():
    old = {
        "paths": {
            "$.total": {
                "types": ["string"],
                "nullable": False,
                "presence_rate": 1.0,
                "value_fingerprint": ["amount-42.50"],
            }
        }
    }
    new = {
        "paths": {
            "$.grand_total": {
                "types": ["number"],
                "nullable": False,
                "presence_rate": 1.0,
                "value_fingerprint": ["amount-42.50"],
            }
        }
    }

    result = diff(old, new)

    assert result["changes"][0]["kind"] == "RENAMED"
    assert result["changes"][0]["old"] == "$.total"
    assert result["changes"][0]["new"] == "$.grand_total"
    assert result["changes"][0]["confidence"] >= 0.9


def test_simultaneous_identical_type_renames():
    old = {
        "paths": {
            "$.first_name": {
                "types": ["string"],
                "nullable": False,
                "presence_rate": 1.0,
                "value_fingerprint": ["alice"],
            },
            "$.last_name": {
                "types": ["string"],
                "nullable": False,
                "presence_rate": 1.0,
                "value_fingerprint": ["smith"],
            },
        }
    }
    new = {
        "paths": {
            "$.given_name": {
                "types": ["string"],
                "nullable": False,
                "presence_rate": 1.0,
                "value_fingerprint": ["alice"],
            },
            "$.surname": {
                "types": ["string"],
                "nullable": False,
                "presence_rate": 1.0,
                "value_fingerprint": ["smith"],
            },
        }
    }

    result = diff(old, new)

    renames = {
        (c["old"], c["new"])
        for c in result["changes"]
        if c["kind"] == "RENAMED"
    }

    assert renames == {
        ("$.first_name", "$.given_name"),
        ("$.last_name", "$.surname"),
    }


def test_genuine_removal():
    old = {
        "paths": {
            "$.total": {
                "types": ["string"],
                "nullable": False,
                "presence_rate": 1.0,
                "value_fingerprint": ["amount-42.50"],
            }
        }
    }
    new = {"paths": {}}

    result = diff(old, new)

    assert result["changes"] == [
        {"kind": "REMOVED", "path": "$.total"}
    ]


def test_genuine_removal():
    old = {
        "paths": {
            "$.total": {
                "types": ["string"],
                "nullable": False,
                "presence_rate": 1.0,
                "value_fingerprint": ["amount-42.50"],
            }
        }
    }
    new = {"paths": {}}

    result = diff(old, new)

    assert result["changes"] == [
        {"kind": "REMOVED", "path": "$.total"}
    ]


def test_nested_rename():
    old = {
        "paths": {
            "$.customer.email": {
                "types": ["string"],
                "nullable": False,
                "presence_rate": 1.0,
                "value_fingerprint": ["a@example.com"],
            }
        }
    }
    new = {
        "paths": {
            "$.customer.contact_email": {
                "types": ["string"],
                "nullable": False,
                "presence_rate": 1.0,
                "value_fingerprint": ["a@example.com"],
            }
        }
    }

    result = diff(old, new)

    rename = next(c for c in result["changes"] if c["kind"] == "RENAMED")

    assert rename["old"] == "$.customer.email"
    assert rename["new"] == "$.customer.contact_email"
    assert rename["confidence"] >= 0.9


def test_array_field_rename():
    old = {
        "paths": {
            "$.line_items[*].amount": {
                "types": ["string"],
                "nullable": False,
                "presence_rate": 1.0,
                "value_fingerprint": ["20.00", "22.50"],
            }
        }
    }
    new = {
        "paths": {
            "$.line_items[*].price": {
                "types": ["string"],
                "nullable": False,
                "presence_rate": 1.0,
                "value_fingerprint": ["20.00", "22.50"],
            }
        }
    }

    result = diff(old, new)

    rename = next(c for c in result["changes"] if c["kind"] == "RENAMED")

    assert rename["old"] == "$.line_items[*].amount"
    assert rename["new"] == "$.line_items[*].price"
    assert rename["confidence"] >= 0.9


def test_false_positive_same_type_unrelated_values():
    old = {
        "paths": {
            "$.total": {
                "types": ["string"],
                "nullable": False,
                "presence_rate": 1.0,
                "value_fingerprint": ["amount-42.50"],
            }
        }
    }
    new = {
        "paths": {
            "$.customer_name": {
                "types": ["string"],
                "nullable": False,
                "presence_rate": 1.0,
                "value_fingerprint": ["alice"],
            }
        }
    }

    result = diff(old, new)

    assert all(c["kind"] != "RENAMED" for c in result["changes"])
    assert {"kind": "REMOVED", "path": "$.total"} in result["changes"]
    assert {"kind": "ADDED", "path": "$.customer_name"} in result["changes"]


def test_healer_applies_high_confidence_rename():
    from graft.healer import propose

    old_mapping = {
        "version": 1,
        "fields": {
            "total": {
                "path": "$.total",
                "transform": "identity"
            }
        }
    }

    old_schema = {
        "paths": {
            "$.total": {
                "types": ["string"],
                "nullable": False,
                "presence_rate": 1.0,
                "value_fingerprint": ["amount-42.50"]
            }
        }
    }

    new_schema = {
        "paths": {
            "$.grand_total": {
                "types": ["string"],
                "nullable": False,
                "presence_rate": 1.0,
                "value_fingerprint": ["amount-42.50"]
            }
        }
    }

    diff_result = {
        "changes": [{
            "kind": "RENAMED",
            "old": "$.total",
            "new": "$.grand_total",
            "confidence": 0.99
        }]
    }

    candidate = propose(
        old_mapping,
        diff_result,
        old_schema,
        new_schema
    )

    assert candidate["version"] == 2
    assert candidate["fields"]["total"]["path"] == "$.grand_total"
    assert candidate["fields"]["total"]["transform"] == "identity"


def test_low_confidence_rename_is_not_proposed():
    from graft.healer import propose

    old_mapping = {
        "version": 1,
        "fields": {
            "total": {
                "path": "$.total",
                "transform": "identity"
            }
        }
    }

    old_schema = {
        "paths": {
            "$.total": {
                "types": ["string"],
                "nullable": False,
                "presence_rate": 1.0,
                "value_fingerprint": ["amount-42.50"]
            }
        }
    }

    new_schema = {
        "paths": {
            "$.unrelated": {
                "types": ["string"],
                "nullable": False,
                "presence_rate": 1.0,
                "value_fingerprint": ["completely-different"]
            }
        }
    }

    diff_result = {
        "changes": [
            {
                "kind": "REMOVED",
                "path": "$.total"
            },
            {
                "kind": "ADDED",
                "path": "$.unrelated"
            }
        ]
    }

    candidate = propose(
        old_mapping,
        diff_result,
        old_schema,
        new_schema
    )

    assert candidate["fields"]["total"]["path"] == "$.total"
