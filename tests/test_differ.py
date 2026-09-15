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
