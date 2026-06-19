"""Rule R4: Complete Order Fulfillment.

If the requested drink is on the menu, in stock, and the size is specified,
the decision must be MAKE with a ticket for the drink and a brief explanation.
"""

from typing import Any
from barista.core.models import Order, Decision
from barista.core.menu import Menu
from barista.core.rules.base import Rule


class R4Make(Rule):
    """Complete Order Fulfillment rule.

    This rule triggers when all constraints are met (valid menu item, size is
    specified, and it is in stock), representing successful drink preparation.
    """

    def evaluate(self, order: Order, menu: Menu, stock: Any = None) -> Decision | None:
        """Evaluate if the order can be completely fulfilled.

        Args:
            order: The customer's order.
            menu: The menu reference data.
            stock: Optional stock reference data.

        Returns:
            A MAKE Decision if all conditions are satisfied, otherwise None.
        """
        if not menu.has_item(order.item):
            return None

        if order.size is None:
            return None

        # R4 only applies if in stock
        if stock is not None and not stock.is_available(order.item, order.size):
            return None

        drink_name = f"{order.size} {order.item}"
        return Decision(
            outcome="MAKE",
            rule_ids=["R4"],
            ticket={"drink": drink_name},
            explanation=f"Making {drink_name}",
        )
