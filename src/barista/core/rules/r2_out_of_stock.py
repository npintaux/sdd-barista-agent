"""Rule R2: Out-of-stock Refusal.

If the requested drink is on the menu, but its required ingredients or the item
itself is currently out of stock, the decision must be REFUSE with an explanation.
"""

from typing import Any
from barista.core.models import Order, Decision
from barista.core.menu import Menu
from barista.core.rules.base import Rule


class R2OutOfStock(Rule):
    """Out-of-stock Refusal rule.

    This rule checks if the item (and size, if specified) is available in stock.
    If the stock lookup indicates it is unavailable, the order is refused.
    """

    def evaluate(self, order: Order, menu: Menu, stock: Any = None) -> Decision | None:
        """Evaluate if the ordered item is out of stock.

        Args:
            order: The customer's order.
            menu: The menu reference data.
            stock: Optional stock reference data.

        Returns:
            A REFUSE Decision if the item/size is out of stock, otherwise None.
        """
        if not menu.has_item(order.item):
            return None

        if stock is None:
            return None

        # Check availability from stock reference
        if not stock.is_available(order.item, order.size):
            # Format the explanation based on whether size is specified
            if order.size:
                explanation = f"{order.size} {order.item} is currently out of stock"
            else:
                explanation = f"{order.item} is currently out of stock"

            return Decision(
                outcome="REFUSE",
                rule_ids=["R2"],
                explanation=explanation,
            )

        return None
