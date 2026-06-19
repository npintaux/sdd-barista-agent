# Specification

> **Source of truth.** GitHub Issues are intake; this file is the contract the
> agent obeys. When the two disagree, this file (and its owners) decide.

## Overview

Given an `Order` (containing the parsed drink item and size), the engine returns a `Decision` (an `outcome` plus the `rule_ids` that fired), evaluating rules in precedence order against external lookup reference data for the menu and current ingredient stock.

## Domain model

- **Order** — the input. The customer's words are parsed into a structured order by the
  agent shell; the pure engine receives this and does NOT do natural-language parsing.
  Fields:
    - `item: str` — the requested drink, normalized (e.g. "latte", "oat latte").
    - `size: str | None` — the requested size if stated (e.g. "medium"), otherwise None.
- **Decision** — the output. Fields:
  - `outcome: str` — one of `MAKE`, `ASK`, `REFUSE`.
  - `rule_ids: list[str]` — the stable rule IDs that determined the outcome, ordered by precedence.
  - `ticket: dict | None` — the ticket (if outcome is `MAKE`), containing:
    - `drink: str` — the name of the drink.
  - `question: str | None` — the clarifying question (if outcome is `ASK`).
  - `explanation: str | None` — explanation of the decision (if outcome is `REFUSE` or `MAKE`).

## Global constraints

- Evaluation is deterministic: same `Order` + same external lookup data → same `Decision`.
- Totality: every `Order` yields exactly one outcome.

## Rules

### R1: Off-menu Refusal

- **Behavior:** If the requested `item` is not present on the menu (external lookup reference), the decision must be `REFUSE` with an explanation that the item is off-menu.
- **Example:** `evaluate(item="unicorn frappe", size=None)` → `REFUSE`, `["R1"]` (explanation: `"unicorn frappe is off-menu"`)
- **Precedence:** Evaluated first. Overrides R2, R3, R4.
- **Source:** issue #1

### R2: Out-of-stock Refusal

- **Behavior:** If the requested `item` is on the menu, but its required ingredients or the item itself is currently out of stock (external lookup reference), the decision must be `REFUSE` with an explanation that the item is out of stock.
- **Example:** `evaluate(item="drip", size="large")` → `REFUSE`, `["R2"]` (explanation: `"large drip is currently out of stock"`)
- **Precedence:** Deferred to R1 and R3. Overrides R4.
- **Source:** issue #1

### R3: Size Clarification

- **Behavior:** If the requested `item` is on the menu and in stock, but the `size` is not specified, the decision must be `ASK` with exactly one clarifying question: `"What size?"`.
- **Example:** `evaluate(item="latte", size=None)` → `ASK`, `["R3"]` (question: `"What size?"`)
- **Precedence:** Deferred to R1. Overrides R2 and R4.
- **Source:** issue #1

### R4: Complete Order Fullfillment

- **Behavior:** If the requested `item` is on the menu, in stock, and the `size` is specified, the decision must be `MAKE` with a ticket for the drink and a brief explanation.
- **Example:** `evaluate(item="oat latte", size="medium")` → `MAKE`, `["R4"]` (ticket: `{"drink": "medium oat latte"}`)
- **Precedence:** Evaluated last, deferred to R1, R2, and R3.
- **Source:** issue #1

## Precedence order

Rules are evaluated as an **ordered list**; earlier entries win on conflict:

1. R1 — Off-menu Refusal
2. R3 — Size Clarification
3. R2 — Out-of-stock Refusal
4. R4 — Complete Order Fullfillment

## Glossary

- **menu** — external reference mapping available drink names (excluding size) to their base details/configurations.
- **stock** — external reference tracking the availability of ingredients or specific drink/size combinations.
- **ticket** — a structured representation of a fulfilled drink order, including the resolved drink name.
- **size** — the volume specification of the drink (e.g., small, medium, large).
