"""Stock reference data module for the decision engine."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Stock:
    """Represents the stock availability reference data.

    Attributes:
        availability: A dictionary mapping drink item names to their size availability
                      or overall availability. e.g., {"drip": {"large": False}}
    """

    availability: dict[str, Any] = field(default_factory=dict)

    def is_available(self, item_name: str, size: str | None) -> bool:
        """Check if a drink item (and specific size, if given) is in stock.

        Args:
            item_name: The name of the drink.
            size: The requested size.

        Returns:
            True if the item (and size, if specified) is available, False otherwise.
        """
        # If the item itself is not present in stock records, default to in-stock
        if item_name not in self.availability:
            return True

        item_stock = self.availability[item_name]

        # If item_stock is a boolean, it represents the item's overall stock
        if isinstance(item_stock, bool):
            return item_stock

        # If item_stock is a dict mapping size -> availability
        if isinstance(item_stock, dict) and size is not None:
            # If the specific size is in the records, return its status
            if size in item_stock:
                return bool(item_stock[size])
            # If not explicitly marked out of stock, default to True
            return True

        return True
