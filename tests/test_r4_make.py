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
    assert decision.ticket == {"drink": "medium latte"}
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
    assert decision.ticket == {"drink": "medium latte"}
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
