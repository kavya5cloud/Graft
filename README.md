# Graft

Deterministic API drift detection and self-healing adapter layer. No LLM calls.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Tests

```bash
pytest -q
```

## Stub provider

```bash
python provider.py
python provider.py --mutate rename
```

Supported mutations: `rename`, `retype`, `drop`, `nest`.

## Design

Adapters are JSON data interpreted by a fixed engine. A repair changes only a mapping document; versions can be switched without changing executable code.

The CLI stages are independently usable: `record`, `snapshot`, `check`, `propose`, `validate`, `apply`, `rollback`.
