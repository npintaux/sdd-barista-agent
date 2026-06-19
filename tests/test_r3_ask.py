"""Unit and engine-level tests for R3: Size Clarification.

This file tests the R3 Size Clarification rule in isolation (unit tests)
and via the engine's entry point (engine-level tests).
"""

import pytest
from barista.core.models import Order
from barista.core.menu import Menu
from barista.core.rules.r3_ask import R3Ask
from barista.core.engine import take_order, NoMatchingRuleError


# --- Test Menu Data for R3 ---
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

def test_r3_size_clarification_no_size(sample_menu: Menu) -> None:
    """R3: If size is None for a menu item, the rule must apply and ask 'What size?'."""
    # Given
    order = Order(item="latte", size=None)
    rule = R3Ask()

    # When
    decision = rule.evaluate(order, sample_menu)

    # Then
    assert decision is not None
    assert decision.outcome == "ASK"
    assert decision.rule_ids == ["R3"]
    assert decision.question == "What size?"
    assert decision.ticket is None
    assert decision.explanation is None


def test_r3_size_clarification_with_size(sample_menu: Menu) -> None:
    """R3: If size is specified, R3 must not apply (returns None)."""
    # Given
    order = Order(item="latte", size="large")
    rule = R3Ask()

    # When
    decision = rule.evaluate(order, sample_menu)

    # Then
    assert decision is None


def test_r3_size_clarification_off_menu(sample_menu: Menu) -> None:
    """R3: If the item is off-menu, R3 does not apply even if size is None."""
    # Given
    order = Order(item="unicorn frappe", size=None)
    rule = R3Ask()

    # When
    decision = rule.evaluate(order, sample_menu)

    # Then
    assert decision is None


# --- Engine-level Tests (Integration and Precedence) ---

def test_engine_r1_overrides_r3_for_off_menu(sample_menu: Menu) -> None:
    """Engine Precedence: R1 (Off-menu Refusal) must override R3 (Size Clarification).

    When an off-menu item is ordered with no size, it should be REFUSE (R1)
    and not ASK (R3).
    """
    # Given
    order = Order(item="unicorn frappe", size=None)

    # When
    decision = take_order(order, sample_menu)

    # Then
    assert decision.outcome == "REFUSE"
    assert decision.rule_ids == ["R1"]
    assert decision.explanation == "unicorn frappe is off-menu"


def test_engine_r3_triggered(sample_menu: Menu) -> None:
    """Engine: R3 triggers asking for size when menu item has no size."""
    # Given
    order = Order(item="latte", size=None)

    # When
    decision = take_order(order, sample_menu)

    # Then
    assert decision.outcome == "ASK"
    assert decision.rule_ids == ["R3"]
    assert decision.question == "What size?"


def test_engine_r3_not_triggered_when_size_provided(sample_menu: Menu) -> None:
    """Engine: Defer to later rules (which raise NoMatchingRuleError) when size is provided."""
    # Given
    order = Order(item="latte", size="medium")

    # When / Then
    with pytest.raises(NoMatchingRuleError, match="No rule applied to the order"):
        take_order(order, sample_menu)
