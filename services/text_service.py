"""
Text AI Service Client

Handles communication with the Text Table Builder v1.2 Text endpoints.

Endpoints:
    - POST /api/ai/text/generate - Generate text content
    - POST /api/ai/text/transform - Transform existing text
    - POST /api/ai/text/autofit - Auto-fit text to container
    - GET /api/ai/constraints/{width}/{height} - Get text constraints
"""

import logging
from typing import Any, Dict, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)


class TextService:
    """
    Client for the Text AI Service.

    Features:
        - Async HTTP calls with configurable timeout
        - Response caching for constraints
        - Support for text generation, transformation, and auto-fit
        - Error handling with retryable status
    """

    def __init__(self):
        self.base_url = settings.TEXT_TABLE_SERVICE_URL
        self.timeout = settings.SERVICE_TIMEOUT
        self._constraints_cache: Dict[str, Dict[str, Any]] = {}

    async def generate(
        self,
        prompt: str,
        presentation_id: str,
        slide_id: str,
        element_id: str,
        context: Dict[str, Any],
        constraints: Dict[str, int],
        tone: str = "professional",
        format: str = "paragraph",
        max_words: Optional[int] = None,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Generate text content via Text AI Service.

        Args:
            prompt: Description of the text content
            presentation_id: Presentation identifier
            slide_id: Slide identifier
            element_id: Element identifier
            context: Presentation context (title, slide info)
            constraints: Grid dimensions (gridWidth, gridHeight)
            tone: Text tone (professional, conversational, academic, etc.)
            format: Output format (paragraph, bullets, numbered, etc.)
            max_words: Maximum word count
            language: ISO language code (default "en")

        Returns:
            Dict with success status and either html_content or error details
        """
        # Build context object matching backend SlideContext schema
        # Required fields: presentationTitle, slideIndex, slideCount
        backend_context = {
            "presentationTitle": context.get("presentationTitle", "Untitled"),
            "slideIndex": context.get("slideIndex", 0),
            "slideCount": context.get("slideCount", 1),
        }
        # Optional context fields
        if context.get("presentationTheme"):
            backend_context["presentationTheme"] = context["presentationTheme"]
        if context.get("slideTitle"):
            backend_context["slideTitle"] = context["slideTitle"]

        # Build options object matching backend TextOptions schema
        options = {
            "tone": tone,
            "format": format,
            "language": language
        }

        request_body = {
            "prompt": prompt,
            "presentationId": presentation_id,
            "slideId": slide_id,
            "elementId": element_id,
            "context": backend_context,
            "constraints": constraints,
            "options": options
        }

        logger.info(f"Generating text: tone={tone}, format={format}, element={element_id}")
        logger.debug(f"Request body: {request_body}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/ai/text/generate",
                    json=request_body
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"Text generated successfully: {element_id}")
                return result

        except httpx.TimeoutException:
            logger.error(f"Text service timeout for element {element_id}")
            return {
                "success": False,
                "error": {
                    "code": "TIMEOUT",
                    "message": "Text generation timed out. Please try again.",
                    "retryable": True
                }
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"Text service HTTP error: {e.response.status_code}")
            try:
                error_data = e.response.json()
                return {
                    "success": False,
                    "error": error_data.get("error", {
                        "code": f"HTTP_{e.response.status_code}",
                        "message": str(e),
                        "retryable": e.response.status_code >= 500
                    })
                }
            except Exception:
                return {
                    "success": False,
                    "error": {
                        "code": f"HTTP_{e.response.status_code}",
                        "message": f"Text service returned status {e.response.status_code}",
                        "retryable": e.response.status_code >= 500
                    }
                }

        except httpx.ConnectError:
            logger.error(f"Failed to connect to Text service at {self.base_url}")
            return {
                "success": False,
                "error": {
                    "code": "CONNECTION_ERROR",
                    "message": "Unable to connect to Text AI service. Please try again later.",
                    "retryable": True
                }
            }

        except Exception as e:
            logger.exception(f"Unexpected error in text generation: {e}")
            return {
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e),
                    "retryable": False
                }
            }

    async def transform(
        self,
        source_content: str,
        transformation: str,
        presentation_id: str,
        slide_id: str,
        element_id: str,
        context: Dict[str, Any],
        constraints: Dict[str, int],
        target_language: Optional[str] = None,
        intensity: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Transform existing text content.

        Args:
            source_content: HTML content to transform
            transformation: Type of transformation (expand, condense, simplify, etc.)
            presentation_id: Presentation identifier
            slide_id: Slide identifier
            element_id: Element identifier
            context: Presentation context
            constraints: Grid dimensions
            target_language: Target language for translate transformation
            intensity: Transformation intensity (0.0-1.0)

        Returns:
            Dict with success status and transformed html_content or error
        """
        # Build context object matching backend SlideContext schema
        backend_context = {
            "presentationTitle": context.get("presentationTitle", "Untitled"),
            "slideIndex": context.get("slideIndex", 0),
            "slideCount": context.get("slideCount", 1),
        }
        if context.get("presentationTheme"):
            backend_context["presentationTheme"] = context["presentationTheme"]
        if context.get("slideTitle"):
            backend_context["slideTitle"] = context["slideTitle"]

        # Build options if target_language or intensity provided
        options = {}
        if target_language:
            options["targetLanguage"] = target_language
        if intensity is not None:
            options["intensity"] = intensity

        request_body = {
            "sourceContent": source_content,
            "transformation": transformation,
            "presentationId": presentation_id,
            "slideId": slide_id,
            "elementId": element_id,
            "context": backend_context,
            "constraints": constraints
        }

        if options:
            request_body["options"] = options

        logger.info(f"Transforming text: transformation={transformation}, element={element_id}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/ai/text/transform",
                    json=request_body
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"Text transformed successfully: {element_id}")
                return result

        except httpx.TimeoutException:
            logger.error(f"Text transform timeout for element {element_id}")
            return {
                "success": False,
                "error": {
                    "code": "TIMEOUT",
                    "message": "Text transformation timed out. Please try again.",
                    "retryable": True
                }
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"Text transform HTTP error: {e.response.status_code}")
            try:
                error_data = e.response.json()
                return {"success": False, "error": error_data.get("error", {"code": f"HTTP_{e.response.status_code}", "message": str(e), "retryable": e.response.status_code >= 500})}
            except Exception:
                return {"success": False, "error": {"code": f"HTTP_{e.response.status_code}", "message": f"Text service returned status {e.response.status_code}", "retryable": e.response.status_code >= 500}}

        except httpx.ConnectError:
            logger.error(f"Failed to connect to Text service at {self.base_url}")
            return {"success": False, "error": {"code": "CONNECTION_ERROR", "message": "Unable to connect to Text AI service.", "retryable": True}}

        except Exception as e:
            logger.exception(f"Unexpected error in text transformation: {e}")
            return {"success": False, "error": {"code": "INTERNAL_ERROR", "message": str(e), "retryable": False}}

    async def autofit(
        self,
        source_content: str,
        presentation_id: str,
        slide_id: str,
        element_id: str,
        context: Dict[str, Any],
        constraints: Dict[str, int],
        target_characters: Optional[int] = None,
        preserve_structure: bool = True
    ) -> Dict[str, Any]:
        """
        Auto-fit text to container size.

        Args:
            source_content: HTML content to fit
            presentation_id: Presentation identifier
            slide_id: Slide identifier
            element_id: Element identifier
            context: Presentation context
            constraints: Grid dimensions
            target_characters: Target character count (optional)
            preserve_structure: Maintain original structure (default True)

        Returns:
            Dict with success status and fitted html_content or error
        """
        # Backend expects 'content' not 'sourceContent', 'targetFit' not 'constraints'
        request_body = {
            "content": source_content,
            "presentationId": presentation_id,
            "slideId": slide_id,
            "elementId": element_id,
            "targetFit": constraints,  # Backend uses 'targetFit' for autofit
            "strategy": "smart_condense",  # Default strategy
            "preserveFormatting": preserve_structure
        }

        if target_characters:
            request_body["targetFit"]["maxCharacters"] = target_characters

        logger.info(f"Auto-fitting text: element={element_id}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/ai/text/autofit",
                    json=request_body
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"Text auto-fitted successfully: {element_id}")
                return result

        except httpx.TimeoutException:
            logger.error(f"Text autofit timeout for element {element_id}")
            return {"success": False, "error": {"code": "TIMEOUT", "message": "Text auto-fit timed out.", "retryable": True}}

        except httpx.HTTPStatusError as e:
            logger.error(f"Text autofit HTTP error: {e.response.status_code}")
            try:
                error_data = e.response.json()
                return {"success": False, "error": error_data.get("error", {"code": f"HTTP_{e.response.status_code}", "message": str(e), "retryable": e.response.status_code >= 500})}
            except Exception:
                return {"success": False, "error": {"code": f"HTTP_{e.response.status_code}", "message": f"Text service returned status {e.response.status_code}", "retryable": e.response.status_code >= 500}}

        except httpx.ConnectError:
            logger.error(f"Failed to connect to Text service at {self.base_url}")
            return {"success": False, "error": {"code": "CONNECTION_ERROR", "message": "Unable to connect to Text AI service.", "retryable": True}}

        except Exception as e:
            logger.exception(f"Unexpected error in text autofit: {e}")
            return {"success": False, "error": {"code": "INTERNAL_ERROR", "message": str(e), "retryable": False}}

    async def get_constraints(self, width: int, height: int) -> Dict[str, Any]:
        """
        Get text constraints for a given grid size.

        Results are cached after first successful call for each size.

        Args:
            width: Grid width (1-12)
            height: Grid height (1-8)

        Returns:
            Dict with maxCharacters, maxLines, recommendedFontSize, maxBullets
        """
        cache_key = f"{width}x{height}"

        if cache_key in self._constraints_cache:
            logger.debug(f"Returning cached text constraints for {cache_key}")
            return self._constraints_cache[cache_key]

        logger.info(f"Fetching text constraints for {cache_key}")

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.base_url}/api/ai/constraints/{width}/{height}"
                )
                response.raise_for_status()
                result = response.json()
                self._constraints_cache[cache_key] = result
                return result

        except Exception as e:
            logger.error(f"Failed to fetch text constraints: {e}")
            # Return estimated constraints based on grid size
            area = width * height
            return {
                "success": True,
                "gridWidth": width,
                "gridHeight": height,
                "maxCharacters": area * 50,  # ~50 chars per grid unit
                "maxLines": height * 3,       # ~3 lines per row
                "recommendedFontSize": "16px" if area > 20 else "14px" if area > 10 else "12px",
                "maxBullets": min(10, height * 2),
                "_cached": False,
                "_fallback": True
            }

    def clear_cache(self):
        """Clear cached constraints"""
        self._constraints_cache = {}
        logger.info("Text service cache cleared")
