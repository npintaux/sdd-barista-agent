"""Decision engine for taking customer orders.

Exposes the main entry point take_order and manages the precedence and
evaluation of decision rules.
"""

from typing import Any
from barista.core.models import Order, Decision
from barista.core.menu import Menu
from barista.core.rules.base import Rule
from barista.core.rules.r1_off_menu import R1OffMenu
from barista.core.rules.r3_ask import R3Ask


class NoMatchingRuleError(Exception):
    """Exception raised when no rule in the engine evaluates to a Decision."""


# Ordered list of rule instances at the SPEC's precedence:
# 1. R1 — Off-menu Refusal
# 2. R3 — Size Clarification
# 3. R2 — Out-of-stock Refusal (Not yet implemented)
# 4. R4 — Complete Order Fullfillment (Not yet implemented)
RULES: list[Rule] = [
    R1OffMenu(),
    R3Ask(),
]


def take_order(order: Order, menu: Menu, stock: Any = None) -> Decision:
    """Evaluate a customer order against all configured decision rules.

    The rules are evaluated in a predefined precedence order. The first rule
    that matches and returns a decision determines the outcome.

    Args:
        order: The customer's order.
        menu: The menu reference data.
        stock: Optional stock reference data.

    Returns:
        The Decision made by the engine.

    Raises:
        NoMatchingRuleError: If no rules applied to the order.
    """
    for rule in RULES:
        decision = rule.evaluate(order, menu, stock)
        if decision is not None:
            return decision

    raise NoMatchingRuleError("No rule applied to the order")
