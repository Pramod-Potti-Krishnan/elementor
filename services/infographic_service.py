"""
Infographic AI Service Client

Handles communication with the Illustrator v1.0 endpoints.

Endpoints:
    - POST /api/ai/illustrator/generate - Generate infographic
    - GET /api/ai/illustrator/types - Get supported infographic types
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)


# Infographic types with their constraints
# Template-based (HTML): pyramid, funnel, concentric_circles, concept_spread, venn, comparison
# Dynamic SVG (Gemini): timeline, process, statistics, hierarchy, list, cycle, matrix, roadmap
INFOGRAPHIC_TYPES = {
    # Template-based (HTML)
    "pyramid": {
        "name": "Pyramid",
        "description": "Hierarchical pyramid visualization",
        "generator": "template",
        "minGridWidth": 6,
        "minGridHeight": 4,
        "minItems": 3,
        "maxItems": 6,
        "supportsIcons": True
    },
    "funnel": {
        "name": "Funnel",
        "description": "Funnel conversion flow",
        "generator": "template",
        "minGridWidth": 6,
        "minGridHeight": 4,
        "minItems": 3,
        "maxItems": 6,
        "supportsIcons": True
    },
    "concentric_circles": {
        "name": "Concentric Circles",
        "description": "Nested circles for layered concepts",
        "generator": "template",
        "minGridWidth": 6,
        "minGridHeight": 6,
        "minItems": 2,
        "maxItems": 5,
        "supportsIcons": False
    },
    "concept_spread": {
        "name": "Concept Spread",
        "description": "Spread layout for related concepts",
        "generator": "template",
        "minGridWidth": 8,
        "minGridHeight": 4,
        "minItems": 3,
        "maxItems": 6,
        "supportsIcons": True
    },
    "venn": {
        "name": "Venn Diagram",
        "description": "Overlapping circles for relationships",
        "generator": "template",
        "minGridWidth": 6,
        "minGridHeight": 4,
        "minItems": 2,
        "maxItems": 4,
        "supportsIcons": False
    },
    "comparison": {
        "name": "Comparison",
        "description": "Side-by-side comparison",
        "generator": "template",
        "minGridWidth": 8,
        "minGridHeight": 4,
        "minItems": 2,
        "maxItems": 2,
        "supportsIcons": True
    },
    # Dynamic SVG (Gemini 2.5 Pro)
    "timeline": {
        "name": "Timeline",
        "description": "Chronological events visualization",
        "generator": "svg",
        "minGridWidth": 8,
        "minGridHeight": 3,
        "minItems": 3,
        "maxItems": 10,
        "supportsIcons": True
    },
    "process": {
        "name": "Process",
        "description": "Step-by-step process flow",
        "generator": "svg",
        "minGridWidth": 6,
        "minGridHeight": 3,
        "minItems": 3,
        "maxItems": 8,
        "supportsIcons": True
    },
    "statistics": {
        "name": "Statistics",
        "description": "Key statistics and metrics",
        "generator": "svg",
        "minGridWidth": 4,
        "minGridHeight": 3,
        "minItems": 2,
        "maxItems": 8,
        "supportsIcons": True
    },
    "hierarchy": {
        "name": "Hierarchy",
        "description": "Organizational hierarchy tree",
        "generator": "svg",
        "minGridWidth": 6,
        "minGridHeight": 4,
        "minItems": 3,
        "maxItems": 15,
        "supportsIcons": False
    },
    "list": {
        "name": "List",
        "description": "Styled list with icons",
        "generator": "svg",
        "minGridWidth": 4,
        "minGridHeight": 4,
        "minItems": 3,
        "maxItems": 12,
        "supportsIcons": True
    },
    "cycle": {
        "name": "Cycle",
        "description": "Circular cycle diagram",
        "generator": "svg",
        "minGridWidth": 6,
        "minGridHeight": 6,
        "minItems": 3,
        "maxItems": 8,
        "supportsIcons": True
    },
    "matrix": {
        "name": "Matrix",
        "description": "2x2 or 3x3 matrix grid",
        "generator": "svg",
        "minGridWidth": 6,
        "minGridHeight": 6,
        "minItems": 4,
        "maxItems": 4,
        "supportsIcons": False
    },
    "roadmap": {
        "name": "Roadmap",
        "description": "Project or product roadmap",
        "generator": "svg",
        "minGridWidth": 8,
        "minGridHeight": 4,
        "minItems": 3,
        "maxItems": 8,
        "supportsIcons": True
    }
}


class InfographicService:
    """
    Client for the Infographic AI Service (Illustrator).

    Features:
        - Async HTTP calls with configurable timeout
        - Support for template (HTML) and SVG generators
        - Response caching for types
        - Error handling with retryable status
    """

    def __init__(self):
        self.base_url = settings.INFOGRAPHIC_SERVICE_URL
        self.timeout = settings.SERVICE_TIMEOUT
        self._types_cache: Optional[Dict[str, Any]] = None

    async def generate(
        self,
        prompt: str,
        infographic_type: str,
        presentation_id: str,
        slide_id: str,
        element_id: str,
        context: Dict[str, Any],
        constraints: Dict[str, int],
        color_scheme: str = "professional",
        icon_style: str = "outlined",
        item_count: Optional[int] = None,
        items: Optional[List[Dict[str, Any]]] = None,
        generate_data: bool = False
    ) -> Dict[str, Any]:
        """
        Generate an infographic via Illustrator AI Service.

        Args:
            prompt: Description of the infographic
            infographic_type: Type of infographic (pyramid, timeline, etc.)
            presentation_id: Presentation identifier
            slide_id: Slide identifier
            element_id: Element identifier
            context: Presentation context (title, slide info)
            constraints: Grid dimensions (gridWidth, gridHeight)
            color_scheme: Color scheme (professional, vibrant, pastel, etc.)
            icon_style: Icon style (outlined, filled, duotone, minimal)
            item_count: Number of items to generate
            items: Pre-defined items with title, description, icon
            generate_data: Generate sample data if no items provided

        Returns:
            Dict with success status and either html_content/svg_content or error
        """
        # Backend uses 'type' not 'infographicType'
        # Backend uses 32x18 grid system - scale up from 12x8 if needed
        grid_width = constraints.get("gridWidth", 8)
        grid_height = constraints.get("gridHeight", 6)

        # Scale grid from 12x8 to 32x18 system if values are small
        if grid_width <= 12 and grid_height <= 8:
            # Scale factor: 32/12 ≈ 2.67 for width, 18/8 = 2.25 for height
            scaled_width = min(32, int(grid_width * 32 / 12))
            scaled_height = min(18, int(grid_height * 18 / 8))
        else:
            scaled_width = min(32, grid_width)
            scaled_height = min(18, grid_height)

        backend_constraints = {
            "gridWidth": scaled_width,
            "gridHeight": scaled_height
        }

        # Build context object matching backend PresentationContext schema
        backend_context = {
            "presentationTitle": context.get("presentationTitle", "Untitled"),
            "slideIndex": context.get("slideIndex", 0),
        }
        if context.get("presentationTheme"):
            backend_context["presentationTheme"] = context["presentationTheme"]
        if context.get("slideTitle"):
            backend_context["slideTitle"] = context["slideTitle"]
        if context.get("brandColors"):
            backend_context["brandColors"] = context["brandColors"]
        if context.get("industry"):
            backend_context["industry"] = context["industry"]

        # Build style object matching backend StyleOptions schema
        style_options = {
            "colorScheme": color_scheme,
            "iconStyle": icon_style,
            "density": "balanced",
            "orientation": "auto"
        }

        # Build contentOptions object matching backend ContentOptions schema
        content_options = {
            "includeIcons": True,
            "includeDescriptions": True,
            "includeNumbers": False
        }
        if item_count is not None:
            content_options["itemCount"] = item_count

        request_body = {
            "prompt": prompt,
            "type": infographic_type,  # Backend uses 'type' not 'infographicType'
            "presentationId": presentation_id,
            "slideId": slide_id,
            "elementId": element_id,
            "context": backend_context,
            "constraints": backend_constraints,
            "style": style_options,
            "contentOptions": content_options
        }

        logger.info(f"Generating infographic: type={infographic_type}, element={element_id}")
        logger.debug(f"Request body: {request_body}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/ai/illustrator/generate",
                    json=request_body
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"Infographic generated successfully: {element_id}")
                return result

        except httpx.TimeoutException:
            logger.error(f"Infographic service timeout for element {element_id}")
            return {
                "success": False,
                "error": {
                    "code": "TIMEOUT",
                    "message": "Infographic generation timed out. Please try again.",
                    "retryable": True
                }
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"Infographic service HTTP error: {e.response.status_code}")
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
                        "message": f"Infographic service returned status {e.response.status_code}",
                        "retryable": e.response.status_code >= 500
                    }
                }

        except httpx.ConnectError:
            logger.error(f"Failed to connect to Infographic service at {self.base_url}")
            return {
                "success": False,
                "error": {
                    "code": "CONNECTION_ERROR",
                    "message": "Unable to connect to Infographic AI service. Please try again later.",
                    "retryable": True
                }
            }

        except Exception as e:
            logger.exception(f"Unexpected error in infographic generation: {e}")
            return {
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e),
                    "retryable": False
                }
            }

    async def get_types(self) -> Dict[str, Any]:
        """
        Get supported infographic types with their constraints.

        Results are cached after first successful call.

        Returns:
            Dict with types array and their constraints
        """
        if self._types_cache is not None:
            logger.debug("Returning cached infographic types")
            return self._types_cache

        logger.info("Fetching infographic types from service")

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/ai/illustrator/types")
                response.raise_for_status()
                self._types_cache = response.json()
                return self._types_cache

        except Exception as e:
            logger.error(f"Failed to fetch infographic types: {e}")
            # Return default types if service is unavailable
            return {
                "success": True,
                "types": [
                    {
                        "type": key,
                        "name": value["name"],
                        "description": value["description"],
                        "generator": value["generator"],
                        "minGridWidth": value["minGridWidth"],
                        "minGridHeight": value["minGridHeight"],
                        "minItems": value["minItems"],
                        "maxItems": value["maxItems"],
                        "supportsIcons": value["supportsIcons"]
                    }
                    for key, value in INFOGRAPHIC_TYPES.items()
                ],
                "colorSchemes": [
                    "professional", "vibrant", "pastel",
                    "monochrome", "warm", "cool"
                ],
                "iconStyles": ["outlined", "filled", "duotone", "minimal"],
                "_cached": False,
                "_fallback": True
            }

    def get_type_info(self, infographic_type: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific infographic type.

        Args:
            infographic_type: Type of infographic

        Returns:
            Dict with type info or None if not found
        """
        return INFOGRAPHIC_TYPES.get(infographic_type)

    def get_min_size(self, infographic_type: str) -> Dict[str, int]:
        """Get minimum grid size for an infographic type"""
        type_info = INFOGRAPHIC_TYPES.get(infographic_type)
        if type_info:
            return {
                "width": type_info["minGridWidth"],
                "height": type_info["minGridHeight"]
            }
        return {"width": 6, "height": 4}  # Default

    def clear_cache(self):
        """Clear cached types"""
        self._types_cache = None
        logger.info("Infographic service cache cleared")
