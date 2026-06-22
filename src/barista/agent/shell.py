"""Agent Shell wrapping the core decision engine and adding non-deterministic features."""

from pathlib import Path
from typing import Any
from barista.core.models import Order
from barista.core.engine import take_order
from barista.core.menu import Menu
from barista.agent.response import AgentResponse


def process_order(
    order: Order,
    menu: Menu,
    stock: Any = None,
    assets_dir: str | Path | None = None,
    api_client: Any = None,
    model_name: str = "imagen-3.0-generate-002",
) -> AgentResponse:
    """Evaluate a customer order and resolve a best-effort visual preview for MAKE outcomes.

    Args:
        order: The customer's order.
        menu: The menu reference data.
        stock: Optional stock reference data.
        assets_dir: Path to the directory where visual preview images are stored.
        api_client: Optional Google GenAI SDK Client to dynamically generate missing assets.
        model_name: The name of the image generation model to use.

    Returns:
        An AgentResponse wrapping the core Decision and any resolved preview metadata.
    """
    decision = take_order(order, menu, stock)

    # Preview Exclusivity: strictly None for ASK and REFUSE outcomes
    if decision.outcome != "MAKE":
        return AgentResponse(decision=decision, preview=None)

    # If assets_dir is not provided, we can look up in a default 'assets' folder or skip
    if assets_dir is None:
        return AgentResponse(decision=decision, preview=None)

    assets_path = Path(assets_dir)
    # Ensure assets directory exists
    try:
        assets_path.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Best-effort fallback: if directory cannot be created, return None
        return AgentResponse(decision=decision, preview=None)

    # Normalize drink name for the filename (e.g. "oat latte" -> "oat_latte.png")
    normalized_name = order.item.lower().replace(" ", "_")
    image_file = assets_path / f"{normalized_name}.png"
    alt_text = f"An illustrative preview of a freshly prepared {order.item}"

    # Best-Effort Preview: Check if local file exists first
    if image_file.exists():
        return AgentResponse(
            decision=decision,
            preview={
                "image_path": str(image_file.resolve()),
                "alt_text": alt_text,
            },
        )

    # If local file does not exist, attempt to generate it dynamically via Google GenAI SDK
    if api_client is not None:
        try:
            prompt = f"An illustrative, high quality, appetizing close-up preview of a {order.item}"
            response = api_client.models.generate_images(
                model=model_name,
                prompt=prompt,
                config={"number_of_images": 1},
            )
            # Verify we got an image in the response
            if response and hasattr(response, "generated_images") and response.generated_images:
                generated_image = response.generated_images[0]
                # Write image bytes to the local file
                image_bytes = getattr(generated_image.image, "image_bytes", None)
                if image_bytes:
                    image_file.write_bytes(image_bytes)
                    return AgentResponse(
                        decision=decision,
                        preview={
                            "image_path": str(image_file.resolve()),
                            "alt_text": alt_text,
                        },
                    )
        except Exception:
            # Best-effort fallback: if generation fails, we complete the order without preview
            pass

    return AgentResponse(decision=decision, preview=None)
