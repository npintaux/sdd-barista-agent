"""Unit and engine-level tests for R5: Allergy Safety.

This file tests the R5 Allergy Safety rule in isolation (unit tests)
and via the engine's entry point (engine-level tests).
"""

import pytest
from barista.core.models import Order
from barista.core.menu import Menu
from barista.core.stock import Stock
from barista.core.rules.r5_allergy import R5Allergy
from barista.core.engine import take_order


# --- Test Reference Data for R5 ---
@pytest.fixture
def sample_menu() -> Menu:
    """Fixture to provide a standard menu with allergen profiles for testing."""
    return Menu(
        items={
            "latte": {"price": 3.50},
            "oat latte": {"price": 4.00},
            "drip": {"price": 2.00},
            "hazelnut latte": {
                "price": 4.50,
                "allergens": ["nut"],
                "substitute": "latte",
            },
            "almond latte": {
                "price": 4.50,
                "allergens": ["nut"],
            },
        }
    )


@pytest.fixture
def sample_stock() -> Stock:
    """Fixture to provide a standard stock database for testing."""
    return Stock(
        availability={
            "drip": {"large": False, "medium": True},
            "hazelnut latte": True,
            "almond latte": True,
        }
    )


# --- Unit Tests (Rule in Isolation) ---

def test_r5_allergy_conflict_with_substitute(sample_menu: Menu) -> None:
    """R5: If an allergen is matched and a substitute exists, suggest the substitute."""
    # Given
    order = Order(item="hazelnut latte", size="medium", allergies=["nut"])
    rule = R5Allergy()

    # When
    decision = rule.evaluate(order, sample_menu)

    # Then
    assert decision is not None
    assert decision.outcome == "REFUSE"
    assert decision.rule_ids == ["R5"]
    assert decision.explanation == (
        "hazelnut latte contains nut, which conflicts with your allergy. "
        "Would you like a latte instead?"
    )
    assert decision.ticket is None
    assert decision.question is None


def test_r5_allergy_conflict_no_substitute(sample_menu: Menu) -> None:
    """R5: If an allergen is matched but no substitute exists, just explain the refusal."""
    # Given
    order = Order(item="almond latte", size="medium", allergies=["nut"])
    rule = R5Allergy()

    # When
    decision = rule.evaluate(order, sample_menu)

    # Then
    assert decision is not None
    assert decision.outcome == "REFUSE"
    assert decision.rule_ids == ["R5"]
    assert decision.explanation == "almond latte contains nut, which conflicts with your allergy"
    assert decision.ticket is None
    assert decision.question is None


def test_r5_no_allergy_conflict(sample_menu: Menu) -> None:
    """R5: If there is no allergy conflict, R5 must not apply (returns None)."""
    # Given
    order = Order(item="latte", size="medium", allergies=["nut"])
    rule = R5Allergy()

    # When
    decision = rule.evaluate(order, sample_menu)

    # Then
    assert decision is None


def test_r5_off_menu_in_isolation(sample_menu: Menu) -> None:
    """R5: In isolation, if the item is off-menu, R5 does not apply (returns None)."""
    # Given
    order = Order(item="unicorn frappe", size="medium", allergies=["nut"])
    rule = R5Allergy()

    # When
    decision = rule.evaluate(order, sample_menu)

    # Then
    assert decision is None


# --- Engine-level Tests (Integration and Precedence) ---

def test_engine_r1_overrides_r5(sample_menu: Menu, sample_stock: Stock) -> None:
    """Engine Precedence: R1 (Off-menu Refusal) must override R5 (Allergy Safety)."""
    # Given
    order = Order(item="unicorn frappe", size="medium", allergies=["nut"])

    # When
    decision = take_order(order, sample_menu, sample_stock)

    # Then
    assert decision.outcome == "REFUSE"
    assert decision.rule_ids == ["R1"]
    assert decision.explanation == "unicorn frappe is off-menu"


def test_engine_r5_overrides_r3(sample_menu: Menu, sample_stock: Stock) -> None:
    """Engine Precedence: R5 (Allergy Safety) must override R3 (Size Clarification)."""
    # Given
    order = Order(item="hazelnut latte", size=None, allergies=["nut"])

    # When
    decision = take_order(order, sample_menu, sample_stock)

    # Then
    assert decision.outcome == "REFUSE"
    assert decision.rule_ids == ["R5"]
    assert decision.explanation == (
        "hazelnut latte contains nut, which conflicts with your allergy. "
        "Would you like a latte instead?"
    )


def test_engine_r5_overrides_r2(sample_menu: Menu) -> None:
    """Engine Precedence: R5 (Allergy Safety) must override R2 (Out-of-stock Refusal)."""
    # Given
    order = Order(item="hazelnut latte", size="medium", allergies=["nut"])
    # Stock states it's sold out completely
    empty_stock = Stock(availability={"hazelnut latte": False})

    # When
    decision = take_order(order, sample_menu, empty_stock)

    # Then
    assert decision.outcome == "REFUSE"
    assert decision.rule_ids == ["R5"]
    assert decision.explanation == (
        "hazelnut latte contains nut, which conflicts with your allergy. "
        "Would you like a latte instead?"
    )


def test_engine_r5_overrides_r4(sample_menu: Menu, sample_stock: Stock) -> None:
    """Engine Precedence: R5 (Allergy Safety) must override R4 (Complete Order Fulfillment)."""
    # Given
    order = Order(item="hazelnut latte", size="medium", allergies=["nut"])

    # When
    decision = take_order(order, sample_menu, sample_stock)

    # Then
    assert decision.outcome == "REFUSE"
    assert decision.rule_ids == ["R5"]
    assert decision.explanation == (
        "hazelnut latte contains nut, which conflicts with your allergy. "
        "Would you like a latte instead?"
    )
