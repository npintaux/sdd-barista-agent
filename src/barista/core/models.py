"""Domain models for the Barista decision engine."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Order:
    """Represents a customer order.

    Attributes:
        item: The normalized name of the drink item.
        size: The requested size of the drink, if specified.
    """

    item: str
    size: str | None = None


@dataclass(frozen=True)
class Decision:
    """Represents the decision outcome from the engine.

    Attributes:
        outcome: The outcome of the decision (e.g., 'MAKE', 'ASK', 'REFUSE').
        rule_ids: The list of rule IDs that determined the outcome, ordered by precedence.
        ticket: The structured ticket if the drink is to be made.
        question: Clarifying question if the engine needs to ask.
        explanation: The rationale/explanation for the decision.
    """

    outcome: str
    rule_ids: list[str] = field(default_factory=list)
    ticket: dict[str, str] | None = None
    question: str | None = None
    explanation: str | None = None
