"""
Table Generation Router

Handles table generation requests from the frontend, coordinates with the
Table AI Service, and returns HTML table content.

After successful generation, content is directly injected into Layout Service.

Endpoints:
    POST /table - Generate table content
    POST /table/transform - Transform existing table
    POST /table/analyze - Analyze table data
    GET /table/presets - Get available table presets
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter

from models import (
    TableGenerateRequest,
    TableGenerateResponse,
    TableTransformRequest,
    TableTransformResponse,
    TableAnalyzeRequest,
    TableAnalyzeResponse,
    ErrorDetail
)
from services.table_service import TableService
from services.layout_service import layout_service
from utils.grid_utils import convert_grid_position

logger = logging.getLogger(__name__)

router = APIRouter()
table_service = TableService()


@router.post("/table", response_model=TableGenerateResponse)
async def generate_table(request: TableGenerateRequest):
    """
    Generate a table using the Table AI Service.

    This endpoint:
    1. Converts Layout Service grid position to Table AI dimensions
    2. Calls the Table AI Service to generate the table
    3. Returns HTML table content ready for rendering

    The frontend should then send the html_content to the Layout Service
    iframe via postMessage to render the table element.
    """
    logger.info(f"Table generation request: element={request.element_id}, preset={request.preset.value}")

    # Convert grid position to dimensions
    grid_dims = convert_grid_position(request.position)
    logger.debug(f"Grid conversion: position={request.position} -> dims={grid_dims}")

    # Build context for Table AI
    context = {
        "presentationTitle": request.context.presentation_title,
        "slideTitle": request.context.slide_title,
        "slideIndex": request.context.slide_index
    }

    if request.context.industry:
        context["industry"] = request.context.industry

    # Call Table AI Service
    result = await table_service.generate(
        prompt=request.prompt,
        presentation_id=request.context.presentation_id,
        slide_id=request.context.slide_id,
        element_id=request.element_id,
        context=context,
        constraints={
            "gridWidth": grid_dims["width"],
            "gridHeight": grid_dims["height"]
        },
        preset=request.preset.value,
        columns=request.columns,
        rows=request.rows,
        has_header=request.has_header,
        data=request.data
    )

    # Handle error response
    if not result.get("success", False):
        error_info = result.get("error", {})
        return TableGenerateResponse(
            success=False,
            element_id=request.element_id,
            error=ErrorDetail(
                code=error_info.get("code", "UNKNOWN_ERROR"),
                message=error_info.get("message", "Table generation failed"),
                retryable=error_info.get("retryable", False),
                suggestion=error_info.get("suggestion")
            )
        )

    # Extract data from response
    data = result.get("data", {})

    logger.info(f"Table generated successfully: element={request.element_id}")

    # Inject content into Layout Service
    injected = None
    injection_error = None

    html_content = data.get("htmlContent") or data.get("html_content") or result.get("htmlContent")
    if html_content:
        injection_result = await layout_service.inject_table(
            presentation_id=request.context.presentation_id,
            slide_index=request.context.slide_index,
            element_id=request.element_id,
            html_content=html_content
        )
        injected = injection_result.get("success", False)
        if not injected:
            injection_error = injection_result.get("error", "Unknown injection error")
            logger.warning(f"Table injection failed: {injection_error}")
        else:
            logger.info(f"Table injected into Layout Service: element={request.element_id}")

    return TableGenerateResponse(
        success=True,
        element_id=request.element_id,
        html_content=html_content,
        columns=data.get("columns") or result.get("columns"),
        rows=data.get("rows") or result.get("rows"),
        preset_applied=request.preset.value,
        injected=injected,
        injection_error=injection_error
    )


@router.post("/table/transform", response_model=TableTransformResponse)
async def transform_table(request: TableTransformRequest):
    """
    Transform existing table content.

    Transformations available:
    - add_column: Add a new column (options.content, options.position)
    - add_row: Add a new row (options.content, options.position)
    - remove_column: Remove a column (options.column_index)
    - remove_row: Remove a row (options.row_index)
    - sort: Sort by column (options.sort_column, options.sort_direction)
    - summarize: Add summary row (options.summarize_type, options.summarize_columns)
    - transpose: Swap rows and columns
    - expand: Expand content (options.focus_area)
    - merge_cells: Merge cells (options.cells)
    - split_column: Split a column (options.column_index, options.split_count)
    """
    logger.info(f"Table transform request: element={request.element_id}, transformation={request.transformation.value}")

    # Convert grid position to dimensions
    grid_dims = convert_grid_position(request.position)

    # Build context
    context = {
        "presentationTitle": request.context.presentation_title,
        "slideTitle": request.context.slide_title,
        "slideIndex": request.context.slide_index
    }

    # Build options dict from request
    options = None
    if request.options:
        options = {}
        if request.options.content is not None:
            options["content"] = request.options.content
        if request.options.position is not None:
            options["position"] = request.options.position
        if request.options.column_index is not None:
            options["columnIndex"] = request.options.column_index
        if request.options.row_index is not None:
            options["rowIndex"] = request.options.row_index
        if request.options.sort_column is not None:
            options["sortColumn"] = request.options.sort_column
        if request.options.sort_direction:
            options["sortDirection"] = request.options.sort_direction.value
        if request.options.summarize_type:
            options["summarizeType"] = request.options.summarize_type.value
        if request.options.summarize_columns:
            options["summarizeColumns"] = request.options.summarize_columns
        if request.options.focus_area:
            options["focusArea"] = request.options.focus_area
        if request.options.cells:
            options["cells"] = request.options.cells
        if request.options.split_count is not None:
            options["splitCount"] = request.options.split_count

    # Call Table AI Service
    result = await table_service.transform(
        source_content=request.source_content,
        transformation=request.transformation.value,
        presentation_id=request.context.presentation_id,
        slide_id=request.context.slide_id,
        element_id=request.element_id,
        context=context,
        constraints={
            "gridWidth": grid_dims["width"],
            "gridHeight": grid_dims["height"]
        },
        options=options
    )

    # Handle error response
    if not result.get("success", False):
        error_info = result.get("error", {})
        return TableTransformResponse(
            success=False,
            element_id=request.element_id,
            error=ErrorDetail(
                code=error_info.get("code", "UNKNOWN_ERROR"),
                message=error_info.get("message", "Table transformation failed"),
                retryable=error_info.get("retryable", False),
                suggestion=error_info.get("suggestion")
            )
        )

    data = result.get("data", {})

    logger.info(f"Table transformed successfully: element={request.element_id}")

    # Inject content into Layout Service
    injected = None
    injection_error = None

    html_content = data.get("htmlContent") or data.get("html_content") or result.get("htmlContent")
    if html_content:
        injection_result = await layout_service.inject_table(
            presentation_id=request.context.presentation_id,
            slide_index=request.context.slide_index,
            element_id=request.element_id,
            html_content=html_content
        )
        injected = injection_result.get("success", False)
        if not injected:
            injection_error = injection_result.get("error", "Unknown injection error")
            logger.warning(f"Table transform injection failed: {injection_error}")
        else:
            logger.info(f"Transformed table injected into Layout Service: element={request.element_id}")

    return TableTransformResponse(
        success=True,
        element_id=request.element_id,
        html_content=html_content,
        transformation_applied=request.transformation.value,
        columns=data.get("columns") or result.get("columns"),
        rows=data.get("rows") or result.get("rows"),
        injected=injected,
        injection_error=injection_error
    )


@router.post("/table/analyze", response_model=TableAnalyzeResponse)
async def analyze_table(request: TableAnalyzeRequest):
    """
    Analyze table data and return insights.

    Analysis types:
    - summary: General summary of the table
    - trends: Identify patterns and trends
    - statistics: Statistical analysis
    """
    logger.info(f"Table analyze request: element={request.element_id}, type={request.analysis_type}")

    # Build context
    context = {
        "presentationTitle": request.context.presentation_title,
        "slideTitle": request.context.slide_title,
        "slideIndex": request.context.slide_index
    }

    # Call Table AI Service
    result = await table_service.analyze(
        source_content=request.source_content,
        element_id=request.element_id,
        context=context,
        analysis_type=request.analysis_type or "summary"
    )

    # Handle error response
    if not result.get("success", False):
        error_info = result.get("error", {})
        return TableAnalyzeResponse(
            success=False,
            element_id=request.element_id,
            error=ErrorDetail(
                code=error_info.get("code", "UNKNOWN_ERROR"),
                message=error_info.get("message", "Table analysis failed"),
                retryable=error_info.get("retryable", False),
                suggestion=error_info.get("suggestion")
            )
        )

    data = result.get("data", {})

    logger.info(f"Table analyzed successfully: element={request.element_id}")

    return TableAnalyzeResponse(
        success=True,
        element_id=request.element_id,
        summary=data.get("summary") or result.get("summary"),
        statistics=data.get("statistics") or result.get("statistics"),
        trends=data.get("trends") or result.get("trends"),
        recommendations=data.get("recommendations") or result.get("recommendations")
    )


@router.get("/table/presets")
async def get_table_presets():
    """
    Get available table style presets.

    Returns an array of preset definitions, each containing:
    - name: Preset identifier
    - description: Description of the style

    Available presets:
    - minimal: Clean design with minimal borders
    - bordered: Full cell borders for clarity
    - striped: Alternating row colors for readability
    - modern: Contemporary design with subtle styling
    - professional: Corporate-appropriate styling
    - colorful: Vibrant colors for engagement
    """
    logger.debug("Fetching table presets")
    return table_service.get_presets()
