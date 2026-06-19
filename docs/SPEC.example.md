<!--
  ILLUSTRATIVE EXAMPLE — the SPEC.md that `/specify` would scaffold from US1.
  Saved as SPEC.example.md (not SPEC.md) so it doesn't pre-empt the real spec
  that /specify creates on an issue branch during the demo.
  Issue number below (#1) is illustrative until the backlog is published.
-->

# Specification

> **Source of truth.** GitHub Issues are intake; this file is the contract the
> agent obeys. When the two disagree, this file (and its owners) decide.

## Overview

Given an `Order` (a requested drink and an optional size) and the current `Menu`,
the barista engine returns a `Decision` — an `outcome` (`MAKE`, `ASK`, or
`REFUSE`), the `rule_ids` that fired, a human-readable `reason`, and, for an
`ASK`, a single clarifying `question` — by evaluating the rules in precedence
order. Reference entry point: `take_order(order, menu)`.

## Domain model

- **Order** — the input. Fields:
  - `item: str` — the drink requested, as understood from the customer (e.g.
    `"latte"`, `"oat latte"`, `"drip"`).
  - `size: str | None` — the requested size if stated (e.g. `"small" | "medium"
    | "large"`), otherwise `None`.
- **Menu** — reference data the engine consults; **not** part of the `Order`. For
  each known drink:
  - `name: str` — the drink's canonical name.
  - `in_stock: bool` — whether it can currently be made.
  - `requires_size: bool` — whether a `size` must be supplied to make it.

  Lookup is by normalized `item` (see Global constraints); an `item` with no
  matching entry is **off-menu**.
- **Decision** — the output. Fields:
  - `outcome` — one of `MAKE | ASK | REFUSE`.
  - `rule_ids: list[str]` — the rule(s) that determined the outcome.
  - `reason: str` — a human-readable explanation of the decision.
  - `question: str | None` — a single clarifying question; set **only** when
    `outcome == ASK`, otherwise `None`.

## Global constraints

Invariants that hold across **all** rules and are not themselves rules:

- **Determinism** — the same `Order` evaluated against the same `Menu` always
  yields the same `Decision`.
- **Totality** — every `Order` yields exactly one `outcome`; `R3` is a catch-all,
  so evaluation always terminates with a decision.
- **Citation** — every `Decision` cites **at least one** `rule_id`: the rule that
  determined its outcome.
- **Single question** — an `ASK` `Decision` carries **exactly one** `question`;
  for `MAKE` and `REFUSE`, `question` is `None`.
- **Item matching** — `item` is matched against the `Menu` case-insensitively
  after trimming surrounding whitespace; an unmatched `item` is **off-menu**.

## Rules

Each rule has a **stable ID** (`R1`, `R2`, …), assigned sequentially and never
reused or renumbered. A rule's behavior is stated in testable terms (a concrete
input → expected `outcome` and `rule_ids`).

### R1: Make a valid order

- **Behavior:** An `Order` whose `item` is on the `Menu`, is `in_stock`, and has
  any required `size` supplied (i.e. `requires_size` is `false`, **or** `size`
  is not `None`) yields `MAKE`. The `reason` names the ordered item.
- **Example:** given `"oat latte"` is on the `Menu`, `in_stock`, and
  `requires_size` → `take_order(item="oat latte", size="medium")`
  → `MAKE`, `["R1"]`
- **Precedence:** defers to `R2` — an otherwise-makeable item that is missing a
  required `size` is asked about first.
- **Source:** issue #1 (US1 — Take an order)

### R2: Ask for a missing required choice

- **Behavior:** An `Order` whose `item` is on the `Menu` and `in_stock`, but for
  which `requires_size` is `true` and `size` is `None`, yields `ASK` with exactly
  one `question` requesting the size.
- **Example:** given `"latte"` is on the `Menu`, `in_stock`, and `requires_size`
  → `take_order(item="latte", size=None)`
  → `ASK`, `["R2"]`, `question="What size?"`
- **Precedence:** overrides `R1` (ask before making). Applies **only** to items
  that are on the `Menu` and `in_stock`; off-menu or out-of-stock items are
  handled by `R3`.
- **Source:** issue #1 (US1 — Take an order)

### R3: Refuse anything else

- **Behavior:** Any `Order` not handled by `R2` or `R1` — its `item` is off-menu,
  or the item is on the `Menu` but not `in_stock` — yields `REFUSE`. The `reason`
  states why (off-menu or out of stock). This is the catch-all that guarantees
  totality.
- **Example:** `take_order(item="unicorn frappe")` → `REFUSE`, `["R3"]`
  (off-menu); and given `"drip"` is on the `Menu` but **not** `in_stock`
  → `take_order(item="drip", size="large")` → `REFUSE`, `["R3"]` (out of stock)
- **Precedence:** lowest; the default outcome.
- **Source:** issue #1 (US1 — Take an order)

## Precedence order

Rules are evaluated as an **ordered list**; earlier entries win on conflict.
Highest priority first:

1. R2 — Ask for a missing required choice
2. R1 — Make a valid order
3. R3 — Refuse anything else

## Glossary

- **Order** — a customer's request: a drink `item` and an optional `size`.
- **Menu** — the shop's reference data: which drinks exist, whether each is
  `in_stock`, and whether each `requires_size`.
- **Decision** — the engine's output: an `outcome` plus the `rule_ids`, a
  `reason`, and (for `ASK`) a `question`.
- **MAKE** — the order is accepted and can be produced.
- **ASK** — the order is valid so far but missing a required choice; the engine
  asks one clarifying question.
- **REFUSE** — the order cannot be made (off-menu or out of stock).
- **off-menu** — an `item` with no matching `Menu` entry.
- **in_stock** — a `Menu` drink that can currently be made.
- **requires_size** — a `Menu` drink for which a `size` must be supplied.
