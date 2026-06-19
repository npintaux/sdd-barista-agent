"""Rule R5: Allergy Safety.

If the requested drink is on the menu, but it contains any allergen that conflicts
with the customer's declared allergies, the decision must be REFUSE with an
explanation that explains the allergy conflict and offers a substitute if available.
"""

from typing import Any
from barista.core.models import Order, Decision
from barista.core.menu import Menu
from barista.core.rules.base import Rule


class R5Allergy(Rule):
    """Allergy Safety rule.

    This rule triggers when a customer profile declares an allergy that conflicts
    with the allergens of the requested menu item. It refuses the order and
    proposes a safe substitute if one is configured on the menu.
    """

    def evaluate(self, order: Order, menu: Menu, stock: Any = None) -> Decision | None:
        """Evaluate if the order conflicts with any customer allergies.

        Args:
            order: The customer's order.
            menu: The menu reference data.
            stock: Optional stock reference data.

        Returns:
            A REFUSE Decision if there is an allergen conflict, otherwise None.
        """
        if not menu.has_item(order.item):
            return None

        item_details = menu.items.get(order.item, {})
        allergens = item_details.get("allergens", [])

        # Find any matching allergens between order.allergies and item.allergens
        matching_allergens = [a for a in order.allergies if a in allergens]

        if not matching_allergens:
            return None

        conflict_allergen = matching_allergens[0]
        substitute = item_details.get("substitute")

        if substitute:
            explanation = (
                f"{order.item} contains {conflict_allergen}, which conflicts with your allergy. "
                f"Would you like a {substitute} instead?"
            )
        else:
            explanation = (
                f"{order.item} contains {conflict_allergen}, which conflicts with your allergy"
            )

        return Decision(
            outcome="REFUSE",
            rule_ids=["R5"],
            explanation=explanation,
        )
