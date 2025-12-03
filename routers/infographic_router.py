"""
Infographic Generation Router

Handles infographic generation requests from the frontend, coordinates with the
Infographic AI Service (Illustrator), and returns HTML/SVG content.

After successful generation, content is directly injected into Layout Service.

Endpoints:
    POST /infographic - Generate infographic
    GET /infographic/types - Get supported infographic types
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter

from models import (
    InfographicGenerateRequest,
    InfographicGenerateResponse,
    InfographicGeneratorType,
    ErrorDetail
)
from services.infographic_service import InfographicService
from services.layout_service import layout_service
from utils.grid_utils import convert_grid_position

logger = logging.getLogger(__name__)

router = APIRouter()
infographic_service = InfographicService()

# Minimum grid sizes per infographic type (in AI grid units)
INFOGRAPHIC_MIN_SIZES = {
    # Template-based (HTML)
    "pyramid": {"width": 6, "height": 4},
    "funnel": {"width": 6, "height": 4},
    "concentric_circles": {"width": 6, "height": 6},
    "concept_spread": {"width": 8, "height": 4},
    "venn": {"width": 6, "height": 4},
    "comparison": {"width": 8, "height": 4},
    # Dynamic SVG
    "timeline": {"width": 8, "height": 3},
    "process": {"width": 6, "height": 3},
    "statistics": {"width": 4, "height": 3},
    "hierarchy": {"width": 6, "height": 4},
    "list": {"width": 4, "height": 4},
    "cycle": {"width": 6, "height": 6},
    "matrix": {"width": 6, "height": 6},
    "roadmap": {"width": 8, "height": 4},
}


def validate_infographic_size(position, infographic_type: str) -> Dict[str, Any]:
    """Validate minimum grid size for infographic type."""
    dims = convert_grid_position(position)
    min_size = INFOGRAPHIC_MIN_SIZES.get(infographic_type, {"width": 6, "height": 4})

    if dims["width"] < min_size["width"] or dims["height"] < min_size["height"]:
        return {
            "valid": False,
            "current_width": dims["width"],
            "current_height": dims["height"],
            "min_width": min_size["width"],
            "min_height": min_size["height"],
            "message": f"Grid size {dims['width']}x{dims['height']} is too small for {infographic_type} infographic. Minimum size is {min_size['width']}x{min_size['height']}."
        }

    return {"valid": True, "width": dims["width"], "height": dims["height"]}


@router.post("/infographic", response_model=InfographicGenerateResponse)
async def generate_infographic(request: InfographicGenerateRequest):
    """
    Generate an infographic using the Illustrator AI Service.

    This endpoint:
    1. Validates the grid size meets minimum requirements
    2. Converts Layout Service grid position to Infographic AI dimensions
    3. Calls the Illustrator AI Service to generate the infographic
    4. Returns HTML or SVG content ready for rendering

    Infographic types are divided into two categories:

    Template-based (HTML, 6 types):
    - pyramid: Hierarchical pyramid visualization
    - funnel: Funnel conversion flow
    - concentric_circles: Nested circles for layered concepts
    - concept_spread: Spread layout for related concepts
    - venn: Overlapping circles for relationships
    - comparison: Side-by-side comparison

    Dynamic SVG (Gemini 2.5 Pro, 8 types):
    - timeline: Chronological events
    - process: Step-by-step flow
    - statistics: Key metrics
    - hierarchy: Organizational tree
    - list: Styled list with icons
    - cycle: Circular cycle diagram
    - matrix: 2x2 or 3x3 matrix
    - roadmap: Project/product roadmap
    """
    logger.info(f"Infographic generation request: element={request.element_id}, type={request.infographic_type.value}")

    # Validate minimum grid size
    validation = validate_infographic_size(request.position, request.infographic_type.value)
    if not validation["valid"]:
        logger.warning(f"Grid size validation failed: {validation['message']}")
        return InfographicGenerateResponse(
            success=False,
            element_id=request.element_id,
            error=ErrorDetail(
                code="GRID_TOO_SMALL",
                message=validation["message"],
                retryable=True,
                suggestion=f"Resize the infographic element to at least {validation['min_width']}x{validation['min_height']} grid units."
            )
        )

    # Convert grid position to dimensions
    grid_dims = convert_grid_position(request.position)
    logger.debug(f"Grid conversion: position={request.position} -> dims={grid_dims}")

    # Build context for Infographic AI
    context = {
        "presentationTitle": request.context.presentation_title,
        "slideTitle": request.context.slide_title,
        "slideIndex": request.context.slide_index
    }

    if request.context.industry:
        context["industry"] = request.context.industry

    # Call Infographic AI Service
    result = await infographic_service.generate(
        prompt=request.prompt,
        infographic_type=request.infographic_type.value,
        presentation_id=request.context.presentation_id,
        slide_id=request.context.slide_id,
        element_id=request.element_id,
        context=context,
        constraints={
            "gridWidth": grid_dims["width"],
            "gridHeight": grid_dims["height"]
        },
        color_scheme=request.color_scheme.value,
        icon_style=request.icon_style.value,
        item_count=request.item_count,
        items=request.items,
        generate_data=request.generate_data
    )

    # Handle error response
    if not result.get("success", False):
        error_info = result.get("error", {})
        return InfographicGenerateResponse(
            success=False,
            element_id=request.element_id,
            error=ErrorDetail(
                code=error_info.get("code", "UNKNOWN_ERROR"),
                message=error_info.get("message", "Infographic generation failed"),
                retryable=error_info.get("retryable", False),
                suggestion=error_info.get("suggestion")
            )
        )

    # Extract data from response
    data = result.get("data", {})

    # Determine generator type based on infographic type
    template_types = {"pyramid", "funnel", "concentric_circles", "concept_spread", "venn", "comparison"}
    generator_type = InfographicGeneratorType.TEMPLATE if request.infographic_type.value in template_types else InfographicGeneratorType.SVG

    logger.info(f"Infographic generated successfully: element={request.element_id}")

    # Inject content into Layout Service
    injected = None
    injection_error = None

    html_content = data.get("htmlContent") or data.get("html_content") or result.get("htmlContent")
    svg_content = data.get("svgContent") or data.get("svg_content") or result.get("svgContent")

    if html_content or svg_content:
        injection_result = await layout_service.inject_infographic(
            presentation_id=request.context.presentation_id,
            slide_index=request.context.slide_index,
            element_id=request.element_id,
            svg_content=svg_content,
            html_content=html_content,
            infographic_type=request.infographic_type.value
        )
        injected = injection_result.get("success", False)
        if not injected:
            injection_error = injection_result.get("error", "Unknown injection error")
            logger.warning(f"Infographic injection failed: {injection_error}")
        else:
            logger.info(f"Infographic injected into Layout Service: element={request.element_id}")

    return InfographicGenerateResponse(
        success=True,
        element_id=request.element_id,
        html_content=html_content,
        svg_content=svg_content,
        generator_type=generator_type,
        infographic_type=request.infographic_type.value,
        item_count=data.get("itemCount") or data.get("item_count") or result.get("itemCount"),
        color_scheme_applied=request.color_scheme.value,
        injected=injected,
        injection_error=injection_error
    )


@router.get("/infographic/types")
async def get_infographic_types():
    """
    Get supported infographic types with their constraints.

    Returns an array of type definitions, each containing:
    - type: Type identifier
    - name: Human-readable name
    - description: Description of use case
    - generator: "template" (HTML) or "svg" (dynamic)
    - minGridWidth/minGridHeight: Minimum grid dimensions
    - minItems/maxItems: Item count constraints
    - supportsIcons: Whether icons can be used

    Also includes available color schemes and icon styles.
    """
    logger.debug("Fetching infographic types")
    return await infographic_service.get_types()


@router.post("/infographic/clear-cache")
async def clear_infographic_cache():
    """
    Clear cached infographic types.

    This forces the next request for types to fetch fresh data
    from the Infographic AI Service.
    """
    infographic_service.clear_cache()
    return {"success": True, "message": "Infographic service cache cleared"}
