# Graft

### Deterministic, self-healing API integrations — without LLMs.

Graft is an API integration layer that detects provider schema drift, infers what changed, generates a constrained mapping repair, validates the repair against real fixtures and business invariants, and supports versioned rollback.

**No LLM calls. No generated executable code. No opaque repair logic.**

Adapters are declarative JSON mappings interpreted by a fixed engine.

---

## Why Graft?

Third-party APIs change.

A provider might silently:

```text
total → grand_total
```

or change:

```text
"42.50" → 42.50
```

or remove, add, nest, or restructure fields.

Traditional integrations usually fail at runtime and require a developer to manually investigate and patch the adapter.

Graft turns that failure into a deterministic pipeline:

```text
Provider Response
       │
       ▼
   Recorder
       │
       ▼
 Schema Inference
       │
       ▼
  Drift Detector
       │
       ▼
 Rename / Retype / Add / Remove
       │
       ▼
 Deterministic Healer
       │
       ▼
   Candidate Mapping
       │
       ▼
     Validator
       │
       ├── ❌ Reject
       │
       ▼
     Apply v2
       │
       ▼
   Current Adapter
       │
       ▼
   Rollback → v1
```

---

## Core principles

### 1. Deterministic by design

Graft does not ask an LLM to decide whether a field changed.

Schema comparison, similarity scoring, mapping generation, validation, deployment, and rollback are all implemented as deterministic operations.

### 2. Adapters are data, not code

An adapter is a JSON document:

```json
{
  "version": 3,
  "fields": {
    "total": {
      "path": "$.amount",
      "transform": "to_decimal"
    }
  }
}
```

The engine interprets the mapping.

A repair therefore changes configuration rather than generating and executing new program logic.

### 3. Evidence-based repair

Graft compares structural and behavioral evidence including:

* JSON paths
* field types
* nullability
* presence rate
* value fingerprints
* structural parent
* field-name similarity

Rename candidates are scored deterministically and assigned a confidence score.

### 4. Validation before activation

A proposed repair is not automatically trusted.

Graft can replay mappings against recorded fixtures and evaluate domain-level invariants such as:

```text
sum($.line_items[*].amount) == $.total
```

A candidate that violates validation is rejected.

### 5. Version everything

Mappings are immutable versions:

```text
v1 → v2 → v3 → ...
```

The active adapter is selected through a version pointer, making rollback straightforward.

---

# Architecture

```text
                    ┌─────────────────────┐
                    │   Provider API      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     Recorder        │
                    │ request/response    │
                    │      fixtures       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    Inferencer       │
                    │  structural schema  │
                    └──────────┬──────────┘
                               │
                 ┌─────────────▼─────────────┐
                 │         Differ            │
                 │                           │
                 │ ADDED / REMOVED /         │
                 │ RETYPED / RENAMED         │
                 └─────────────┬─────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │      Healer         │
                    │ constrained mapping │
                    │      proposal       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     Validator       │
                    │ fixtures + invariants│
                    └──────────┬──────────┘
                               │
                         ┌─────┴─────┐
                         │           │
                       reject      accept
                         │           │
                         │           ▼
                         │     ┌───────────┐
                         │     │ Apply vN  │
                         │     └─────┬─────┘
                         │           │
                         │           ▼
                         │     ┌───────────┐
                         └────►│ Rollback  │
                               └───────────┘
```

---

# Drift detection

Graft currently models four important categories of schema change:

| Change    | Example                     |
| --------- | --------------------------- |
| `ADDED`   | `$.currency` appears        |
| `REMOVED` | `$.total` disappears        |
| `RETYPED` | `"42.50"` → `42.50`         |
| `RENAMED` | `$.total` → `$.grand_total` |

## Rename matching

For a removed field and an added field, Graft calculates a deterministic similarity score.

Evidence includes:

1. **Value fingerprint similarity**
2. Type compatibility
3. Nullability
4. Presence rate
5. Field-name similarity
6. Structural parent

The highest-scoring valid pairs are selected using greedy one-to-one matching.

Confidence levels:

```text
≥ 0.90       Auto-proposable
0.60–0.90    Human review
< 0.60       Unmatched
```

Example:

```json
{
  "kind": "RENAMED",
  "old": "$.total",
  "new": "$.grand_total",
  "confidence": 0.98875
}
```

---

# Deterministic mapping engine

Mappings contain paths and fixed transforms.

Supported transforms include:

```text
identity
to_decimal
to_int
to_string
iso_datetime
unix_to_iso
default(...)
```

Unknown transforms are rejected.

Example:

```json
{
  "version": 2,
  "fields": {
    "order_id": {
      "path": "$.order_id",
      "transform": "identity"
    },
    "total": {
      "path": "$.grand_total",
      "transform": "identity"
    },
    "created_at": {
      "path": "$.created_at",
      "transform": "iso_datetime"
    }
  }
}
```

The provider can change its representation while the domain-facing contract remains stable.

---

# Validation

Validation is designed to answer:

> "Does this proposed adapter still produce the domain output we expect?"

Graft checks for things such as:

* candidate null outputs
* dropped domain keys
* mapping compatibility
* domain output consistency
* business invariants

Example invariant:

```text
sum($.line_items[*].amount) == $.total
```

This prevents a structurally plausible repair from silently producing an incorrect business result.

---

# Versioning and rollback

Every mapping is versioned.

Example:

```text
mappings/
└── orders/
    ├── v1.json
    ├── v2.json
    └── current.json
```

Applying a candidate creates/activates a new version.

If the new mapping causes problems:

```bash
python -m graft.cli rollback orders
```

Graft moves the active pointer back to the previous version.

---

# Quick start

## 1. Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Start the demo provider

```bash
python provider.py
```

The example provider exposes:

```text
/orders/1001
```

## 3. Record the baseline

```bash
python -m graft.cli record demo orders http://127.0.0.1:8000/orders/1001 --reset
```

## 4. Create a schema snapshot

```bash
python -m graft.cli snapshot demo orders
```

## 5. Simulate provider drift

In another terminal:

```bash
python provider.py --mutate rename
```

The provider changes:

```text
total → grand_total
```

## 6. Record the changed response

```bash
python -m graft.cli record demo orders http://127.0.0.1:8000/orders/1001
```

## 7. Detect the drift

```bash
python -m graft.cli check demo orders snapshots/demo/orders.json
```

Expected result:

```json
{
  "changes": [
    {
      "kind": "RENAMED",
      "old": "$.total",
      "new": "$.grand_total",
      "confidence": 0.98875
    }
  ]
}
```

## 8. Generate a repair

```bash
python -m graft.cli propose \
  snapshots/demo/orders.json \
  .graft/latest_schema.json \
  mappings/orders/v1.json \
  .graft/last_diff.json
```

The generated candidate updates:

```text
$.total
   ↓
$.grand_total
```

and creates mapping version `2`.

## 9. Validate the repair

```bash
python -m graft.cli validate \
  mappings/orders/v1.json \
  .graft/candidate.json \
  fixtures/demo/orders \
  --invariant 'sum($.line_items[*].amount) == $.total'
```

Expected:

```json
{
  "valid": true,
  "errors": []
}
```

## 10. Apply the repair

```bash
python -m graft.cli apply orders .graft/candidate.json
```

## 11. Roll back

```bash
python -m graft.cli rollback orders
```

---

# CLI

| Command    | Purpose                                    |
| ---------- | ------------------------------------------ |
| `record`   | Capture provider request/response fixtures |
| `snapshot` | Infer and store a baseline schema          |
| `check`    | Detect schema drift                        |
| `propose`  | Generate a deterministic mapping candidate |
| `validate` | Replay and validate the candidate          |
| `apply`    | Activate a mapping version                 |
| `rollback` | Restore the previous mapping version       |

---

# Project structure

```text
graft/
├── graft/
│   ├── cli.py
│   ├── differ.py
│   ├── healer.py
│   ├── inferencer.py
│   ├── mapping.py
│   ├── recorder.py
│   └── validator.py
│
├── mappings/
│   └── orders/
│       ├── v1.json
│       ├── v2.json
│       └── current.json
│
├── tests/
│   ├── test_differ.py
│   ├── test_inferencer.py
│   ├── test_mapping.py
│   └── test_validator.py
│
├── provider.py
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

# Testing

Run:

```bash
pytest -q
```

Current MVP test suite:

```text
9 passed
```

The test suite covers schema inference, mapping behavior, drift detection, rename matching, and validation.

---

# Design goals

Graft is intentionally conservative.

It is designed around the principle:

> **A repair should be explainable, constrained, testable, and reversible.**

The system does not attempt to understand arbitrary API semantics or automatically rewrite application code.

Instead, it focuses on a narrower problem:

**Detect known classes of API contract drift and safely repair declarative mappings when the available evidence is strong enough.**

---

# Roadmap

Potential next steps:

* [ ] More robust multi-field rename matching
* [ ] Rename + retype handling
* [ ] Nested object restructuring
* [ ] Array schema evolution
* [ ] Better fixture/baseline lifecycle management
* [ ] Expanded invariant language
* [ ] Shadow validation against live traffic
* [ ] Approval workflow for medium-confidence repairs
* [ ] Adapter audit history
* [ ] Provider/endpoint registry
* [ ] Production HTTP middleware
* [ ] More comprehensive adversarial tests

---

# Philosophy

Graft is built around a simple idea:

**API integrations should fail safely and repair predictably.**

When a provider changes, the system should be able to answer:

```text
What changed?
Why do we believe it changed?
What mapping would repair it?
Does the repair preserve the domain contract?
Can we undo it?
```

If those questions cannot be answered deterministically, Graft should **stop rather than guess**.

---

## License

Add your preferred open-source license before publishing a stable release.
