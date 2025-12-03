"""
Diagram Generation Router

Handles diagram generation requests from the frontend, coordinates with the
Diagram AI Service using async polling, and returns SVG/Mermaid content.

After successful generation, content is directly injected into Layout Service.

Endpoints:
    POST /diagram - Submit diagram generation (async polling)
    GET /diagram/status/{job_id} - Poll job status
    GET /diagram/types - Get supported diagram types
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter

from models import (
    DiagramGenerateRequest,
    DiagramGenerateResponse,
    DiagramStatusResponse,
    DiagramJobStatus,
    ErrorDetail
)
from services.diagram_service import DiagramService
from services.layout_service import layout_service
from utils.grid_utils import convert_grid_position

logger = logging.getLogger(__name__)

router = APIRouter()
diagram_service = DiagramService()

# Minimum grid sizes per diagram type (in Chart AI grid units)
DIAGRAM_MIN_SIZES = {
    "flowchart": {"width": 3, "height": 2},
    "sequence": {"width": 4, "height": 3},
    "class": {"width": 4, "height": 3},
    "state": {"width": 3, "height": 3},
    "er": {"width": 4, "height": 3},
    "gantt": {"width": 6, "height": 2},
    "userjourney": {"width": 4, "height": 2},
    "gitgraph": {"width": 4, "height": 2},
    "mindmap": {"width": 4, "height": 4},
    "pie": {"width": 3, "height": 3},
    "timeline": {"width": 5, "height": 2},
}


def validate_diagram_size(position, diagram_type: str) -> Dict[str, Any]:
    """Validate minimum grid size for diagram type."""
    dims = convert_grid_position(position)
    min_size = DIAGRAM_MIN_SIZES.get(diagram_type, {"width": 3, "height": 3})

    if dims["width"] < min_size["width"] or dims["height"] < min_size["height"]:
        return {
            "valid": False,
            "current_width": dims["width"],
            "current_height": dims["height"],
            "min_width": min_size["width"],
            "min_height": min_size["height"],
            "message": f"Grid size {dims['width']}x{dims['height']} is too small for {diagram_type} diagram. Minimum size is {min_size['width']}x{min_size['height']}."
        }

    return {"valid": True, "width": dims["width"], "height": dims["height"]}


@router.post("/diagram", response_model=DiagramGenerateResponse)
async def generate_diagram(request: DiagramGenerateRequest):
    """
    Generate a diagram using the Diagram AI Service.

    This endpoint:
    1. Validates the grid size meets minimum requirements
    2. Converts Layout Service grid position to Diagram AI dimensions
    3. Calls the Diagram AI Service with automatic polling
    4. Returns the Mermaid code and SVG content

    The frontend should then send the svg_content to the Layout Service
    iframe via postMessage to render the diagram.
    """
    logger.info(f"Diagram generation request: element={request.element_id}, type={request.diagram_type.value}")

    # Validate minimum grid size
    validation = validate_diagram_size(request.position, request.diagram_type.value)
    if not validation["valid"]:
        logger.warning(f"Grid size validation failed: {validation['message']}")
        return DiagramGenerateResponse(
            success=False,
            element_id=request.element_id,
            error=ErrorDetail(
                code="GRID_TOO_SMALL",
                message=validation["message"],
                retryable=True,
                suggestion=f"Resize the diagram element to at least {validation['min_width']}x{validation['min_height']} grid units."
            )
        )

    # Convert grid position to dimensions
    grid_dims = convert_grid_position(request.position)
    logger.debug(f"Grid conversion: position={request.position} -> dims={grid_dims}")

    # Build context for Diagram AI
    context = {
        "presentationTitle": request.context.presentation_title,
        "slideTitle": request.context.slide_title,
        "slideIndex": request.context.slide_index
    }

    if request.context.industry:
        context["industry"] = request.context.industry

    # Call Diagram AI Service with polling
    result = await diagram_service.generate_with_polling(
        prompt=request.prompt,
        diagram_type=request.diagram_type.value,
        presentation_id=request.context.presentation_id,
        slide_id=request.context.slide_id,
        element_id=request.element_id,
        context=context,
        constraints={
            "gridWidth": grid_dims["width"],
            "gridHeight": grid_dims["height"]
        },
        direction=request.direction.value,
        theme=request.theme.value,
        complexity=request.complexity.value,
        mermaid_code=request.mermaid_code
    )

    # Handle error response
    if not result.get("success", False):
        error_info = result.get("error", {})
        return DiagramGenerateResponse(
            success=False,
            element_id=request.element_id,
            job_id=result.get("job_id"),
            error=ErrorDetail(
                code=error_info.get("code", "UNKNOWN_ERROR"),
                message=error_info.get("message", "Diagram generation failed"),
                retryable=error_info.get("retryable", False),
                suggestion=error_info.get("suggestion")
            )
        )

    logger.info(f"Diagram generated successfully: element={request.element_id}")

    # Inject content into Layout Service
    injected = None
    injection_error = None

    svg_content = result.get("svg_content")
    mermaid_code = result.get("mermaid_code")
    if svg_content or mermaid_code:
        injection_result = await layout_service.inject_diagram(
            presentation_id=request.context.presentation_id,
            slide_index=request.context.slide_index,
            element_id=request.element_id,
            svg_content=svg_content,
            mermaid_code=mermaid_code,
            diagram_type=request.diagram_type.value
        )
        injected = injection_result.get("success", False)
        if not injected:
            injection_error = injection_result.get("error", "Unknown injection error")
            logger.warning(f"Diagram injection failed: {injection_error}")
        else:
            logger.info(f"Diagram injected into Layout Service: element={request.element_id}")

    return DiagramGenerateResponse(
        success=True,
        element_id=request.element_id,
        job_id=result.get("job_id"),
        mermaid_code=mermaid_code,
        svg_content=svg_content,
        diagram_type=result.get("diagram_type", request.diagram_type.value),
        injected=injected,
        injection_error=injection_error
    )


@router.get("/diagram/status/{job_id}", response_model=DiagramStatusResponse)
async def get_diagram_status(job_id: str):
    """
    Poll the status of a diagram generation job.

    This endpoint is used when the frontend needs to manually poll
    instead of waiting for the automatic polling in POST /diagram.

    Returns:
        - status: pending, processing, completed, failed
        - progress: 0-100 (if available)
        - mermaid_code: Mermaid syntax (if completed)
        - svg_content: SVG markup (if completed)
        - error: Error message (if failed)
    """
    logger.debug(f"Polling diagram status: job_id={job_id}")

    result = await diagram_service.poll_status(job_id)

    status_map = {
        "pending": DiagramJobStatus.PENDING,
        "processing": DiagramJobStatus.PROCESSING,
        "completed": DiagramJobStatus.COMPLETED,
        "failed": DiagramJobStatus.FAILED
    }

    return DiagramStatusResponse(
        job_id=job_id,
        status=status_map.get(result.get("status", "failed"), DiagramJobStatus.FAILED),
        progress=result.get("progress"),
        mermaid_code=result.get("mermaidCode"),
        svg_content=result.get("svgContent"),
        error=result.get("error")
    )


@router.get("/diagram/types")
async def get_diagram_types():
    """
    Get supported diagram types with their constraints.

    Returns an array of diagram type definitions, each containing:
    - type: Diagram type identifier
    - name: Human-readable name
    - description: Description of use case
    - minGridWidth/minGridHeight: Minimum grid dimensions
    - supportsDirection: Whether layout direction can be configured

    The frontend should display these types for user selection
    when configuring a diagram element.
    """
    logger.debug("Fetching diagram types")
    return await diagram_service.get_types()


@router.post("/diagram/clear-cache")
async def clear_diagram_cache():
    """
    Clear cached diagram types.

    This forces the next request for types to fetch fresh data
    from the Diagram AI Service.
    """
    diagram_service.clear_cache()
    return {"success": True, "message": "Diagram service cache cleared"}
