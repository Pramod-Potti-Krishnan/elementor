"""
Chart Generation Router

Handles chart generation requests from the frontend, coordinates with the
Chart AI Service, and returns Chart.js configurations ready for rendering.

After successful generation, content is directly injected into Layout Service.

Endpoints:
    POST /chart - Generate Chart.js configuration
    GET /chart/constraints - Get grid size constraints
    GET /chart/palettes - Get available color palettes
    POST /chart/validate - Validate chart request before generation
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from models import (
    ChartGenerateRequest,
    ChartGenerateResponse,
    ChartMetadata,
    ChartInsights,
    ErrorDetail
)
from services.chart_service import ChartService
from services.layout_service import layout_service
from utils.grid_utils import convert_grid_position, validate_minimum_size

logger = logging.getLogger(__name__)

router = APIRouter()
chart_service = ChartService()


@router.post("/chart", response_model=ChartGenerateResponse)
async def generate_chart(request: ChartGenerateRequest):
    """
    Generate a Chart.js configuration for a chart element.

    This endpoint:
    1. Validates the grid size meets minimum requirements
    2. Converts Layout Service grid position to Chart AI dimensions
    3. Calls the Chart AI Service to generate the chart
    4. Returns the Chart.js config ready for rendering

    The frontend should then send the chartConfig to the Layout Service
    iframe via postMessage to render the chart.
    """
    logger.info(f"Chart generation request: element={request.element_id}, type={request.chart_type.value}")

    # Validate minimum grid size
    validation = validate_minimum_size(request.position, request.chart_type.value)
    if not validation["valid"]:
        logger.warning(f"Grid size validation failed: {validation['message']}")
        return ChartGenerateResponse(
            success=False,
            element_id=request.element_id,
            error=ErrorDetail(
                code="GRID_TOO_SMALL",
                message=validation["message"],
                retryable=True,
                suggestion=f"Resize the chart element to at least {validation['min_width']}x{validation['min_height']} grid units."
            )
        )

    # Convert grid position to Chart AI dimensions
    grid_dims = convert_grid_position(request.position)
    logger.debug(f"Grid conversion: position={request.position} -> dims={grid_dims}")

    # Build context for Chart AI
    context = {
        "presentationTitle": request.context.presentation_title,
        "slideTitle": request.context.slide_title,
        "slideIndex": request.context.slide_index,
    }

    # Add optional context fields
    if request.context.industry:
        context["industry"] = request.context.industry
    if request.context.time_frame:
        context["timeFrame"] = request.context.time_frame

    # Build style options
    style = {
        "palette": request.palette.value,
        "showLegend": request.show_legend,
        "showDataLabels": request.show_data_labels
    }

    if request.legend_position:
        style["legendPosition"] = request.legend_position

    # Build axes config if provided
    axes = None
    if request.x_label or request.y_label or request.stacked:
        axes = {}
        if request.x_label:
            axes["xLabel"] = request.x_label
        if request.y_label:
            axes["yLabel"] = request.y_label
        if request.stacked:
            axes["stacked"] = request.stacked

    # Prepare data if provided
    data = None
    if request.data:
        data = [{"label": d.label, "value": d.value} for d in request.data]

    # Call Chart AI Service
    result = await chart_service.generate(
        prompt=request.prompt,
        chart_type=request.chart_type.value,
        presentation_id=request.context.presentation_id,
        slide_id=request.context.slide_id,
        element_id=request.element_id,
        context=context,
        constraints={
            "gridWidth": grid_dims["width"],
            "gridHeight": grid_dims["height"]
        },
        style=style,
        data=data,
        generate_data=request.generate_data,
        axes=axes
    )

    # Handle error response
    if not result.get("success", False):
        error_info = result.get("error", {})
        return ChartGenerateResponse(
            success=False,
            element_id=request.element_id,
            error=ErrorDetail(
                code=error_info.get("code", "UNKNOWN_ERROR"),
                message=error_info.get("message", "Chart generation failed"),
                retryable=error_info.get("retryable", False),
                suggestion=error_info.get("suggestion")
            )
        )

    # Extract chart data from response
    chart_data = result.get("data", {})

    # Build metadata
    metadata = None
    if chart_data.get("metadata"):
        meta = chart_data["metadata"]
        metadata = ChartMetadata(
            chart_type=meta.get("chartType", request.chart_type.value),
            data_point_count=meta.get("dataPointCount", 0),
            dataset_count=meta.get("datasetCount", 1),
            suggested_title=meta.get("suggestedTitle"),
            data_range=meta.get("dataRange")
        )

    # Build insights
    insights = None
    if chart_data.get("insights"):
        ins = chart_data["insights"]
        insights = ChartInsights(
            trend=ins.get("trend"),
            outliers=ins.get("outliers"),
            highlights=ins.get("highlights")
        )

    logger.info(f"Chart generated successfully: element={request.element_id}")

    # Inject content into Layout Service
    injected = None
    injection_error = None

    chart_config = chart_data.get("chartConfig")
    if chart_config:
        injection_result = await layout_service.inject_chart(
            presentation_id=request.context.presentation_id,
            slide_index=request.context.slide_index,
            element_id=request.element_id,
            chart_config=chart_config,
            chart_type=request.chart_type.value
        )
        injected = injection_result.get("success", False)
        if not injected:
            injection_error = injection_result.get("error", "Unknown injection error")
            logger.warning(f"Chart injection failed: {injection_error}")
        else:
            logger.info(f"Chart injected into Layout Service: element={request.element_id}")

    return ChartGenerateResponse(
        success=True,
        element_id=request.element_id,
        chart_config=chart_config,
        raw_data=chart_data.get("rawData"),
        metadata=metadata,
        insights=insights,
        generation_id=chart_data.get("generationId"),
        injected=injected,
        injection_error=injection_error
    )


@router.get("/chart/constraints")
async def get_chart_constraints():
    """
    Get grid size constraints and data limits for all chart types.

    Returns minimum grid sizes, data point limits by size category,
    valid grid ranges, and size threshold definitions.

    This information should be used by the frontend to:
    - Enforce minimum sizes when resizing chart elements
    - Show appropriate data entry limits based on element size
    - Display helpful error messages when constraints are violated
    """
    logger.debug("Fetching chart constraints")
    return await chart_service.get_constraints()


@router.get("/chart/palettes")
async def get_chart_palettes():
    """
    Get available color palettes for charts.

    Returns an array of palette definitions, each containing:
    - name: Palette identifier
    - colors: Array of hex color codes
    - colorCount: Number of colors in the palette

    The frontend should display these palettes for user selection
    when configuring a chart element.
    """
    logger.debug("Fetching chart palettes")
    return await chart_service.get_palettes()


@router.post("/chart/validate")
async def validate_chart_request(request: ChartGenerateRequest) -> Dict[str, Any]:
    """
    Validate a chart generation request without actually generating.

    This is useful for the frontend to check if a request is valid
    before showing a loading state or making the full generation call.

    Returns validation status and any error details.
    """
    logger.debug(f"Validating chart request: element={request.element_id}")

    # Validate minimum grid size
    validation = validate_minimum_size(request.position, request.chart_type.value)

    if not validation["valid"]:
        return {
            "valid": False,
            "error": {
                "code": "GRID_TOO_SMALL",
                "message": validation["message"],
                "suggestion": f"Resize to at least {validation['min_width']}x{validation['min_height']} grid units."
            }
        }

    # Check data requirements
    if not request.data and not request.generate_data:
        return {
            "valid": False,
            "error": {
                "code": "MISSING_DATA",
                "message": "Either provide data or set generate_data=true",
                "suggestion": "Add data points or enable synthetic data generation."
            }
        }

    grid_dims = convert_grid_position(request.position)

    return {
        "valid": True,
        "grid_dimensions": grid_dims,
        "chart_type": request.chart_type.value,
        "palette": request.palette.value,
        "has_data": request.data is not None and len(request.data) > 0,
        "generate_data": request.generate_data
    }


@router.post("/chart/clear-cache")
async def clear_chart_cache():
    """
    Clear cached constraints and palettes.

    This forces the next request for constraints or palettes to
    fetch fresh data from the Chart AI Service.
    """
    chart_service.clear_cache()
    return {"success": True, "message": "Chart service cache cleared"}
