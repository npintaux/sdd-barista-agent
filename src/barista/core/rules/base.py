"""Base rule class for the Barista decision engine."""

from abc import ABC, abstractmethod
from typing import Any
from barista.core.models import Order, Decision
from barista.core.menu import Menu


class Rule(ABC):
    """Abstract base class for all rules in the decision engine."""

    @abstractmethod
    def evaluate(self, order: Order, menu: Menu, stock: Any = None) -> Decision | None:
        """Evaluate the rule against the given order and reference data.

        Args:
            order: The customer's order.
            menu: The menu reference data.
            stock: Optional stock reference data.

        Returns:
            A Decision if the rule applies, or None if it does not apply.
        """
