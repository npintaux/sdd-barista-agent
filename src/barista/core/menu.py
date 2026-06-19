"""Menu reference data module for the decision engine."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Menu:
    """Represents the menu reference data.

    Attributes:
        items: A dictionary mapping drink item names to their details.
    """

    items: dict[str, dict] = field(default_factory=dict)

    def has_item(self, item_name: str) -> bool:
        """Check if an item is present on the menu.

        Args:
            item_name: The name of the item to check.

        Returns:
            True if the item is on the menu, False otherwise.
        """
        return item_name in self.items
