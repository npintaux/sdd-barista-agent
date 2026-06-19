"""Unit and engine-level tests for R2: Out-of-stock Refusal.

This file tests the R2 Out-of-stock Refusal rule in isolation (unit tests)
and via the engine's entry point (engine-level tests).
"""

import pytest
from barista.core.models import Order
from barista.core.menu import Menu
from barista.core.stock import Stock
from barista.core.rules.r2_out_of_stock import R2OutOfStock
from barista.core.engine import take_order


# --- Test Reference Data for R2 ---
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

def test_r2_in_stock(sample_menu: Menu, sample_stock: Stock) -> None:
    """R2: If the item and size are in stock, R2 must not apply (returns None)."""
    # Given
    order = Order(item="drip", size="medium")
    rule = R2OutOfStock()

    # When
    decision = rule.evaluate(order, sample_menu, sample_stock)

    # Then
    assert decision is None


def test_r2_out_of_stock_with_size(sample_menu: Menu, sample_stock: Stock) -> None:
    """R2: If a specific size of a menu item is out of stock, it must be refused."""
    # Given
    order = Order(item="drip", size="large")
    rule = R2OutOfStock()

    # When
    decision = rule.evaluate(order, sample_menu, sample_stock)

    # Then
    assert decision is not None
    assert decision.outcome == "REFUSE"
    assert decision.rule_ids == ["R2"]
    assert decision.explanation == "large drip is currently out of stock"
    assert decision.ticket is None
    assert decision.question is None


def test_r2_out_of_stock_overall(sample_menu: Menu, sample_stock: Stock) -> None:
    """R2: If the item itself is marked out of stock, any size must be refused."""
    # Given
    order = Order(item="oat latte", size="medium")
    rule = R2OutOfStock()

    # When
    decision = rule.evaluate(order, sample_menu, sample_stock)

    # Then
    assert decision is not None
    assert decision.outcome == "REFUSE"
    assert decision.rule_ids == ["R2"]
    assert decision.explanation == "medium oat latte is currently out of stock"


def test_r2_off_menu(sample_menu: Menu, sample_stock: Stock) -> None:
    """R2: If the item is off-menu, R2 does not apply (delegates to R1)."""
    # Given
    order = Order(item="unicorn frappe", size="large")
    rule = R2OutOfStock()

    # When
    decision = rule.evaluate(order, sample_menu, sample_stock)

    # Then
    assert decision is None


# --- Engine-level Tests (Integration and Precedence) ---

def test_engine_r1_overrides_r2_for_off_menu(sample_menu: Menu, sample_stock: Stock) -> None:
    """Engine Precedence: R1 (Off-menu Refusal) must override R2 (Out-of-stock Refusal).

    Even if an item is out of stock in the stock database, if it's off-menu,
    it must be refused under R1 (off-menu explanation) first.
    """
    # Given
    order = Order(item="unicorn frappe", size="large")

    # When
    decision = take_order(order, sample_menu, sample_stock)

    # Then
    assert decision.outcome == "REFUSE"
    assert decision.rule_ids == ["R1"]
    assert decision.explanation == "unicorn frappe is off-menu"


def test_engine_r3_overrides_r2_for_missing_size(sample_menu: Menu, sample_stock: Stock) -> None:
    """Engine Precedence: R3 (Size Clarification) must override R2 (Out-of-stock Refusal).

    If an item is out of stock, but the size is not specified, we must ask "What size?"
    (R3) before refusing under R2.
    """
    # Given
    order = Order(item="drip", size=None)

    # When
    decision = take_order(order, sample_menu, sample_stock)

    # Then
    assert decision.outcome == "ASK"
    assert decision.rule_ids == ["R3"]
    assert decision.question == "What size?"


def test_engine_r2_triggered(sample_menu: Menu, sample_stock: Stock) -> None:
    """Engine: R2 triggers refusal when on-menu item size is out of stock."""
    # Given
    order = Order(item="drip", size="large")

    # When
    decision = take_order(order, sample_menu, sample_stock)

    # Then
    assert decision.outcome == "REFUSE"
    assert decision.rule_ids == ["R2"]
    assert decision.explanation == "large drip is currently out of stock"


def test_engine_r2_not_triggered_when_in_stock(sample_menu: Menu, sample_stock: Stock) -> None:
    """Engine: When item is in stock, R2 is skipped, and order completes successfully."""
    # Given
    order = Order(item="drip", size="medium")

    # When
    decision = take_order(order, sample_menu, sample_stock)

    # Then
    assert decision.outcome == "MAKE"
    assert decision.rule_ids == ["R4"]
    assert decision.ticket == {"drink": "medium drip"}



# --- Coverage-Boosting Edge Cases ---

def test_r2_out_of_stock_no_size_in_isolation(sample_menu: Menu, sample_stock: Stock) -> None:
    """R2: In isolation, if size is None and item is out of stock, it must refuse."""
    # Given
    order = Order(item="oat latte", size=None)
    rule = R2OutOfStock()

    # When
    decision = rule.evaluate(order, sample_menu, sample_stock)

    # Then
    assert decision is not None
    assert decision.outcome == "REFUSE"
    assert decision.rule_ids == ["R2"]
    assert decision.explanation == "oat latte is currently out of stock"


def test_stock_defaults_to_in_stock(sample_stock: Stock) -> None:
    """Stock: If an item is not present in stock records, it defaults to in-stock."""
    # Then
    assert sample_stock.is_available("latte", "medium") is True
    assert sample_stock.is_available("drip", None) is True


def test_stock_unlisted_size_defaults_to_in_stock(sample_stock: Stock) -> None:
    """Stock: If a size is not listed in an item's stock sub-dictionary, it defaults to in-stock."""
    # Then
    assert sample_stock.is_available("drip", "small") is True
