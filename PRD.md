# PRD — Barista Agent

| | |
|---|---|
| **Product** | Barista Agent — a conversational order-taking agent for counter service |
| **Author** | Product Owner |
| **Status** | Draft |
| **Repo** | `npintaux/sdd-barista-agent` |
| **Last updated** | 2026-06-18 |

> **Altitude note.** This PRD is *product intent*. It describes the behaviour we want and how we'll know it's right — not the implementation. Engineering translates each accepted story into a technical specification, which becomes the source of truth the implementation follows.

---

## 1. Summary

The Barista Agent turns a customer's plain-language order into a clear, auditable decision: **make it, ask one clarifying question, or politely refuse** — always saying *why*. It is built as an ADK agent with a menu tool, and it is deliberately generic: the same mechanics re-skin to fast food, a pharmacy counter, or a ticket desk.

The differentiator is **trust**: every decision is deterministic, cites the rule(s) that produced it, and is safe by default (it will never auto-make an order that conflicts with a declared allergy).

## 2. Background & problem

Counter staff spend disproportionate time on repetitive order intake, clarifying ambiguous requests, and dietary-safety checks. Mistakes (wrong size, a missed allergen) are costly and occasionally dangerous. We want an assistant that converts natural orders into structured, priced tickets the POS/kitchen can act on automatically, while keeping a human in the loop exactly where it matters (clarify / refuse / substitute).

## 3. Goals & non-goals

**Goals**
- Convert a natural-language order into a structured decision and a kitchen ticket.
- Be **safe by default** — allergens and unknown items never slip through.
- Be **auditable** — every decision cites the rule(s) behind it.
- Be **cheap and observable** to run at counter scale.

**Non-goals (v1)**
- Payment processing, loyalty accrual, recommendations/upsell.
- Voice input, languages other than English, barista robotics.

## 4. Personas

- **Customer** — places an order in their own words.
- **Barista / counter staff** — acts on the ticket; handles `ASK` and `REFUSE` outcomes.
- **Shop manager** — owns the menu, pricing and allergen policy; reviews logs and cost.
- **POS / kitchen system** — a downstream consumer of the structured ticket.

## 5. Experience

Customer states an order → the agent interprets it against the current menu and the customer's dietary profile → it returns one of three outcomes:

- **MAKE** — produces a ticket the kitchen can act on.
- **ASK** — poses exactly one clarifying question (e.g. *"What size?"*).
- **REFUSE** — explains why (off-menu, out of stock, or unsafe).

## 6. Functional requirements

| ID | Requirement |
|----|-------------|
| **FR1** | Accept a free-text order. |
| **FR2** | Validate the requested item against the **current menu and stock**. |
| **FR3** | Return one decision — `MAKE` / `ASK` / `REFUSE` — with human-readable reasons **and** the rule id(s) that fired. |
| **FR4** | When a required attribute is missing (e.g. size, milk), **ASK one** clarifying question rather than guessing. |
| **FR5** | When the item is off-menu or out of stock, **REFUSE** with a reason. |
| **FR6** | **Allergen safety:** when an order conflicts with the customer's declared allergy, **never `MAKE`** — substitute (offer a safe alternative) or refuse — *regardless of menu match*. |
| **FR7** | On `MAKE`, produce a **priced ticket** with line items, total and currency. |
| **FR8** | Emit the ticket as **JSON validating against a published schema**, including audit fields (`policy_version`, `evaluated_at`). |
| **FR9** | *(Stretch)* When an order is made, show an illustrative **preview image** of the drink. |
| **FR10** | **Auditability:** every decision cites at least one rule id. |

## 7. Non-functional requirements

| ID | Requirement |
|----|-------------|
| **NFR1 — Determinism** | The same order, against the same menu and customer profile, yields the same decision. (Applies to the decision; the optional preview image is explicitly excluded.) |
| **NFR2 — Latency** | A decision returns in < 3 s p95 (excluding the optional image). |
| **NFR3 — Cost** | Default to the cheap model; escalate only on evidence. The optional preview is the expensive call — generate it **only on `MAKE`**. Track spend per team. |
| **NFR4 — Safety** | The agent must never emit a `MAKE` that violates a declared allergen. On any uncertainty, the safe default is `REFUSE`. |
| **NFR5 — Observability** | Usage attributed per user; metrics exported to the org's monitoring; budget alerts as spend thresholds are crossed. |
| **NFR6 — Testability** | Every acceptance criterion maps to exactly one automated test; CI must be green before merge; coverage ≥ 90%. |
| **NFR7 — Packaging** | Released as a **versioned package** (semantic versioning) via the org's artifact registry; a version bump signals any contract change. |
| **NFR8 — Maintainability** | Rules and the menu are declarative, so policies can evolve without rewriting the agent. |
| **NFR9 — Privacy & security** | No PII (including customer profiles) in logs; secrets never in code. |
| **NFR10 — Portability** | Re-skinnable to other counter-service domains with no change to the core decision mechanics. |

## 8. User stories (the backlog)

Each story is **independent** and delivers value on its own — they can be picked up and released in any order. Acceptance criteria are written as **observable behaviour with concrete examples** so each one can be mapped to a single test.

---

### US1 — Take an order
**As a** customer, **I want** to place an order in plain language **so that** I get my drink without learning a menu.

**Acceptance criteria**
- Given `"medium oat latte"` (on the menu, in stock) → **MAKE**; the ticket lists the drink and explains why.
- Given `"latte"` with **no size** → **ASK** one question (*"What size?"*).
- Given `"unicorn frappe"` (off-menu) → **REFUSE** with a reason.
- Given `"large drip"` that is **sold out** → **REFUSE** (out of stock).
- Every decision states the rule(s) behind it. When an order both needs clarifying and could be made, the agent **asks first**.

---

### US2 — Allergy safety
**As a** shop manager, **I want** orders that conflict with a customer's declared allergy to never be auto-made **so that** we never endanger a customer.

**Acceptance criteria**
- Given a profile declaring a **nut allergy** and order `"hazelnut latte"` → the agent does **not** make it; it **substitutes** (offers a nut-free option) or **refuses**, and says why.
- Allergen safety **overrides a valid menu match** — a drink that would otherwise be made is substituted or refused when it conflicts with a declared allergy.
- An order with **no** allergen conflict is handled normally.

---

### US3 — Priced, machine-readable ticket
**As a** POS/kitchen system, **I want** each decision as a validated JSON ticket with a price **so that** I can act on it automatically.

**Acceptance criteria**
- A made order returns a **JSON ticket**: line items, **total price**, currency, plus audit fields (`policy_version`, `evaluated_at`).
- The JSON **validates against a published schema**; an invalid payload is rejected.
- Prices are computed via a **shared, centrally-maintained pricing source** — never hard-coded.
- A change to the ticket format is signalled by a **version bump** so consumers can adapt.

---

### US4 — Visual preview  ·  *stretch / could-have*
**As a** customer, **I want** to see a picture of my drink **so that** ordering feels delightful.

**Acceptance criteria**
- When an order is **made**, the customer is shown **one** illustrative preview image of the drink (PNG, with alt-text, modestly sized).
- The image is an **illustrative preview**, not a guarantee of the drink's exact appearance; it is produced on a **best-effort** basis.
- A preview is shown **only for a made order** — not when the agent asks a question or refuses.
- If a preview cannot be produced, the order is **still completed without it** (the picture is never on the critical path).

---

## 9. Out of scope (v1)

Payments, loyalty accrual, upsell/recommendations, voice input, multi-language, robotics.

## 10. Success metrics

- **Auto-resolution rate** — % of orders that reach `MAKE` without human help.
- **Clarification rate** — % ending in `ASK`.
- **Allergen incidents** — target **zero**.
- **Cost** — tokens per decision; share of decisions that needed the expensive model/image.
- **Quality** — schema-validation pass rate; CI green rate.

## 11. Prioritisation

| Story | Priority |
|-------|----------|
| US1 — Take an order | Must have |
| US2 — Allergy safety | Must have |
| US3 — Priced, machine-readable ticket | Should have |
| US4 — Visual preview | Could have (stretch) |

The stories are independent and can be delivered in whatever order suits the team. Each accepted story ships as its own versioned release.

## 12. Open questions & risks

- Exact **menu** and the required attributes per drink (which need a size? a milk choice?).
- Source of the **customer dietary profile** and how allergens are declared.
- **Ownership and versioning** of the shared pricing component.
- **Feasibility, latency and cost** of generating preview images (gates the visual-preview stretch goal).
- **Who owns precedence** when product and engineering disagree on how rules should be ordered.
