"""
Chart AI Service Client

Handles communication with the Analytics Microservice v3.0 Chart AI endpoints.

Endpoints:
    - POST /generate - Submit chart generation job
    - GET /status/{job_id} - Poll job status
    - GET /api/v1/chart-types - Get available chart types
    - GET /api/v1/chart-types/chartjs - Get Chart.js specific types
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)


class ChartService:
    """
    Client for the Chart AI Service.

    Features:
        - Async HTTP calls with job polling
        - Response caching for chart types
        - Error handling with retryable status
    """

    def __init__(self):
        self.base_url = settings.CHART_SERVICE_URL
        self.timeout = settings.SERVICE_TIMEOUT
        self._constraints_cache: Optional[Dict[str, Any]] = None
        self._palettes_cache: Optional[Dict[str, Any]] = None
        self.poll_interval = 1.0  # seconds
        self.poll_timeout = 60.0  # max polling time

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
        axes: Optional[Dict[str, Any]] = None,
        layout: str = "L02"
    ) -> Dict[str, Any]:
        """
        Generate a Chart.js configuration via Analytics Microservice v3.0.

        Uses the /generate endpoint with async job polling.

        Args:
            prompt: Description of the chart data (used as content)
            chart_type: Type of chart (bar_vertical, line, pie, etc.)
            presentation_id: Presentation identifier
            slide_id: Slide identifier
            element_id: Element identifier
            context: Presentation context (title, slide info)
            constraints: Grid dimensions (gridWidth, gridHeight)
            style: Style options (palette, legend, data labels)
            data: User-provided data points (optional)
            generate_data: Generate synthetic data if no data provided
            axes: Axis configuration (labels, min/max, stacked)
            layout: Layout identifier (default L02 for chart slides)

        Returns:
            Dict with success status and either chart config or error details
        """
        # Map simple chart types to Analytics service types
        chart_type_map = {
            "bar": "bar_vertical",
            "line": "line",
            "pie": "pie",
            "doughnut": "doughnut",
            "area": "area",
            "scatter": "scatter",
            "radar": "radar",
            "polarArea": "polar_area",
            "bubble": "bubble",
            "treemap": "treemap"
        }
        mapped_chart_type = chart_type_map.get(chart_type, chart_type)

        # Get theme from style - map to valid Analytics service themes
        # Valid themes: professional, vibrant, minimal, colorful
        theme_map = {
            "default": "professional",
            "professional": "professional",
            "vibrant": "vibrant",
            "pastel": "pastel",
            "monochrome": "minimal",
            "colorful": "colorful"
        }
        raw_theme = style.get("palette", "professional") if style else "professional"
        theme = theme_map.get(raw_theme, "professional")

        # Build request matching ChartRequest schema
        title = context.get("slideTitle") or context.get("presentationTitle") or "Chart"
        request_body = {
            "content": prompt,
            "title": title,
            "chart_type": mapped_chart_type,
            "theme": theme
        }

        # Add data if provided
        if data:
            request_body["data"] = [
                {"label": d.get("label", str(i)), "value": d.get("value", 0)}
                for i, d in enumerate(data)
            ]

        logger.info(f"Generating chart: type={mapped_chart_type}, element={element_id}")
        logger.info(f"Chart request body: {request_body}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Submit job
                response = await client.post(
                    f"{self.base_url}/generate",
                    json=request_body
                )
                response.raise_for_status()
                job_data = response.json()
                job_id = job_data.get("job_id")

                if not job_id:
                    return {
                        "success": False,
                        "error": {
                            "code": "NO_JOB_ID",
                            "message": "Chart service did not return a job ID",
                            "retryable": True
                        }
                    }

                logger.info(f"Chart job submitted: {job_id}")

                # Poll for completion
                result = await self._poll_job(client, job_id)
                if result.get("success"):
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

    async def _poll_job(self, client: httpx.AsyncClient, job_id: str) -> Dict[str, Any]:
        """
        Poll the job status until completion or timeout.

        Args:
            client: The HTTP client to use
            job_id: The job ID to poll

        Returns:
            Dict with success status and chart data or error
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > self.poll_timeout:
                return {
                    "success": False,
                    "error": {
                        "code": "POLL_TIMEOUT",
                        "message": f"Chart generation timed out after {self.poll_timeout}s",
                        "retryable": True
                    }
                }

            try:
                response = await client.get(f"{self.base_url}/status/{job_id}")
                response.raise_for_status()
                status_data = response.json()

                status = status_data.get("status", "unknown")
                logger.debug(f"Chart job {job_id} status: {status}")

                if status == "completed":
                    # Build Chart.js compatible config from the data
                    chart_data = status_data.get("chart_data", {})
                    chart_type = status_data.get("chart_type", "bar")

                    # Create Chart.js configuration
                    chartjs_config = {
                        "type": chart_type.replace("_vertical", "").replace("_horizontal", ""),
                        "data": {
                            "labels": chart_data.get("labels", []),
                            "datasets": [{
                                "label": chart_data.get("title", "Data"),
                                "data": chart_data.get("values", []),
                                "backgroundColor": [
                                    "#3B82F6", "#10B981", "#F59E0B", "#EF4444",
                                    "#8B5CF6", "#EC4899", "#06B6D4", "#84CC16"
                                ][:len(chart_data.get("values", []))]
                            }]
                        },
                        "options": {
                            "responsive": True,
                            "maintainAspectRatio": False,
                            "plugins": {
                                "title": {
                                    "display": True,
                                    "text": chart_data.get("title", "")
                                }
                            }
                        }
                    }

                    # Return successful result
                    return {
                        "success": True,
                        "data": {
                            "chartConfig": chartjs_config,
                            "chartUrl": status_data.get("chart_url"),
                            "rawData": chart_data,
                            "chartType": chart_type,
                            "theme": status_data.get("theme"),
                            "metadata": status_data.get("metadata")
                        }
                    }
                elif status == "failed":
                    return {
                        "success": False,
                        "error": {
                            "code": "CHART_GENERATION_FAILED",
                            "message": status_data.get("error", "Chart generation failed"),
                            "retryable": True
                        }
                    }
                else:
                    # Still processing, wait and retry
                    await asyncio.sleep(self.poll_interval)

            except httpx.HTTPStatusError as e:
                return {
                    "success": False,
                    "error": {
                        "code": f"POLL_HTTP_{e.response.status_code}",
                        "message": f"Error polling chart status: {e.response.status_code}",
                        "retryable": True
                    }
                }
            except Exception as e:
                logger.error(f"Error polling chart job {job_id}: {e}")
                return {
                    "success": False,
                    "error": {
                        "code": "POLL_ERROR",
                        "message": str(e),
                        "retryable": True
                    }
                }

    async def get_constraints(self) -> Dict[str, Any]:
        """
        Get chart types with their constraints.

        Fetches from /api/v1/chart-types endpoint and extracts constraints.
        Results are cached after first successful call.

        Returns:
            Dict with minimumGridSizes, dataLimits, gridRanges, sizeThresholds
        """
        if self._constraints_cache is not None:
            logger.debug("Returning cached constraints")
            return self._constraints_cache

        logger.info("Fetching chart types/constraints from service")

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/v1/chart-types/chartjs")
                response.raise_for_status()
                chart_types = response.json()

                # Build constraints from chart types data
                min_sizes = {}
                for ct in chart_types if isinstance(chart_types, list) else []:
                    chart_id = ct.get("id", ct.get("type", "unknown"))
                    min_sizes[chart_id] = {
                        "width": ct.get("minWidth", 3),
                        "height": ct.get("minHeight", 3)
                    }

                self._constraints_cache = {
                    "success": True,
                    "minimumGridSizes": min_sizes,
                    "chartTypes": chart_types
                }
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
