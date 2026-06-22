"""Unit and engine-level tests for R1: Off-menu Refusal.

This file tests the R1 Off-menu Refusal rule in isolation (unit tests)
and via the engine's entry point (engine-level tests).
"""

import pytest
from barista.core.models import Order
from barista.core.menu import Menu
from barista.core.rules.r1_off_menu import R1OffMenu
from barista.core.engine import take_order


# --- Test Menu Data for R1 ---
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


# --- Unit Tests (Rule in Isolation) ---

def test_r1_off_menu_not_on_menu(sample_menu: Menu) -> None:
    """R1: If the item is not on the menu, it must be refused as off-menu."""
    # Given
    order = Order(item="unicorn frappe", size=None)
    rule = R1OffMenu()

    # When
    decision = rule.evaluate(order, sample_menu)

    # Then
    assert decision is not None
    assert decision.outcome == "REFUSE"
    assert decision.rule_ids == ["R1"]
    assert decision.explanation == "unicorn frappe is off-menu"
    assert decision.ticket is None
    assert decision.question is None


def test_r1_off_menu_is_on_menu(sample_menu: Menu) -> None:
    """R1: If the item is on the menu, R1 should not apply (return None)."""
    # Given
    order = Order(item="latte", size="medium")
    rule = R1OffMenu()

    # When
    decision = rule.evaluate(order, sample_menu)

    # Then
    assert decision is None


# --- Engine-level Tests (Integration) ---

def test_engine_r1_refusal_triggered(sample_menu: Menu) -> None:
    """Engine: R1 triggers off-menu refusal when item is not on the menu."""
    # Given
    order = Order(item="unicorn frappe", size=None)

    # When
    decision = take_order(order, sample_menu)

    # Then
    assert decision.outcome == "REFUSE"
    assert decision.rule_ids == ["R1"]
    assert decision.explanation == "unicorn frappe is off-menu"


def test_engine_complete_order_fulfilled(sample_menu: Menu) -> None:
    """Engine: A complete valid order is successfully prepared (R4)."""
    # Given
    order = Order(item="latte", size="medium")

    # When
    decision = take_order(order, sample_menu)

    # Then
    assert decision.outcome == "MAKE"
    assert decision.rule_ids == ["R4"]
    assert decision.ticket is not None
    assert decision.ticket["line_items"] == [{"item": "latte", "size": "medium", "price": 3.50}]
    assert decision.ticket["total_price"] == 3.50
    assert decision.ticket["currency"] == "USD"
    assert decision.ticket["policy_version"] == "1.0.0"
    assert "evaluated_at" in decision.ticket
