"""Tests for the Agent Shell and Visual Preview functionality."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from barista.core.models import Order
from barista.core.menu import Menu
from barista.agent import AgentResponse, process_order


@pytest.fixture
def sample_menu() -> Menu:
    """Fixture to provide a sample Menu."""
    return Menu(
        items={
            "latte": {
                "allergens": ["dairy"],
                "substitute": "oat latte",
                "prices": {
                    "small": 3.00,
                    "medium": 3.50,
                    "large": 4.00,
                },
            },
            "oat latte": {
                "allergens": [],
                "prices": {
                    "small": 3.50,
                    "medium": 4.00,
                    "large": 4.50,
                },
            },
        }
    )


def test_agent_response_make_outcome_with_existing_asset(sample_menu):
    """Test that a visual preview is resolved when the image asset exists locally."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assets_path = Path(tmpdir)
        # Pre-create the image file in the assets directory
        image_file = assets_path / "oat_latte.png"
        image_file.write_bytes(b"dummy image bytes")

        order = Order(item="oat latte", size="medium")
        # R4 evaluates to MAKE
        response = process_order(order, sample_menu, assets_dir=assets_path)

        assert response.decision.outcome == "MAKE"
        assert response.preview is not None
        assert response.preview["image_path"] == str(image_file.resolve())
        assert "oat latte" in response.preview["alt_text"]


def test_agent_response_make_outcome_with_missing_asset_no_api(sample_menu):
    """Test best-effort fallback: returns None when asset is missing and no API is provided."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assets_path = Path(tmpdir)
        order = Order(item="oat latte", size="medium")

        response = process_order(order, sample_menu, assets_dir=assets_path)

        assert response.decision.outcome == "MAKE"
        assert response.preview is None


def test_agent_response_make_outcome_with_missing_asset_api_success(sample_menu):
    """Test dynamic generation: generates and saves image via the mock Gemini API."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assets_path = Path(tmpdir)
        order = Order(item="oat latte", size="medium")

        # Mock the Google GenAI SDK client
        mock_client = MagicMock()
        mock_image = MagicMock()
        mock_image.image.image_bytes = b"generated image bytes"
        mock_response = MagicMock()
        mock_response.generated_images = [mock_image]
        mock_client.models.generate_images.return_value = mock_response

        response = process_order(
            order, sample_menu, assets_dir=assets_path, api_client=mock_client
        )

        assert response.decision.outcome == "MAKE"
        assert response.preview is not None
        assert response.preview["image_path"] == str((assets_path / "oat_latte.png").resolve())
        assert (assets_path / "oat_latte.png").read_bytes() == b"generated image bytes"
        mock_client.models.generate_images.assert_called_once()


def test_agent_response_make_outcome_api_failure_fallback(sample_menu):
    """Test best-effort fallback: if API call raises exception, order completes with preview=None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assets_path = Path(tmpdir)
        order = Order(item="oat latte", size="medium")

        mock_client = MagicMock()
        mock_client.models.generate_images.side_effect = Exception("API error")

        response = process_order(
            order, sample_menu, assets_dir=assets_path, api_client=mock_client
        )

        assert response.decision.outcome == "MAKE"
        assert response.preview is None


def test_agent_response_exclusivity_ask_outcome(sample_menu):
    """Test preview exclusivity: preview is strictly None for ASK outcomes (even if asset exists)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assets_path = Path(tmpdir)
        # Pre-create the image file in the assets directory
        image_file = assets_path / "latte.png"
        image_file.write_bytes(b"dummy image bytes")

        # No size specified -> results in ASK ("What size?")
        order = Order(item="latte", size=None)
        response = process_order(order, sample_menu, assets_dir=assets_path)

        assert response.decision.outcome == "ASK"
        assert response.preview is None


def test_agent_response_exclusivity_refuse_outcome(sample_menu):
    """Test preview exclusivity: preview is strictly None for REFUSE outcomes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        assets_path = Path(tmpdir)
        # Pre-create the image file in the assets directory
        image_file = assets_path / "latte.png"
        image_file.write_bytes(b"dummy image bytes")

        # Allergen safety conflict (hazelnut latte / nut allergy) -> results in REFUSE
        order = Order(item="latte", size="medium", allergies=["dairy"])
        response = process_order(order, sample_menu, assets_dir=assets_path)

        assert response.decision.outcome == "REFUSE"
        assert response.preview is None


def test_agent_response_make_outcome_with_assets_dir_none(sample_menu):
    """Test that preview is None when assets_dir is None."""
    order = Order(item="oat latte", size="medium")
    response = process_order(order, sample_menu, assets_dir=None)

    assert response.decision.outcome == "MAKE"
    assert response.preview is None


def test_agent_response_make_outcome_mkdir_exception(sample_menu, monkeypatch):
    """Test best-effort fallback: returns None when assets_dir creation fails with an exception."""
    order = Order(item="oat latte", size="medium")

    def mock_mkdir(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr(Path, "mkdir", mock_mkdir)

    response = process_order(order, sample_menu, assets_dir="/invalid/path")

    assert response.decision.outcome == "MAKE"
    assert response.preview is None

