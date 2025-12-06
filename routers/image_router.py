"""
Image Generation Router

Handles image generation requests from the frontend, coordinates with the
Image AI Service, and returns generated images.

After successful generation, content is directly injected into Layout Service.

Endpoints:
    POST /image - Generate image
    GET /image/styles - Get available image styles
    GET /image/credits/{presentation_id} - Get image credits
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter

from models import (
    ImageGenerateRequest,
    ImageGenerateResponse,
    ErrorDetail
)
from services.image_service import ImageService
from services.layout_service import layout_service
from utils.grid_utils import convert_grid_position

logger = logging.getLogger(__name__)

router = APIRouter()
image_service = ImageService()


@router.post("/image", response_model=ImageGenerateResponse)
async def generate_image(request: ImageGenerateRequest):
    """
    Generate an image using the Image AI Service.

    This endpoint:
    1. Converts Layout Service grid position to Image AI dimensions
    2. Calls the Image AI Service to generate the image
    3. Returns the image URL or base64 content

    The frontend should then send the image_url to the Layout Service
    iframe via postMessage to render the image element.

    Credits are consumed based on quality tier:
    - draft (512px): 1 credit
    - standard (1024px): 2 credits
    - high (1536px): 4 credits
    - ultra (2048px): 8 credits
    """
    logger.info(f"Image generation request: element={request.element_id}, style={request.style.value}")

    # Convert grid position to dimensions
    grid_dims = convert_grid_position(request.position)
    logger.debug(f"Grid conversion: position={request.position} -> dims={grid_dims}")

    # Build context for Image AI
    context = {
        "presentationTitle": request.context.presentation_title,
        "slideTitle": request.context.slide_title,
        "slideIndex": request.context.slide_index,
    }

    if request.context.presentation_theme:
        context["presentationTheme"] = request.context.presentation_theme
    if request.context.brand_colors:
        context["brandColors"] = request.context.brand_colors
    if request.context.industry:
        context["industry"] = request.context.industry

    # Call Image AI Service
    result = await image_service.generate(
        prompt=request.prompt,
        presentation_id=request.context.presentation_id,
        slide_id=request.context.slide_id,
        element_id=request.element_id,
        context=context,
        constraints={
            "gridWidth": grid_dims["width"],
            "gridHeight": grid_dims["height"]
        },
        style=request.style.value,
        quality=request.quality.value,
        aspect_ratio=request.aspect_ratio.value,
        negative_prompt=request.negative_prompt,
        seed=request.seed
    )

    # Handle error response
    if not result.get("success", False):
        error_info = result.get("error", {})
        return ImageGenerateResponse(
            success=False,
            element_id=request.element_id,
            error=ErrorDetail(
                code=error_info.get("code", "UNKNOWN_ERROR"),
                message=error_info.get("message", "Image generation failed"),
                retryable=error_info.get("retryable", False),
                suggestion=error_info.get("suggestion")
            )
        )

    # Extract data from response
    data = result.get("data", {})

    logger.info(f"Image generated successfully: element={request.element_id}")

    # Inject content into Layout Service
    injected = None
    injection_error = None

    image_url = data.get("imageUrl") or data.get("image_url") or result.get("imageUrl")
    image_base64 = data.get("imageBase64") or data.get("image_base64") or result.get("imageBase64")
    alt_text = data.get("altText") or data.get("alt_text") or request.prompt[:100]

    if image_url or image_base64:
        injection_result = await layout_service.inject_image(
            presentation_id=request.context.presentation_id,
            slide_index=request.context.slide_index,
            element_id=request.element_id,
            image_url=image_url,
            image_base64=image_base64,
            alt_text=alt_text
        )
        injected = injection_result.get("success", False)
        if not injected:
            injection_error = injection_result.get("error", "Unknown injection error")
            logger.warning(f"Image injection failed: {injection_error}")
        else:
            logger.info(f"Image injected into Layout Service: element={request.element_id}")

    return ImageGenerateResponse(
        success=True,
        element_id=request.element_id,
        image_url=image_url,
        image_base64=image_base64,
        alt_text=alt_text,
        width=data.get("width") or result.get("width"),
        height=data.get("height") or result.get("height"),
        style_applied=request.style.value,
        quality_applied=request.quality.value,
        credits_used=data.get("creditsUsed") or data.get("credits_used") or result.get("creditsUsed"),
        credits_remaining=data.get("creditsRemaining") or data.get("credits_remaining") or result.get("creditsRemaining"),
        seed_used=data.get("seedUsed") or data.get("seed_used") or result.get("seedUsed"),
        injected=injected,
        injection_error=injection_error
    )


@router.get("/image/styles")
async def get_image_styles():
    """
    Get available image styles with their descriptions.

    Returns an array of style definitions, each containing:
    - style: Style identifier
    - name: Human-readable name
    - description: Description of the style
    - bestFor: List of recommended use cases

    Also includes quality tiers with their resolution and credit costs.

    Available styles:
    - realistic: Photo-realistic imagery (Business, Corporate, Marketing)
    - illustration: Hand-drawn style (Educational, Storytelling)
    - abstract: Abstract and artistic (Creative, Art, Conceptual)
    - minimal: Clean, minimalist (Tech, Startup, Modern presentations)
    - photo: High-quality photography (Marketing, Advertising, Products)
    """
    logger.debug("Fetching image styles")
    return await image_service.get_styles()


@router.get("/image/credits/{presentation_id}")
async def get_image_credits(presentation_id: str):
    """
    Get image credits for a presentation.

    Returns:
    - used: Number of credits used
    - remaining: Number of credits remaining
    - total: Total credits available
    - qualityCosts: Credit cost per quality tier

    Credit costs by quality:
    - draft (512px): 1 credit
    - standard (1024px): 2 credits
    - high (1536px): 4 credits
    - ultra (2048px): 8 credits
    """
    logger.debug(f"Fetching image credits for presentation {presentation_id}")
    return await image_service.get_credits(presentation_id)


@router.post("/image/clear-cache")
async def clear_image_cache():
    """
    Clear cached image styles.

    This forces the next request for styles to fetch fresh data
    from the Image AI Service.
    """
    image_service.clear_cache()
    return {"success": True, "message": "Image service cache cleared"}
