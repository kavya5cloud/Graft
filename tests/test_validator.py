from graft.validator import check_invariant

def test_sum_invariant():
    body={"line_items":[{"amount":"20.00"},{"amount":"22.50"}],"total":"42.50"}
    assert check_invariant("sum($.line_items[*].amount) == $.total", body, {})
