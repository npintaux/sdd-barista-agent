# Code layout convention — Barista Agent

> **Why this file exists.** `/implement` carries the *method* (TDD, OO, docstrings).
> This file carries the *layout* — where code goes — so the structure is
> **deterministic** rather than improvised on each run. `/implement` MUST read this
> before creating files. Its machine-readable twin, [`code-layout.env`](code-layout.env) (same
> directory), declares the same paths/patterns as `key=value` so the hooks can enforce
> them — keep the two in sync. The `post-implement` hook imposes the load-bearing parts.

## Repository layout

```
sdd-barista-agent/
├── SPEC.md                  # the contract /implement obeys — ROOT, load-bearing (hooks grep it here)
├── pyproject.toml           # package metadata + semantic version (NFR7)
├── AGENTS.md                # thin router → SPEC.md, this convention, the skills
├── .agents/
│  └── conventions/
│     ├── code-layout.md          # this file (prose, for the agent)
│     └── code-layout.env         # the same invariants as key=value (for the hooks)
├── docs/
│  └── PRD.md                # Product Owner artifact — REFERENCE only, not the dev's contract
├── src/
│  └── barista/              # the importable package (= the built wheel)
│     ├── __init__.py
│     ├── core/              # PURE decision engine — deterministic, NO I/O (US1 → US3)
│     │  ├── __init__.py
│     │  ├── models.py       #   Request/Order, Decision  (frozen dataclasses)
│     │  ├── menu.py         #   Menu reference data
│     │  ├── engine.py       #   take_order(...) entry point + ordered rule list
│     │  └── rules/
│     │     ├── __init__.py
│     │     ├── base.py      #   Rule (typing.Protocol)
│     │     ├── r1_make.py   #   one rule class per file, named r<n>_<slug>.py
│     │     ├── r2_ask.py
│     │     └── r3_refuse.py
│     └── agent/             # ADK agent shell — I/O, menu tool, preview (US4, later)
│        └── __init__.py
└── tests/                   # mirrors src/barista/core; one test file per rule
   ├── test_r1_make.py
   ├── test_r2_ask.py
   └── test_r3_refuse.py
```

## The core / agent seam (load-bearing)

The package splits in two on purpose — this *is* the PRD's portability promise (NFR10):

- **`core/`** — the pure decision engine. Deterministic, no I/O, no network, no model
  calls. Same `Request` + same `Menu` → same `Decision` (NFR1). This is what
  `/implement` builds and tests in TDD for US1 → US3. It re-skins to other
  counter-service domains (pharmacy, ticket desk) **unchanged**.
- **`agent/`** — the ADK shell around the core: the menu tool, model calls, the
  optional preview image (US4). All I/O lives here. Kept empty until a story needs it.

**Never import `agent` from `core`.** The dependency points one way: `agent → core`.

## Rules — the unit of the engine

A *rule* is one declarative decision unit with a **stable ID** (`R1`, `R2`, …; never
reused or renumbered — see `SPEC.md`). Each rule answers: *given this `Request` and
`Menu`, do I apply, and if so what `outcome` and `rule_ids` do I produce?*

- **One rule class per file**, named `r<n>_<slug>.py` (e.g. `r2_ask.py`), under
  `src/barista/core/rules/`.
- Each rule implements the `Rule` Protocol in `base.py`, e.g.
  `evaluate(request, menu) -> Decision | None` (`None` = "I don't apply").
- The **engine** (`engine.py`) holds the rules in an **ordered list**; precedence =
  list order; the first rule returning a non-`None` `Decision` wins. The last rule is
  the catch-all (`R3`) guaranteeing totality.
- This ordered-list-of-rules design is what makes the engine auditable
  (`rule_ids` → file → commit `[Rn]` → issue → PRD) and declarative (add a policy =
  add a file, NFR8).

## Tests

- Live in `tests/` at the repo root, **mirroring** the rule files: `test_r<n>_<slug>.py`.
- One test file per rule; each test traces to an acceptance criterion in `SPEC.md`,
  not to the implementation.
- Assert the `outcome` **and** the `rule_ids`.

## Packaging

- `pyproject.toml` declares the `barista` package (`src/` layout) and a **semantic
  version**; a contract change is signalled by a version bump (NFR7).
- Python 3.13, full type hints, complete docstrings (enforced by `pylint`).

## What a hook enforces (deterministic, not just advised)

- `SPEC.md` stays at the repo **root**.
- New rule files live under `src/barista/core/rules/` as `r<n>_<slug>.py` and have a
  matching `tests/test_r<n>_<slug>.py`.
- `core/` imports nothing from `agent/`.

Everything else here is convention the agent follows; the hook checks the parts that
must never drift.
