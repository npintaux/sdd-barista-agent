"""Rule R3: Size Clarification.

If the requested drink is on the menu but no size was specified,
the decision must be ASK with exactly one clarifying question: "What size?".
"""

from typing import Any
from barista.core.models import Order, Decision
from barista.core.menu import Menu
from barista.core.rules.base import Rule


class R3Ask(Rule):
    """Size Clarification rule.

    This rule checks if the item is present on the menu but its size is not
    specified, and asks for clarification if so.
    """

    def evaluate(self, order: Order, menu: Menu, stock: Any = None) -> Decision | None:
        """Evaluate if the order needs size clarification.

        Args:
            order: The customer's order.
            menu: The menu reference data.
            stock: Optional stock reference data.

        Returns:
            An ASK Decision if size is missing, otherwise None.
        """
        if not menu.has_item(order.item):
            return None

        if order.size is None:
            return Decision(
                outcome="ASK",
                rule_ids=["R3"],
                question="What size?",
            )

        return None
