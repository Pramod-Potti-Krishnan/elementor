"""
Text Generation Router

Handles text generation requests from the frontend, coordinates with the
Text AI Service, and returns HTML content for text elements.

After successful generation, content is directly injected into Layout Service.

Endpoints:
    POST /text - Generate text content
    POST /text/transform - Transform existing text
    POST /text/autofit - Auto-fit text to container
    GET /text/constraints/{width}/{height} - Get text constraints
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter

from models import (
    TextGenerateRequest,
    TextGenerateResponse,
    TextTransformRequest,
    TextTransformResponse,
    TextAutofitRequest,
    TextAutofitResponse,
    ErrorDetail
)
from services.text_service import TextService
from services.layout_service import layout_service
from utils.grid_utils import convert_grid_position

logger = logging.getLogger(__name__)

router = APIRouter()
text_service = TextService()


@router.post("/text", response_model=TextGenerateResponse)
async def generate_text(request: TextGenerateRequest):
    """
    Generate text content using the Text AI Service.

    This endpoint:
    1. Converts Layout Service grid position to Text AI dimensions
    2. Calls the Text AI Service to generate content
    3. Returns HTML content ready for rendering

    The frontend should then send the html_content to the Layout Service
    iframe via postMessage to render the text element.
    """
    logger.info(f"Text generation request: element={request.element_id}, tone={request.tone.value}")

    # Convert grid position to dimensions
    grid_dims = convert_grid_position(request.position)
    logger.debug(f"Grid conversion: position={request.position} -> dims={grid_dims}")

    # Build context for Text AI
    context = {
        "presentationTitle": request.context.presentation_title,
        "slideTitle": request.context.slide_title,
        "slideIndex": request.context.slide_index
    }

    if request.context.industry:
        context["industry"] = request.context.industry

    # Call Text AI Service
    result = await text_service.generate(
        prompt=request.prompt,
        presentation_id=request.context.presentation_id,
        slide_id=request.context.slide_id,
        element_id=request.element_id,
        context=context,
        constraints={
            "gridWidth": grid_dims["width"],
            "gridHeight": grid_dims["height"]
        },
        tone=request.tone.value,
        format=request.format.value,
        max_words=request.max_words,
        language=request.language or "en"
    )

    # Handle error response
    if not result.get("success", False):
        error_info = result.get("error", {})
        return TextGenerateResponse(
            success=False,
            element_id=request.element_id,
            error=ErrorDetail(
                code=error_info.get("code", "UNKNOWN_ERROR"),
                message=error_info.get("message", "Text generation failed"),
                retryable=error_info.get("retryable", False),
                suggestion=error_info.get("suggestion")
            )
        )

    # Extract data from response
    data = result.get("data", {})

    logger.info(f"Text generated successfully: element={request.element_id}")

    # Inject content into Layout Service
    injected = None
    injection_error = None

    html_content = data.get("htmlContent") or data.get("html_content") or result.get("htmlContent")
    if html_content:
        injection_result = await layout_service.inject_text(
            presentation_id=request.context.presentation_id,
            slide_index=request.context.slide_index,
            element_id=request.element_id,
            html_content=html_content
        )
        injected = injection_result.get("success", False)
        if not injected:
            injection_error = injection_result.get("error", "Unknown injection error")
            logger.warning(f"Text injection failed: {injection_error}")
        else:
            logger.info(f"Text injected into Layout Service: element={request.element_id}")

    return TextGenerateResponse(
        success=True,
        element_id=request.element_id,
        html_content=html_content,
        plain_text=data.get("plainText") or data.get("plain_text"),
        word_count=data.get("wordCount") or data.get("word_count"),
        character_count=data.get("characterCount") or data.get("character_count"),
        injected=injected,
        injection_error=injection_error
    )


@router.post("/text/transform", response_model=TextTransformResponse)
async def transform_text(request: TextTransformRequest):
    """
    Transform existing text content.

    Transformations available:
    - expand: Increase length
    - condense: Reduce length
    - simplify: Simpler language
    - formalize: Professional tone
    - casualize: Casual tone
    - bulletize: Convert to bullets
    - paragraphize: Convert to paragraphs
    - rephrase: Alternative wording
    - proofread: Fix grammar
    - translate: Change language (requires target_language)
    """
    logger.info(f"Text transform request: element={request.element_id}, transformation={request.transformation.value}")

    # Convert grid position to dimensions
    grid_dims = convert_grid_position(request.position)

    # Build context
    context = {
        "presentationTitle": request.context.presentation_title,
        "slideTitle": request.context.slide_title,
        "slideIndex": request.context.slide_index
    }

    # Call Text AI Service
    result = await text_service.transform(
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
        target_language=request.target_language,
        intensity=request.intensity
    )

    # Handle error response
    if not result.get("success", False):
        error_info = result.get("error", {})
        return TextTransformResponse(
            success=False,
            element_id=request.element_id,
            error=ErrorDetail(
                code=error_info.get("code", "UNKNOWN_ERROR"),
                message=error_info.get("message", "Text transformation failed"),
                retryable=error_info.get("retryable", False),
                suggestion=error_info.get("suggestion")
            )
        )

    data = result.get("data", {})

    logger.info(f"Text transformed successfully: element={request.element_id}")

    # Inject content into Layout Service
    injected = None
    injection_error = None

    html_content = data.get("htmlContent") or data.get("html_content") or result.get("htmlContent")
    if html_content:
        injection_result = await layout_service.inject_text(
            presentation_id=request.context.presentation_id,
            slide_index=request.context.slide_index,
            element_id=request.element_id,
            html_content=html_content
        )
        injected = injection_result.get("success", False)
        if not injected:
            injection_error = injection_result.get("error", "Unknown injection error")
            logger.warning(f"Text transform injection failed: {injection_error}")
        else:
            logger.info(f"Transformed text injected into Layout Service: element={request.element_id}")

    return TextTransformResponse(
        success=True,
        element_id=request.element_id,
        html_content=html_content,
        transformation_applied=request.transformation.value,
        word_count=data.get("wordCount") or data.get("word_count"),
        injected=injected,
        injection_error=injection_error
    )


@router.post("/text/autofit", response_model=TextAutofitResponse)
async def autofit_text(request: TextAutofitRequest):
    """
    Auto-fit text content to container size.

    Adjusts the text length to fit within the specified grid dimensions
    while preserving the original structure if requested.
    """
    logger.info(f"Text autofit request: element={request.element_id}")

    # Convert grid position to dimensions
    grid_dims = convert_grid_position(request.position)

    # Build context
    context = {
        "presentationTitle": request.context.presentation_title,
        "slideTitle": request.context.slide_title,
        "slideIndex": request.context.slide_index
    }

    # Call Text AI Service
    result = await text_service.autofit(
        source_content=request.source_content,
        presentation_id=request.context.presentation_id,
        slide_id=request.context.slide_id,
        element_id=request.element_id,
        context=context,
        constraints={
            "gridWidth": grid_dims["width"],
            "gridHeight": grid_dims["height"]
        },
        target_characters=request.target_characters,
        preserve_structure=request.preserve_structure
    )

    # Handle error response
    if not result.get("success", False):
        error_info = result.get("error", {})
        return TextAutofitResponse(
            success=False,
            element_id=request.element_id,
            error=ErrorDetail(
                code=error_info.get("code", "UNKNOWN_ERROR"),
                message=error_info.get("message", "Text autofit failed"),
                retryable=error_info.get("retryable", False),
                suggestion=error_info.get("suggestion")
            )
        )

    data = result.get("data", {})

    logger.info(f"Text auto-fitted successfully: element={request.element_id}")

    # Inject content into Layout Service
    injected = None
    injection_error = None

    html_content = data.get("htmlContent") or data.get("html_content") or result.get("htmlContent")
    if html_content:
        injection_result = await layout_service.inject_text(
            presentation_id=request.context.presentation_id,
            slide_index=request.context.slide_index,
            element_id=request.element_id,
            html_content=html_content
        )
        injected = injection_result.get("success", False)
        if not injected:
            injection_error = injection_result.get("error", "Unknown injection error")
            logger.warning(f"Text autofit injection failed: {injection_error}")
        else:
            logger.info(f"Auto-fitted text injected into Layout Service: element={request.element_id}")

    return TextAutofitResponse(
        success=True,
        element_id=request.element_id,
        html_content=html_content,
        original_length=data.get("originalLength") or data.get("original_length"),
        fitted_length=data.get("fittedLength") or data.get("fitted_length"),
        reduction_percentage=data.get("reductionPercentage") or data.get("reduction_percentage"),
        injected=injected,
        injection_error=injection_error
    )


@router.get("/text/constraints/{width}/{height}")
async def get_text_constraints(width: int, height: int):
    """
    Get text constraints for a given grid size.

    Returns maximum characters, lines, recommended font size, and bullet limits
    based on the grid dimensions.

    Args:
        width: Grid width (1-12)
        height: Grid height (1-8)
    """
    logger.debug(f"Fetching text constraints for {width}x{height}")

    # Validate input ranges
    width = max(1, min(12, width))
    height = max(1, min(8, height))

    return await text_service.get_constraints(width, height)


@router.post("/text/clear-cache")
async def clear_text_cache():
    """
    Clear cached text constraints.

    This forces the next constraint request to fetch fresh data
    from the Text AI Service.
    """
    text_service.clear_cache()
    return {"success": True, "message": "Text service cache cleared"}
