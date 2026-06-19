"""Rule R1: Off-menu Refusal.

If the requested drink item is not present on the menu, the decision
must be REFUSE with an explanation that the item is off-menu.
"""

from typing import Any
from barista.core.models import Order, Decision
from barista.core.menu import Menu
from barista.core.rules.base import Rule


class R1OffMenu(Rule):
    """Off-menu Refusal rule.

    This rule checks if the requested drink is in the menu. If not, it refuses
    the order since the item is off-menu.
    """

    def evaluate(self, order: Order, menu: Menu, stock: Any = None) -> Decision | None:
        """Evaluate if the ordered item is off-menu.

        Args:
            order: The customer's order.
            menu: The menu reference data.
            stock: Optional stock reference data.

        Returns:
            A REFUSE Decision if the item is not on the menu, otherwise None.
        """
        if not menu.has_item(order.item):
            return Decision(
                outcome="REFUSE",
                rule_ids=["R1"],
                explanation=f"{order.item} is off-menu",
            )
        return None
