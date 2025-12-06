"""
Diagram AI Service Client

Handles communication with the Diagram Generator v3.0 endpoints.

Uses async polling pattern:
1. POST /api/ai/diagram/generate → returns jobId
2. GET /api/ai/diagram/status/{jobId} → poll until complete/failed
3. Return SVG/Mermaid result

Endpoints:
    - POST /api/ai/diagram/generate - Submit diagram generation job
    - GET /api/ai/diagram/status/{jobId} - Poll job status
    - GET /api/ai/diagram/types - Get supported diagram types
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)


# Minimum grid sizes per diagram type (in 12×8 grid)
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


class DiagramService:
    """
    Client for the Diagram AI Service.

    Features:
        - Async job submission with polling
        - Configurable polling interval and max attempts
        - Response caching for diagram types
        - Error handling with retryable status
    """

    def __init__(self):
        self.base_url = settings.DIAGRAM_SERVICE_URL
        self.timeout = settings.SERVICE_TIMEOUT
        self.poll_timeout = settings.DIAGRAM_POLL_TIMEOUT
        self._types_cache: Optional[Dict[str, Any]] = None

    async def submit_job(
        self,
        prompt: str,
        diagram_type: str,
        presentation_id: str,
        slide_id: str,
        element_id: str,
        context: Dict[str, Any],
        constraints: Dict[str, int],
        direction: str = "TB",
        theme: str = "default",
        complexity: str = "moderate",
        mermaid_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit a diagram generation job.

        Args:
            prompt: Description of the diagram
            diagram_type: Type of diagram (flowchart, sequence, etc.)
            presentation_id: Presentation identifier
            slide_id: Slide identifier
            element_id: Element identifier
            context: Presentation context (title, slide info)
            constraints: Grid dimensions (gridWidth, gridHeight)
            direction: Layout direction (TB, BT, LR, RL)
            theme: Mermaid theme (default, dark, forest, neutral, base)
            complexity: Diagram complexity (simple, moderate, detailed)
            mermaid_code: Existing Mermaid code (bypasses AI generation)

        Returns:
            Dict with jobId for polling or error details
        """
        # Build request matching backend DiagramRequest schema
        # Backend expects: content, diagram_type (snake_case), theme (object), constraints (pixel-based)

        # Convert grid constraints to pixel constraints (60px per grid unit)
        grid_width = constraints.get("gridWidth", 8)
        grid_height = constraints.get("gridHeight", 6)
        max_width = grid_width * 60
        max_height = grid_height * 60

        # Build theme object matching backend DiagramTheme schema
        theme_obj = {
            "primaryColor": "#3B82F6",  # Default blue
            "colorScheme": "complementary",
            "backgroundColor": "#FFFFFF",
            "textColor": "#1F2937",
            "fontFamily": "Inter, system-ui, sans-serif",
            "style": theme if isinstance(theme, str) else "professional",
            "useSmartTheming": True
        }

        # Extract brand colors from context if available
        if context.get("brandColors") and len(context["brandColors"]) > 0:
            theme_obj["primaryColor"] = context["brandColors"][0]
            if len(context["brandColors"]) > 1:
                theme_obj["secondaryColor"] = context["brandColors"][1]

        # Build constraints object matching backend DiagramConstraints schema
        backend_constraints = {
            "maxWidth": max_width,
            "maxHeight": max_height,
            "orientation": "landscape" if grid_width > grid_height else "portrait",
            "complexity": complexity,
            "animationEnabled": False
        }

        # Calculate aspect ratio
        from math import gcd
        divisor = gcd(grid_width, grid_height)
        backend_constraints["aspectRatio"] = f"{grid_width // divisor}:{grid_height // divisor}"

        request_body = {
            "content": prompt,  # Backend uses 'content' not 'prompt'
            "diagram_type": diagram_type.lower().replace("-", "_"),  # snake_case
            "data_points": [],  # Empty list, AI will generate
            "theme": theme_obj,
            "constraints": backend_constraints,
            "correlation_id": element_id,
            "session_id": presentation_id,
            "user_id": slide_id
        }

        if mermaid_code:
            # If mermaid code provided, add it as additional context
            request_body["content"] = f"{prompt}\n\nMermaid code:\n{mermaid_code}"

        logger.info(f"Submitting diagram job: type={diagram_type}, element={element_id}")
        logger.debug(f"Request body: {request_body}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/ai/diagram/generate",
                    json=request_body
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"Diagram job submitted: {result.get('jobId')}")
                return result

        except httpx.TimeoutException:
            logger.error(f"Diagram service timeout for element {element_id}")
            return {
                "success": False,
                "error": {
                    "code": "TIMEOUT",
                    "message": "Diagram service timed out. Please try again.",
                    "retryable": True
                }
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"Diagram service HTTP error: {e.response.status_code}")
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
                        "message": f"Diagram service returned status {e.response.status_code}",
                        "retryable": e.response.status_code >= 500
                    }
                }

        except httpx.ConnectError:
            logger.error(f"Failed to connect to Diagram service at {self.base_url}")
            return {
                "success": False,
                "error": {
                    "code": "CONNECTION_ERROR",
                    "message": "Unable to connect to Diagram AI service. Please try again later.",
                    "retryable": True
                }
            }

        except Exception as e:
            logger.exception(f"Unexpected error in diagram job submission: {e}")
            return {
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e),
                    "retryable": False
                }
            }

    async def poll_status(self, job_id: str) -> Dict[str, Any]:
        """
        Poll the status of a diagram generation job.

        Args:
            job_id: Job identifier from submit_job

        Returns:
            Dict with status, progress, and result (if complete)
        """
        logger.debug(f"Polling diagram job status: {job_id}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/ai/diagram/status/{job_id}"
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {
                    "status": "failed",
                    "error": f"Job {job_id} not found"
                }
            return {
                "status": "failed",
                "error": f"HTTP error: {e.response.status_code}"
            }

        except Exception as e:
            logger.error(f"Error polling diagram status: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }

    async def generate_with_polling(
        self,
        prompt: str,
        diagram_type: str,
        presentation_id: str,
        slide_id: str,
        element_id: str,
        context: Dict[str, Any],
        constraints: Dict[str, int],
        direction: str = "TB",
        theme: str = "default",
        complexity: str = "moderate",
        mermaid_code: Optional[str] = None,
        max_polls: int = 30,
        poll_interval: float = 2.0
    ) -> Dict[str, Any]:
        """
        Generate a diagram with automatic polling until complete.

        Args:
            prompt: Description of the diagram
            diagram_type: Type of diagram
            ... (same as submit_job)
            max_polls: Maximum number of poll attempts (default 30 = 60 seconds)
            poll_interval: Seconds between polls (default 2.0)

        Returns:
            Dict with success status and either diagram result or error details
        """
        # Submit the job
        submit_result = await self.submit_job(
            prompt=prompt,
            diagram_type=diagram_type,
            presentation_id=presentation_id,
            slide_id=slide_id,
            element_id=element_id,
            context=context,
            constraints=constraints,
            direction=direction,
            theme=theme,
            complexity=complexity,
            mermaid_code=mermaid_code
        )

        if not submit_result.get("success", True):
            return submit_result

        job_id = submit_result.get("jobId")
        if not job_id:
            # Direct result (no polling needed)
            return submit_result

        # Poll for completion
        logger.info(f"Polling diagram job {job_id} (max {max_polls} attempts)")

        for attempt in range(max_polls):
            await asyncio.sleep(poll_interval)

            status_result = await self.poll_status(job_id)
            status = status_result.get("status", "unknown")

            logger.debug(f"Poll {attempt + 1}/{max_polls}: status={status}")

            if status == "completed":
                logger.info(f"Diagram job {job_id} completed successfully")
                return {
                    "success": True,
                    "job_id": job_id,
                    "mermaid_code": status_result.get("mermaidCode"),
                    "svg_content": status_result.get("svgContent"),
                    "diagram_type": diagram_type
                }

            elif status == "failed":
                error_msg = status_result.get("error", "Unknown error")
                logger.error(f"Diagram job {job_id} failed: {error_msg}")
                return {
                    "success": False,
                    "job_id": job_id,
                    "error": {
                        "code": "GENERATION_FAILED",
                        "message": error_msg,
                        "retryable": True
                    }
                }

            elif status not in ("pending", "processing"):
                logger.warning(f"Unknown diagram job status: {status}")

        # Polling timed out
        logger.error(f"Diagram job {job_id} polling timed out after {max_polls} attempts")
        return {
            "success": False,
            "job_id": job_id,
            "error": {
                "code": "POLL_TIMEOUT",
                "message": f"Diagram generation timed out after {max_polls * poll_interval} seconds",
                "retryable": True
            }
        }

    async def get_types(self) -> Dict[str, Any]:
        """
        Get supported diagram types with their constraints.

        Results are cached after first successful call.

        Returns:
            Dict with types array and their constraints
        """
        if self._types_cache is not None:
            logger.debug("Returning cached diagram types")
            return self._types_cache

        logger.info("Fetching diagram types from service")

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/ai/diagram/types")
                response.raise_for_status()
                self._types_cache = response.json()
                return self._types_cache

        except Exception as e:
            logger.error(f"Failed to fetch diagram types: {e}")
            # Return default types if service is unavailable
            return {
                "success": True,
                "types": [
                    {
                        "type": "flowchart",
                        "name": "Flowchart",
                        "description": "Process flows and decision trees",
                        "minGridWidth": 3,
                        "minGridHeight": 2,
                        "supportsDirection": True
                    },
                    {
                        "type": "sequence",
                        "name": "Sequence Diagram",
                        "description": "API interactions and message flows",
                        "minGridWidth": 4,
                        "minGridHeight": 3,
                        "supportsDirection": False
                    },
                    {
                        "type": "class",
                        "name": "Class Diagram",
                        "description": "UML class relationships",
                        "minGridWidth": 4,
                        "minGridHeight": 3,
                        "supportsDirection": True
                    },
                    {
                        "type": "state",
                        "name": "State Diagram",
                        "description": "State machines and transitions",
                        "minGridWidth": 3,
                        "minGridHeight": 3,
                        "supportsDirection": True
                    },
                    {
                        "type": "er",
                        "name": "ER Diagram",
                        "description": "Entity-relationship database schemas",
                        "minGridWidth": 4,
                        "minGridHeight": 3,
                        "supportsDirection": False
                    },
                    {
                        "type": "gantt",
                        "name": "Gantt Chart",
                        "description": "Project timelines and schedules",
                        "minGridWidth": 6,
                        "minGridHeight": 2,
                        "supportsDirection": False
                    },
                    {
                        "type": "userjourney",
                        "name": "User Journey",
                        "description": "UX flows and user experiences",
                        "minGridWidth": 4,
                        "minGridHeight": 2,
                        "supportsDirection": False
                    },
                    {
                        "type": "gitgraph",
                        "name": "Git Graph",
                        "description": "Git branch and merge visualizations",
                        "minGridWidth": 4,
                        "minGridHeight": 2,
                        "supportsDirection": True
                    },
                    {
                        "type": "mindmap",
                        "name": "Mind Map",
                        "description": "Ideas and concept hierarchies",
                        "minGridWidth": 4,
                        "minGridHeight": 4,
                        "supportsDirection": False
                    },
                    {
                        "type": "pie",
                        "name": "Pie Chart",
                        "description": "Proportional data visualization",
                        "minGridWidth": 3,
                        "minGridHeight": 3,
                        "supportsDirection": False
                    },
                    {
                        "type": "timeline",
                        "name": "Timeline",
                        "description": "Chronological events",
                        "minGridWidth": 5,
                        "minGridHeight": 2,
                        "supportsDirection": False
                    }
                ],
                "_cached": False,
                "_fallback": True
            }

    def clear_cache(self):
        """Clear cached diagram types"""
        self._types_cache = None
        logger.info("Diagram service cache cleared")

    def get_min_size(self, diagram_type: str) -> Dict[str, int]:
        """Get minimum grid size for a diagram type"""
        return DIAGRAM_MIN_SIZES.get(diagram_type, {"width": 3, "height": 3})
