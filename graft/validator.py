from decimal import Decimal
import re
from .mapping import apply_mapping

SUM_PATH_RE = re.compile(r"^sum\(\$\.([A-Za-z_][\w]*)\[\*\]\.([A-Za-z_][\w]*)\)$")


def _numeric(v):
    if isinstance(v, list): return sum((_numeric(x) for x in v), Decimal(0))
    if isinstance(v, (int,float,Decimal)): return Decimal(str(v))
    if isinstance(v, str): return Decimal(v)
    raise ValueError(f"not numeric: {v!r}")


def _resolve_expr(expr, body, domain):
    m = SUM_PATH_RE.fullmatch(expr)
    if m:
        arr = body.get(m.group(1), [])
        return sum((_numeric(x.get(m.group(2))) for x in arr), Decimal(0))
    if expr.startswith("$.domain."): return domain.get(expr[9:])
    if expr.startswith("$.") and expr[2:] in domain: return domain.get(expr[2:])
    if expr.startswith("$.line_items[*]."):
        key = expr.split(".")[-1]
        return [x.get(key) for x in body.get("line_items", [])]
    if expr.startswith("$." ):
        cur = body
        for token in expr[2:].split("."):
            if not isinstance(cur, dict): return None
            cur = cur.get(token)
        return cur
    try: return Decimal(expr)
    except Exception: return expr.strip('"\'')


def check_invariant(expr, body, domain):
    if "==" not in expr: raise ValueError("Invariant must contain ==")
    left, right = (x.strip() for x in expr.split("==",1))
    a, b = _resolve_expr(left, body, domain), _resolve_expr(right, body, domain)
    try: return _numeric(a) == _numeric(b)
    except (ValueError, TypeError, ArithmeticError): return a == b


def validate(old_mapping, candidate_mapping, fixtures, invariants=None):
    errors = []
    old_outputs = []
    new_outputs = []

    for i, fixture in enumerate(fixtures):
        body = fixture.get("body")

        old_out = apply_mapping(body, old_mapping)
        new_out = apply_mapping(body, candidate_mapping)

        old_outputs.append(old_out)
        new_outputs.append(new_out)

        # Candidate must fully populate the domain output.
        if any(v is None for v in new_out.values()):
            errors.append(f"fixture {i}: candidate produced null")

        if set(new_out) != set(old_out):
            errors.append(f"fixture {i}: dropped keys")

        for inv in invariants or []:
            if not check_invariant(inv, body, new_out):
                errors.append(f"fixture {i}: invariant failed: {inv}")

    return {
        "valid": not errors,
        "errors": errors,
        "old_outputs": old_outputs,
        "new_outputs": new_outputs,
    }
