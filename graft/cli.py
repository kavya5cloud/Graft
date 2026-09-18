import argparse, json, os, shutil, tempfile
from pathlib import Path
from .recorder import record_pair
from .inferencer import infer, load_fixtures
from .differ import diff
from .healer import propose
from .validator import validate
from .audit import record_audit
from .provider import get_provider
from .registry import register_contract

ROOT=Path.cwd(); STATE=ROOT/".graft"
def read_json(p): return json.loads(Path(p).read_text())
def write_json(p,x): Path(p).parent.mkdir(parents=True,exist_ok=True); Path(p).write_text(json.dumps(x,indent=2,sort_keys=True))

def cmd_record(a):
    if a.reset:
        shutil.rmtree(ROOT/"fixtures"/a.provider/a.endpoint, ignore_errors=True)

    try:
        provider = get_provider(a.transport)
    except ValueError as exc:
        raise SystemExit(str(exc))

    response = provider.fetch(a.url)
    print(record_pair(
        ROOT,
        a.provider,
        a.endpoint,
        {"method": "GET", "url": a.url},
        response,
    ))

def cmd_snapshot(a):
    schema_path = ROOT / "snapshots" / a.provider / f"{a.endpoint}.json"

    fixture_dir = ROOT / "fixtures" / a.provider / a.endpoint
    fixtures = sorted(
        fixture_dir.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
    )

    if not fixtures:
        raise SystemExit("no fixtures found")

    write_json(
        schema_path,
        infer([read_json(fixtures[-1])]),
    )

    register_contract(
        ROOT,
        a.provider,
        a.endpoint,
        schema_path.relative_to(ROOT),
    )

    print("snapshot written")

def cmd_check(a):
    if a.old:
        old_path = Path(a.old)
    else:
        registry_path = STATE / "contracts.json"

        if not registry_path.exists():
            raise SystemExit(
                f"no registered contract for {a.provider}/{a.endpoint}"
            )

        registry = read_json(registry_path)
        key = f"{a.provider}/{a.endpoint}"
        contract = registry.get(key)

        if not contract:
            raise SystemExit(
                f"no registered contract for {a.provider}/{a.endpoint}"
            )

        old_path = Path(contract["schema"])

        if not old_path.is_absolute():
            old_path = ROOT / old_path

    old=read_json(old_path)

    fixture_dir=ROOT/"fixtures"/a.provider/a.endpoint
    fixtures=sorted(fixture_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)

    if not fixtures:
        raise SystemExit("no fixtures found")

    # Check only the latest observation against the stored baseline.
    new=infer([read_json(fixtures[-1])])

    d=diff(old,new)
    write_json(STATE/"last_diff.json",d)
    write_json(STATE/"latest_schema.json",new)
    print(json.dumps(d,indent=2))

def cmd_propose(a):
    c=propose(read_json(a.mapping),read_json(a.diff),read_json(a.old_schema),read_json(a.new_schema)); write_json(STATE/"candidate.json",c); print(json.dumps(c,indent=2))

def cmd_validate(a):
    fixture_dir = Path(a.fixtures)
    fixtures = sorted(fixture_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)

    if not fixtures:
        raise SystemExit("no fixtures found")

    # Validate the candidate against the latest provider observation.
    latest_fixture = read_json(fixtures[-1])

    r = validate(
        read_json(a.old),
        read_json(a.candidate),
        [latest_fixture],
        a.invariant or [],
    )

    print(json.dumps(r, indent=2))
    raise SystemExit(0 if r["valid"] else 1)

def cmd_apply(a):
    src = Path(a.mapping)
    provider_dir = ROOT / "mappings" / a.provider
    provider_dir.mkdir(parents=True, exist_ok=True)

    version = read_json(src)["version"]
    dst = provider_dir / f"v{version}.json"
    current = provider_dir / "current.json"

    shutil.copyfile(src, dst)

    fd, temp_name = tempfile.mkstemp(
        dir=provider_dir,
        prefix=".current-",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(src.read_bytes())
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(temp_name, current)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise

    record_audit(
        ROOT,
        "apply",
        a.provider,
        version=version,
        mapping=str(dst),
    )
    print(dst)

def cmd_audit(a):
    path = STATE / "audit.jsonl"

    if not path.exists():
        print("no audit events")
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            print(json.dumps(json.loads(line), indent=2, sort_keys=True))


def cmd_rollback(a):
    d = ROOT / "mappings" / a.provider
    current = d / "current.json"

    if not current.exists():
        raise SystemExit("no current mapping")

    active_version = read_json(current)["version"]
    versions = sorted(
        d.glob("v*.json"),
        key=lambda p: int(p.stem[1:]),
    )
    previous = [
        p for p in versions
        if int(p.stem[1:]) < active_version
    ]

    if not previous:
        raise SystemExit("no previous version")

    target = previous[-1]
    target_version = int(target.stem[1:])
    shutil.copyfile(target, current)

    record_audit(
        ROOT,
        "rollback",
        a.provider,
        from_version=active_version,
        to_version=target_version,
        mapping=str(target),
    )

    print(f"rolled back to {target.name}")

def main():
    p=argparse.ArgumentParser(prog="graft"); s=p.add_subparsers(dest="cmd",required=True)
    r=s.add_parser("record"); r.add_argument("provider"); r.add_argument("endpoint"); r.add_argument("url"); r.add_argument("--reset",action="store_true"); r.add_argument("--transport",default="http"); r.set_defaults(fn=cmd_record)
    r=s.add_parser("snapshot"); r.add_argument("provider"); r.add_argument("endpoint"); r.set_defaults(fn=cmd_snapshot)
    r=s.add_parser("check"); r.add_argument("provider"); r.add_argument("endpoint"); r.add_argument("old", nargs="?"); r.set_defaults(fn=cmd_check)
    r=s.add_parser("propose"); r.add_argument("old_schema"); r.add_argument("new_schema"); r.add_argument("mapping"); r.add_argument("diff"); r.set_defaults(fn=cmd_propose)
    r=s.add_parser("validate"); r.add_argument("old"); r.add_argument("candidate"); r.add_argument("fixtures"); r.add_argument("--invariant",action="append"); r.set_defaults(fn=cmd_validate)
    r=s.add_parser("apply"); r.add_argument("provider"); r.add_argument("mapping"); r.set_defaults(fn=cmd_apply)
    r=s.add_parser("rollback"); r.add_argument("provider"); r.set_defaults(fn=cmd_rollback)
    r=s.add_parser("audit"); r.set_defaults(fn=cmd_audit)
    a=p.parse_args(); a.fn(a)
if __name__=="__main__": main()
