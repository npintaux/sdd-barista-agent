"""Unit and engine-level tests for R4: Complete Order Fulfillment.

This file tests the R4 Complete Order Fulfillment rule in isolation (unit tests)
and via the engine's entry point (engine-level tests).
"""

import pytest
from barista.core.models import Order
from barista.core.menu import Menu
from barista.core.stock import Stock
from barista.core.rules.r4_make import R4Make
from barista.core.engine import take_order, NoMatchingRuleError
from barista.core import engine


# --- Test Reference Data for R4 ---
@pytest.fixture
def sample_menu() -> Menu:
    """Fixture to provide a standard menu for testing."""
    return Menu(
        items={
            "latte": {"price": 3.50},
            "oat latte": {"price": 4.00},
            "drip": {"price": 2.00},
        }
    )


@pytest.fixture
def sample_stock() -> Stock:
    """Fixture to provide a standard stock database for testing."""
    return Stock(
        availability={
            "drip": {"large": False, "medium": True},
            "oat latte": False,  # Completely out of stock
        }
    )


# --- Unit Tests (Rule in Isolation) ---

def test_r4_complete_fulfillment(sample_menu: Menu, sample_stock: Stock) -> None:
    """R4: If the item is on the menu, in stock, and size is specified, return MAKE."""
    # Given
    order = Order(item="latte", size="medium")
    rule = R4Make()

    # When
    decision = rule.evaluate(order, sample_menu, sample_stock)

    # Then
    assert decision is not None
    assert decision.outcome == "MAKE"
    assert decision.rule_ids == ["R4"]
    assert decision.ticket is not None
    assert decision.ticket["line_items"] == [{"item": "latte", "size": "medium", "price": 3.50}]
    assert decision.ticket["total_price"] == 3.50
    assert decision.ticket["currency"] == "USD"
    assert decision.ticket["policy_version"] == "1.0.0"
    assert "evaluated_at" in decision.ticket
    assert decision.explanation == "Making medium latte"
    assert decision.question is None


def test_r4_size_missing(sample_menu: Menu, sample_stock: Stock) -> None:
    """R4: If size is not specified, R4 must not apply (returns None)."""
    # Given
    order = Order(item="latte", size=None)
    rule = R4Make()

    # When
    decision = rule.evaluate(order, sample_menu, sample_stock)

    # Then
    assert decision is None


def test_r4_out_of_stock(sample_menu: Menu, sample_stock: Stock) -> None:
    """R4: If the item/size is out of stock, R4 must not apply (returns None)."""
    # Given
    order = Order(item="drip", size="large")
    rule = R4Make()

    # When
    decision = rule.evaluate(order, sample_menu, sample_stock)

    # Then
    assert decision is None


def test_r4_off_menu(sample_menu: Menu, sample_stock: Stock) -> None:
    """R4: If the item is off-menu, R4 must not apply (returns None)."""
    # Given
    order = Order(item="unicorn frappe", size="medium")
    rule = R4Make()

    # When
    decision = rule.evaluate(order, sample_menu, sample_stock)

    # Then
    assert decision is None


# --- Engine-level Tests (Integration and Precedence) ---

def test_engine_r1_overrides_r4(sample_menu: Menu, sample_stock: Stock) -> None:
    """Engine Precedence: R1 (Off-menu Refusal) must override R4 (Complete Order Fulfillment)."""
    # Given
    order = Order(item="unicorn frappe", size="medium")

    # When
    decision = take_order(order, sample_menu, sample_stock)

    # Then
    assert decision.outcome == "REFUSE"
    assert decision.rule_ids == ["R1"]
    assert decision.explanation == "unicorn frappe is off-menu"


def test_engine_r3_overrides_r4(sample_menu: Menu, sample_stock: Stock) -> None:
    """Engine Precedence: R3 (Size Clarification) must override R4 (Complete Order Fulfillment)."""
    # Given
    order = Order(item="latte", size=None)

    # When
    decision = take_order(order, sample_menu, sample_stock)

    # Then
    assert decision.outcome == "ASK"
    assert decision.rule_ids == ["R3"]
    assert decision.question == "What size?"


def test_engine_r2_overrides_r4(sample_menu: Menu, sample_stock: Stock) -> None:
    """Engine Precedence: R2 must override R4 (Complete Order Fulfillment)."""
    # Given
    order = Order(item="drip", size="large")

    # When
    decision = take_order(order, sample_menu, sample_stock)

    # Then
    assert decision.outcome == "REFUSE"
    assert decision.rule_ids == ["R2"]
    assert decision.explanation == "large drip is currently out of stock"


def test_engine_r4_fulfilled(sample_menu: Menu, sample_stock: Stock) -> None:
    """Engine: R4 successfully prepares the drink when all constraints are satisfied."""
    # Given
    order = Order(item="latte", size="medium")

    # When
    decision = take_order(order, sample_menu, sample_stock)

    # Then
    assert decision.outcome == "MAKE"
    assert decision.rule_ids == ["R4"]
    assert decision.ticket is not None
    assert decision.ticket["line_items"] == [{"item": "latte", "size": "medium", "price": 3.50}]
    assert decision.ticket["total_price"] == 3.50
    assert decision.ticket["currency"] == "USD"
    assert decision.ticket["policy_version"] == "1.0.0"
    assert "evaluated_at" in decision.ticket
    assert decision.explanation == "Making medium latte"


def test_engine_no_rule_applies_fallback(sample_menu: Menu) -> None:
    """Engine: Raises NoMatchingRuleError if the rules list is empty (fallback)."""
    # Given
    order = Order(item="latte", size="medium")
    original_rules = engine.RULES
    engine.RULES = []

    try:
        # When / Then
        with pytest.raises(NoMatchingRuleError, match="No rule applied to the order"):
            take_order(order, sample_menu)
    finally:
        # Restore original rules
        engine.RULES = original_rules


def test_r4_size_based_pricing_lookup() -> None:
    """R4: Checks that size-based prices are correctly resolved from the 'prices' dictionary."""
    menu = Menu(
        items={
            "latte": {
                "prices": {
                    "small": 3.00,
                    "medium": 3.50,
                    "large": 4.00
                }
            }
        }
    )
    order = Order(item="latte", size="large")
    rule = R4Make()
    decision = rule.evaluate(order, menu)
    assert decision is not None
    assert decision.ticket["line_items"][0]["price"] == 4.00
    assert decision.ticket["total_price"] == 4.00


from barista.core.schema import validate_ticket, TicketValidationError

def test_ticket_schema_validation_failures() -> None:
    """Tests all ticket schema validation failure modes for 100% coverage."""
    # 1. Not a dictionary
    with pytest.raises(TicketValidationError, match="Ticket must be a dictionary"):
        validate_ticket("not-a-dict")

    # 2. Missing required keys
    with pytest.raises(TicketValidationError, match="Ticket is missing required keys"):
        validate_ticket({})

    # Base valid ticket for subsequent test alterations
    base_ticket = {
        "line_items": [{"item": "latte", "size": "medium", "price": 3.50}],
        "total_price": 3.50,
        "currency": "USD",
        "policy_version": "1.0.0",
        "evaluated_at": "2026-06-22T08:44:02Z",
    }

    # 3. line_items not a list
    invalid_ticket = base_ticket.copy()
    invalid_ticket["line_items"] = "not-a-list"
    with pytest.raises(TicketValidationError, match="line_items must be a list"):
        validate_ticket(invalid_ticket)

    # 4. line_items is empty
    invalid_ticket = base_ticket.copy()
    invalid_ticket["line_items"] = []
    with pytest.raises(TicketValidationError, match="line_items must not be empty"):
        validate_ticket(invalid_ticket)

    # 5. Line item is not a dict
    invalid_ticket = base_ticket.copy()
    invalid_ticket["line_items"] = ["not-a-dict"]
    with pytest.raises(TicketValidationError, match="Line item at index 0 must be a dictionary"):
        validate_ticket(invalid_ticket)

    # 6. Line item is missing keys
    invalid_ticket = base_ticket.copy()
    invalid_ticket["line_items"] = [{"item": "latte"}]
    with pytest.raises(TicketValidationError, match="Line item at index 0 is missing keys"):
        validate_ticket(invalid_ticket)

    # 7. Line item types: invalid item
    invalid_ticket = base_ticket.copy()
    invalid_ticket["line_items"] = [{"item": 123, "size": "medium", "price": 3.50}]
    with pytest.raises(TicketValidationError, match="Line item 'item' at index 0 must be a non-empty string"):
        validate_ticket(invalid_ticket)

    # 8. Line item types: empty item
    invalid_ticket = base_ticket.copy()
    invalid_ticket["line_items"] = [{"item": "", "size": "medium", "price": 3.50}]
    with pytest.raises(TicketValidationError, match="Line item 'item' at index 0 must be a non-empty string"):
        validate_ticket(invalid_ticket)

    # 9. Line item types: invalid size
    invalid_ticket = base_ticket.copy()
    invalid_ticket["line_items"] = [{"item": "latte", "size": 456, "price": 3.50}]
    with pytest.raises(TicketValidationError, match="Line item 'size' at index 0 must be a non-empty string"):
        validate_ticket(invalid_ticket)

    # 10. Line item types: empty size
    invalid_ticket = base_ticket.copy()
    invalid_ticket["line_items"] = [{"item": "latte", "size": "", "price": 3.50}]
    with pytest.raises(TicketValidationError, match="Line item 'size' at index 0 must be a non-empty string"):
        validate_ticket(invalid_ticket)

    # 11. Line item types: invalid price
    invalid_ticket = base_ticket.copy()
    invalid_ticket["line_items"] = [{"item": "latte", "size": "medium", "price": "free"}]
    with pytest.raises(TicketValidationError, match="Line item 'price' at index 0 must be a number"):
        validate_ticket(invalid_ticket)

    # 12. total_price is invalid type
    invalid_ticket = base_ticket.copy()
    invalid_ticket["total_price"] = "expensive"
    with pytest.raises(TicketValidationError, match="total_price must be a number"):
        validate_ticket(invalid_ticket)

    # 13. currency is invalid type
    invalid_ticket = base_ticket.copy()
    invalid_ticket["currency"] = 123
    with pytest.raises(TicketValidationError, match="currency must be a 3-letter uppercase string"):
        validate_ticket(invalid_ticket)

    # 14. currency is wrong length
    invalid_ticket = base_ticket.copy()
    invalid_ticket["currency"] = "US"
    with pytest.raises(TicketValidationError, match="currency must be a 3-letter uppercase string"):
        validate_ticket(invalid_ticket)

    # 15. currency is lowercase
    invalid_ticket = base_ticket.copy()
    invalid_ticket["currency"] = "usd"
    with pytest.raises(TicketValidationError, match="currency must be a 3-letter uppercase string"):
        validate_ticket(invalid_ticket)

    # 16. policy_version is not a string
    invalid_ticket = base_ticket.copy()
    invalid_ticket["policy_version"] = 1
    with pytest.raises(TicketValidationError, match="policy_version must be a semantic version string"):
        validate_ticket(invalid_ticket)

    # 17. policy_version is not semver
    invalid_ticket = base_ticket.copy()
    invalid_ticket["policy_version"] = "1.0"
    with pytest.raises(TicketValidationError, match="policy_version must be a semantic version string"):
        validate_ticket(invalid_ticket)

    # 18. evaluated_at is not a string
    invalid_ticket = base_ticket.copy()
    invalid_ticket["evaluated_at"] = 123456789
    with pytest.raises(TicketValidationError, match="evaluated_at must be a string"):
        validate_ticket(invalid_ticket)

    # 19. evaluated_at is invalid ISO string
    invalid_ticket = base_ticket.copy()
    invalid_ticket["evaluated_at"] = "June 22, 2026"
    with pytest.raises(TicketValidationError, match="evaluated_at is not a valid ISO 8601 string"):
        validate_ticket(invalid_ticket)

