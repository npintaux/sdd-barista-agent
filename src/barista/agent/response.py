"""Model for the customer-facing Agent Shell response."""

from dataclasses import dataclass
from barista.core.models import Decision


@dataclass(frozen=True)
class AgentResponse:
    """Represents the final customer-facing response returned by the Agent Shell.

    Attributes:
        decision: The deterministic decision evaluated by the core engine.
        preview: The visual preview metadata of the drink, if outcome is MAKE.
    """

    decision: Decision
    preview: dict[str, str] | None = None
