# Specification

> **Source of truth.** GitHub Issues are intake; this file is the contract the
> agent obeys. When the two disagree, this file (and its owners) decide.

## Overview

Given an `Order` (containing the parsed drink item, size, and customer's declared allergies), the engine returns a `Decision` (an `outcome` plus the `rule_ids` that fired), evaluating rules in precedence order against external lookup reference data for the menu and current ingredient stock.

An **Agent Shell** wraps this pure, deterministic engine. The shell is responsible for user interaction, natural language parsing, and non-deterministic I/O tasks, such as resolving best-effort visual previews of the prepared drinks.

## Domain model

- **Order** — the input. The customer's words and profile are parsed into a structured order by the
  agent shell; the pure engine receives this and does NOT do natural-language parsing.
  Fields:
    - `item: str` — the requested drink, normalized (e.g. "latte", "oat latte").
    - `size: str | None` — the requested size if stated (e.g. "medium"), otherwise None.
    - `allergies: list[str]` — the list of customer's declared allergies (e.g. `["nut"]`). Defaults to empty.
- **Decision** — the output. Fields:
  - `outcome: str` — one of `MAKE`, `ASK`, `REFUSE`.
  - `rule_ids: list[str]` — the stable rule IDs that determined the outcome, ordered by precedence.
  - `ticket: dict | None` — the ticket (if outcome is `MAKE`), containing:
    - `line_items: list[dict]` — a list of purchased drink details, where each item contains:
      - `item: str` — the normalized name of the drink (e.g. `"oat latte"`).
      - `size: str` — the specified size of the drink (e.g. `"medium"`).
      - `price: float` — the computed price of the drink item.
    - `total_price: float` — the sum of prices of all line items.
    - `currency: str` — the three-letter currency code (e.g. `"USD"`).
    - `policy_version: str` — the version of the ticket schema/policy format (e.g. `"1.0.0"`).
    - `evaluated_at: str` — the ISO 8601 timestamp of evaluation (e.g. `"2026-06-22T08:37:30Z"`).
  - `question: str | None` — the clarifying question (if outcome is `ASK`).
  - `explanation: str | None` — explanation of the decision (if outcome is `REFUSE` or `MAKE`).
- **AgentResponse** — the final customer-facing output returned by the agent shell. Fields:
  - `decision: Decision` — the deterministic decision evaluated by the core engine.
  - `preview: dict | None` — the visual preview metadata of the drink. `None` if the outcome is not `MAKE` or if a preview cannot be found. If present, it contains:
    - `image_path: str` — the path or URI to the illustrative PNG image file.
    - `alt_text: str` — a descriptive alt-text string summarizing the visual appearance of the drink.

## Global constraints

- Evaluation is deterministic: same `Order` + same external lookup data → same `Decision`.
- Totality: every `Order` yields exactly one outcome.
- **Pricing Consistency:** All prices are computed using a shared, centrally-maintained pricing source (e.g., looking up menu prices) and never hard-coded in individual rules.
- **Ticket Schema Validation:** Any generated `ticket` (when outcome is `MAKE`) must conform to a published JSON schema; invalid payloads are rejected.
- **Format Schema Versioning:** Any changes to the ticket format structure are governed by semantic versioning, signaled by a bumped `policy_version` and/or schema version to allow consumers to adapt.
- **Visual Preview Isolation:** Visual preview resolution is managed completely within the non-deterministic `agent` shell and is kept completely isolated from the pure deterministic core decision engine rules.
- **Best-Effort Preview:** Drink previews are resolved on a best-effort basis. The agent shell checks local asset directories for pre-generated images. These assets can be pre-generated or dynamically generated/cached using Google's Gemini Flash Image model (affectionately nicknamed "Nano Banana") via the Google GenAI SDK. If no image can be found or generated, the preview must be `None` and the order must still complete successfully (never blocking the critical order path).
- **Preview Exclusivity:** A visual preview can only be shown for successful `MAKE` decisions. Previews must be strictly `None` for `ASK` or `REFUSE` decisions.

## Rules

### R1: Off-menu Refusal

- **Behavior:** If the requested `item` is not present on the menu (external lookup reference), the decision must be `REFUSE` with an explanation that the item is off-menu.
- **Example:** `evaluate(item="unicorn frappe", size=None)` → `REFUSE`, `["R1"]` (explanation: `"unicorn frappe is off-menu"`)
- **Precedence:** Evaluated first. Overrides R5, R2, R3, R4.
- **Source:** issue #1

### R5: Allergy Safety

- **Behavior:** If the requested `item` is on the menu, but it contains any allergen that conflicts with the customer's declared `allergies` (external lookup reference), the decision must be `REFUSE` (never `MAKE`). If a safe alternative `substitute` is defined on the menu for that item, the explanation must offer the substitute; otherwise, it must explain the refusal based on the allergen.
- **Example 1 (With substitute):** `evaluate(item="hazelnut latte", size="medium", allergies=["nut"])` → `REFUSE`, `["R5"]` (explanation: `"hazelnut latte contains nut, which conflicts with your allergy. Would you like a latte instead?"`)
- **Example 2 (Without substitute):** `evaluate(item="hazelnut latte", size="medium", allergies=["nut"])` → `REFUSE`, `["R5"]` (explanation: `"hazelnut latte contains nut, which conflicts with your allergy"`)
- **Precedence:** Deferred to R1. Overrides R3, R2, R4.
- **Source:** issue #2

### R3: Size Clarification

- **Behavior:** If the requested `item` is on the menu and in stock, but the `size` is not specified, the decision must be `ASK` with exactly one clarifying question: `"What size?"`.
- **Example:** `evaluate(item="latte", size=None)` → `ASK`, `["R3"]` (question: `"What size?"`)
- **Precedence:** Deferred to R1 and R5. Overrides R2 and R4.
- **Source:** issue #1

### R2: Out-of-stock Refusal

- **Behavior:** If the requested `item` is on the menu, but its required ingredients or the item itself is currently out of stock (external lookup reference), the decision must be `REFUSE` with an explanation that the item is out of stock.
- **Example:** `evaluate(item="drip", size="large")` → `REFUSE`, `["R2"]` (explanation: `"large drip is currently out of stock"`)
- **Precedence:** Deferred to R1, R5, and R3. Overrides R4.
- **Source:** issue #1

### R4: Complete Order Fulfillment

- **Behavior:** If the requested `item` is on the menu, in stock, and the `size` is specified, the decision must be `MAKE` with a validated, priced JSON ticket and a brief explanation.
- **Example:** `evaluate(item="oat latte", size="medium")` → `MAKE`, `["R4"]`
  ```json
  ticket: {
    "line_items": [
      {
        "item": "oat latte",
        "size": "medium",
        "price": 4.00
      }
    ],
    "total_price": 4.00,
    "currency": "USD",
    "policy_version": "1.0.0",
    "evaluated_at": "2026-06-22T08:37:30Z"
  }
  ```
- **Precedence:** Evaluated last, deferred to R1, R5, R3, and R2.
- **Source:** issue #1, issue #3

## Precedence order

Rules are evaluated as an **ordered list**; earlier entries win on conflict:

1. R1 — Off-menu Refusal
2. R5 — Allergy Safety
3. R3 — Size Clarification
4. R2 — Out-of-stock Refusal
5. R4 — Complete Order Fulfillment

## Glossary

- **menu** — external reference mapping available drink names (excluding size) to their base details/configurations (including associated `allergens`, optional `substitute`, and pricing).
- **stock** — external reference tracking the availability of ingredients or specific drink/size combinations.
- **ticket** — a structured, validated JSON representation of a fulfilled drink order, containing line items, total price, currency, plus evaluation/audit fields.
- **size** — the volume specification of the drink (e.g., small, medium, large).
- **allergies** — list of customer's declared allergies passed as part of the order profile.
- **allergens** — specific ingredients/substances in menu items (e.g., nut, dairy) that can cause allergic reactions.
- **pricing source** — the price catalog maintained by the **Shop Manager** (via the Store Catalog Service) and passed to the engine as part of the external `Menu` reference data. It is implemented as a sub-dictionary under each menu item mapping size keys to their respective prices.
  * *Example:*
    ```json
    {
      "items": {
        "latte": {
          "allergens": ["dairy"],
          "substitute": "oat latte",
          "prices": {
            "small": 3.00,
            "medium": 3.50,
            "large": 4.00
          }
        }
      }
    }
    ```
- **agent shell** — the container wrapper surrounding the decision core that handles parsing, I/O integrations, and non-deterministic features.
- **visual preview** — an illustrative image (PNG with descriptive alt-text) showing how the made drink looks. These are resolved on a best-effort basis by the agent shell, which either pulls from a local cache of pre-generated assets or generates them on-demand using Google's Gemini Flash Image ("Nano Banana") model series.
