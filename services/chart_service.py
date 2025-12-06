"""
Chart AI Service Client

Handles communication with the Analytics Microservice v3.0 Chart AI endpoints.

Endpoints:
    - POST /api/ai/chart/generate - Generate Chart.js configuration
    - GET /api/ai/chart/constraints - Get minimum grid sizes and data limits
    - GET /api/ai/chart/palettes - Get available color palettes
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)


class ChartService:
    """
    Client for the Chart AI Service.

    Features:
        - Async HTTP calls with configurable timeout
        - Response caching for constraints and palettes
        - Error handling with retryable status
    """

    def __init__(self):
        self.base_url = settings.CHART_SERVICE_URL
        self.timeout = settings.SERVICE_TIMEOUT
        self._constraints_cache: Optional[Dict[str, Any]] = None
        self._palettes_cache: Optional[Dict[str, Any]] = None

    async def generate(
        self,
        prompt: str,
        chart_type: str,
        presentation_id: str,
        slide_id: str,
        element_id: str,
        context: Dict[str, Any],
        constraints: Dict[str, int],
        style: Dict[str, Any],
        data: Optional[List[Dict]] = None,
        generate_data: bool = False,
        axes: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a Chart.js configuration via Chart AI Service.

        Args:
            prompt: Description of the chart data
            chart_type: Type of chart (bar, line, pie, etc.)
            presentation_id: Presentation identifier
            slide_id: Slide identifier
            element_id: Element identifier
            context: Presentation context (title, slide info)
            constraints: Grid dimensions (gridWidth, gridHeight)
            style: Style options (palette, legend, data labels)
            data: User-provided data points (optional)
            generate_data: Generate synthetic data if no data provided
            axes: Axis configuration (labels, min/max, stacked)

        Returns:
            Dict with success status and either chart config or error details
        """
        # Build context object matching backend ChartContext schema
        # Required fields: presentationTitle, slideIndex
        backend_context = {
            "presentationTitle": context.get("presentationTitle", "Untitled"),
            "slideIndex": context.get("slideIndex", 0),
        }
        # Optional context fields
        if context.get("slideTitle"):
            backend_context["slideTitle"] = context["slideTitle"]
        if context.get("industry"):
            backend_context["industry"] = context["industry"]
        if context.get("timeFrame"):
            backend_context["timeFrame"] = context["timeFrame"]

        request_body = {
            "prompt": prompt,
            "chartType": chart_type,
            "presentationId": presentation_id,
            "slideId": slide_id,
            "elementId": element_id,
            "context": backend_context,
            "constraints": constraints,
        }

        # Add style if provided
        if style:
            request_body["style"] = style

        if data:
            # Convert data to Chart AI format
            request_body["data"] = [
                {"label": d.get("label", str(i)), "value": d.get("value", 0)}
                for i, d in enumerate(data)
            ]
        else:
            request_body["generateData"] = generate_data

        if axes:
            request_body["axes"] = axes

        logger.info(f"Generating chart: type={chart_type}, element={element_id}")
        logger.debug(f"Request body: {request_body}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/ai/chart/generate",
                    json=request_body
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"Chart generated successfully: {element_id}")
                return result

        except httpx.TimeoutException:
            logger.error(f"Chart service timeout for element {element_id}")
            return {
                "success": False,
                "error": {
                    "code": "TIMEOUT",
                    "message": "Chart generation timed out. Please try again.",
                    "retryable": True
                }
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"Chart service HTTP error: {e.response.status_code}")
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
                        "message": f"Chart service returned status {e.response.status_code}",
                        "retryable": e.response.status_code >= 500
                    }
                }

        except httpx.ConnectError:
            logger.error(f"Failed to connect to Chart service at {self.base_url}")
            return {
                "success": False,
                "error": {
                    "code": "CONNECTION_ERROR",
                    "message": "Unable to connect to Chart AI service. Please try again later.",
                    "retryable": True
                }
            }

        except Exception as e:
            logger.exception(f"Unexpected error in chart generation: {e}")
            return {
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e),
                    "retryable": False
                }
            }

    async def get_constraints(self) -> Dict[str, Any]:
        """
        Get grid size constraints and data limits for all chart types.

        Results are cached after first successful call.

        Returns:
            Dict with minimumGridSizes, dataLimits, gridRanges, sizeThresholds
        """
        if self._constraints_cache is not None:
            logger.debug("Returning cached constraints")
            return self._constraints_cache

        logger.info("Fetching chart constraints from service")

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/ai/chart/constraints")
                response.raise_for_status()
                self._constraints_cache = response.json()
                return self._constraints_cache

        except Exception as e:
            logger.error(f"Failed to fetch constraints: {e}")
            # Return default constraints if service is unavailable
            return {
                "success": True,
                "minimumGridSizes": {
                    "bar": {"width": 3, "height": 3},
                    "line": {"width": 3, "height": 2},
                    "pie": {"width": 3, "height": 3},
                    "doughnut": {"width": 3, "height": 3},
                    "area": {"width": 3, "height": 2},
                    "scatter": {"width": 4, "height": 3},
                    "radar": {"width": 4, "height": 4},
                    "polarArea": {"width": 3, "height": 3}
                },
                "dataLimits": {
                    "bar": {"small": 4, "medium": 8, "large": 15},
                    "line": {"small": 6, "medium": 12, "large": 24},
                    "pie": {"small": 4, "medium": 6, "large": 8}
                },
                "gridRanges": {
                    "width": {"min": 1, "max": 12},
                    "height": {"min": 1, "max": 8}
                },
                "sizeThresholds": {
                    "small": "area <= 16",
                    "medium": "16 < area <= 48",
                    "large": "area > 48"
                },
                "_cached": False,
                "_fallback": True
            }

    async def get_palettes(self) -> Dict[str, Any]:
        """
        Get available color palettes.

        Results are cached after first successful call.

        Returns:
            Dict with palettes array and defaultPalette
        """
        if self._palettes_cache is not None:
            logger.debug("Returning cached palettes")
            return self._palettes_cache

        logger.info("Fetching chart palettes from service")

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/ai/chart/palettes")
                response.raise_for_status()
                self._palettes_cache = response.json()
                return self._palettes_cache

        except Exception as e:
            logger.error(f"Failed to fetch palettes: {e}")
            # Return default palettes if service is unavailable
            return {
                "success": True,
                "palettes": [
                    {
                        "name": "default",
                        "colors": ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#06B6D4", "#84CC16"],
                        "colorCount": 8
                    },
                    {
                        "name": "professional",
                        "colors": ["#1E3A5F", "#2D5A87", "#3D7AAF", "#4D9AD7", "#5DBAFF", "#0D9488", "#14B8A6", "#2DD4BF"],
                        "colorCount": 8
                    },
                    {
                        "name": "vibrant",
                        "colors": ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FECA57", "#FF9FF3", "#54A0FF", "#5F27CD"],
                        "colorCount": 8
                    },
                    {
                        "name": "pastel",
                        "colors": ["#A8D8EA", "#AA96DA", "#FCBAD3", "#FFFFD2", "#B5EAD7", "#C7CEEA", "#FFB7B2", "#FFDAC1"],
                        "colorCount": 8
                    },
                    {
                        "name": "monochrome",
                        "colors": ["#111827", "#374151", "#4B5563", "#6B7280", "#9CA3AF", "#D1D5DB", "#E5E7EB", "#F3F4F6"],
                        "colorCount": 8
                    }
                ],
                "defaultPalette": "default",
                "_cached": False,
                "_fallback": True
            }

    def clear_cache(self):
        """Clear cached constraints and palettes"""
        self._constraints_cache = None
        self._palettes_cache = None
        logger.info("Chart service cache cleared")
