"""Ticket schema validation module.

Defines the structure and validation logic for JSON tickets generated on MAKE
decisions, ensuring compliance with the contract.
"""

import re
from datetime import datetime
from typing import Any


class TicketValidationError(ValueError):
    """Raised when a ticket fails schema validation."""


def _validate_line_item(item: Any, idx: int) -> None:
    """Validate an individual line item.

    Args:
        item: The line item to validate.
        idx: The list index of the item.

    Raises:
        TicketValidationError: If validation fails.
    """
    if not isinstance(item, dict):
        raise TicketValidationError(
            f"Line item at index {idx} must be a dictionary"
        )

    item_keys = {"item", "size", "price"}
    missing_item_keys = item_keys - item.keys()
    if missing_item_keys:
        raise TicketValidationError(
            f"Line item at index {idx} is missing keys: {missing_item_keys}"
        )

    if not isinstance(item["item"], str) or not item["item"]:
        raise TicketValidationError(
            f"Line item 'item' at index {idx} must be a non-empty string"
        )

    if not isinstance(item["size"], str) or not item["size"]:
        raise TicketValidationError(
            f"Line item 'size' at index {idx} must be a non-empty string"
        )

    if not isinstance(item["price"], (int, float)):
        raise TicketValidationError(
            f"Line item 'price' at index {idx} must be a number"
        )


def _validate_line_items_list(line_items: Any) -> None:
    """Validate the complete list of line items.

    Args:
        line_items: The object to validate as a line items list.

    Raises:
        TicketValidationError: If validation fails.
    """
    if not isinstance(line_items, list):
        raise TicketValidationError("line_items must be a list")

    if not line_items:
        raise TicketValidationError("line_items must not be empty")

    for idx, item in enumerate(line_items):
        _validate_line_item(item, idx)


def _validate_metadata(ticket: dict[str, Any]) -> None:
    """Validate ticket prices, currency, policy version, and timestamps.

    Args:
        ticket: The ticket to validate metadata for.

    Raises:
        TicketValidationError: If validation fails.
    """
    # Validate total_price
    total_price = ticket["total_price"]
    if not isinstance(total_price, (int, float)):
        raise TicketValidationError("total_price must be a number")

    # Validate currency
    currency = ticket["currency"]
    if (
        not isinstance(currency, str)
        or len(currency) != 3
        or not currency.isupper()
    ):
        raise TicketValidationError(
            "currency must be a 3-letter uppercase string"
        )

    # Validate policy_version
    policy_version = ticket["policy_version"]
    if not isinstance(policy_version, str) or not re.match(
        r"^\d+\.\d+\.\d+$", policy_version
    ):
        raise TicketValidationError(
            "policy_version must be a semantic version string (e.g., '1.0.0')"
        )

    # Validate evaluated_at
    evaluated_at = ticket["evaluated_at"]
    if not isinstance(evaluated_at, str):
        raise TicketValidationError("evaluated_at must be a string")
    try:
        if evaluated_at.endswith("Z"):
            datetime.fromisoformat(evaluated_at[:-1] + "+00:00")
        else:
            datetime.fromisoformat(evaluated_at)
    except ValueError as e:
        raise TicketValidationError(
            f"evaluated_at is not a valid ISO 8601 string: {e}"
        ) from e


def validate_ticket(ticket: dict[str, Any]) -> None:
    """Validate a ticket against the published ticket schema.

    Args:
        ticket: The ticket dictionary to validate.

    Raises:
        TicketValidationError: If validation fails.
    """
    if not isinstance(ticket, dict):
        raise TicketValidationError("Ticket must be a dictionary")

    required_keys = {
        "line_items",
        "total_price",
        "currency",
        "policy_version",
        "evaluated_at",
    }
    missing_keys = required_keys - ticket.keys()
    if missing_keys:
        raise TicketValidationError(
            f"Ticket is missing required keys: {missing_keys}"
        )

    _validate_line_items_list(ticket["line_items"])
    _validate_metadata(ticket)
