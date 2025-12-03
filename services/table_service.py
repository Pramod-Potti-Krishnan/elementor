"""
Table AI Service Client

Handles communication with the Text Table Builder v1.2 Table endpoints.

Endpoints:
    - POST /api/ai/table/generate - Generate table content
    - POST /api/ai/table/transform - Transform existing table
    - POST /api/ai/table/analyze - Analyze table data
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)


# Table presets with their descriptions
TABLE_PRESETS = {
    "minimal": "Clean design with minimal borders",
    "bordered": "Full cell borders for clarity",
    "striped": "Alternating row colors for readability",
    "modern": "Contemporary design with subtle styling",
    "professional": "Corporate-appropriate styling",
    "colorful": "Vibrant colors for engagement"
}


class TableService:
    """
    Client for the Table AI Service.

    Features:
        - Async HTTP calls with configurable timeout
        - Support for table generation, transformation, and analysis
        - Error handling with retryable status
    """

    def __init__(self):
        self.base_url = settings.TEXT_TABLE_SERVICE_URL
        self.timeout = settings.SERVICE_TIMEOUT

    async def generate(
        self,
        prompt: str,
        presentation_id: str,
        slide_id: str,
        element_id: str,
        context: Dict[str, Any],
        constraints: Dict[str, int],
        preset: str = "professional",
        columns: Optional[int] = None,
        rows: Optional[int] = None,
        has_header: bool = True,
        data: Optional[List[List[str]]] = None
    ) -> Dict[str, Any]:
        """
        Generate a table via Table AI Service.

        Args:
            prompt: Description of the table content
            presentation_id: Presentation identifier
            slide_id: Slide identifier
            element_id: Element identifier
            context: Presentation context (title, slide info)
            constraints: Grid dimensions (gridWidth, gridHeight)
            preset: Table style preset (minimal, bordered, striped, etc.)
            columns: Number of columns (optional, AI will decide)
            rows: Number of data rows (optional, AI will decide)
            has_header: Include header row (default True)
            data: Existing data as 2D array (optional)

        Returns:
            Dict with success status and either html_content or error details
        """
        request_body = {
            "prompt": prompt,
            "presentationId": presentation_id,
            "slideId": slide_id,
            "elementId": element_id,
            "context": context,
            "constraints": constraints,
            "preset": preset,
            "hasHeader": has_header
        }

        if columns:
            request_body["columns"] = columns
        if rows:
            request_body["rows"] = rows
        if data:
            request_body["data"] = data

        logger.info(f"Generating table: preset={preset}, element={element_id}")
        logger.debug(f"Request body: {request_body}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/ai/table/generate",
                    json=request_body
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"Table generated successfully: {element_id}")
                return result

        except httpx.TimeoutException:
            logger.error(f"Table service timeout for element {element_id}")
            return {
                "success": False,
                "error": {
                    "code": "TIMEOUT",
                    "message": "Table generation timed out. Please try again.",
                    "retryable": True
                }
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"Table service HTTP error: {e.response.status_code}")
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
                        "message": f"Table service returned status {e.response.status_code}",
                        "retryable": e.response.status_code >= 500
                    }
                }

        except httpx.ConnectError:
            logger.error(f"Failed to connect to Table service at {self.base_url}")
            return {
                "success": False,
                "error": {
                    "code": "CONNECTION_ERROR",
                    "message": "Unable to connect to Table AI service. Please try again later.",
                    "retryable": True
                }
            }

        except Exception as e:
            logger.exception(f"Unexpected error in table generation: {e}")
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
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Transform existing table content.

        Args:
            source_content: HTML table to transform
            transformation: Type of transformation:
                - add_column: Add a new column
                - add_row: Add a new row
                - remove_column: Remove a column (options.columnIndex)
                - remove_row: Remove a row (options.rowIndex)
                - sort: Sort by column (options.sortColumn, options.sortDirection)
                - summarize: Add summary (options.summarizeType, options.summarizeColumns)
                - transpose: Swap rows and columns
                - expand: Expand content (options.focusArea)
                - merge_cells: Merge cells (options.cells)
                - split_column: Split a column (options.columnIndex, options.splitCount)
            presentation_id: Presentation identifier
            slide_id: Slide identifier
            element_id: Element identifier
            context: Presentation context
            constraints: Grid dimensions
            options: Transformation-specific options

        Returns:
            Dict with success status and transformed html_content or error
        """
        request_body = {
            "sourceContent": source_content,
            "transformation": transformation,
            "presentationId": presentation_id,
            "slideId": slide_id,
            "elementId": element_id,
            "context": context,
            "constraints": constraints
        }

        if options:
            request_body["options"] = options

        logger.info(f"Transforming table: transformation={transformation}, element={element_id}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/ai/table/transform",
                    json=request_body
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"Table transformed successfully: {element_id}")
                return result

        except httpx.TimeoutException:
            logger.error(f"Table transform timeout for element {element_id}")
            return {
                "success": False,
                "error": {
                    "code": "TIMEOUT",
                    "message": "Table transformation timed out. Please try again.",
                    "retryable": True
                }
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"Table transform HTTP error: {e.response.status_code}")
            try:
                error_data = e.response.json()
                return {"success": False, "error": error_data.get("error", {"code": f"HTTP_{e.response.status_code}", "message": str(e), "retryable": e.response.status_code >= 500})}
            except Exception:
                return {"success": False, "error": {"code": f"HTTP_{e.response.status_code}", "message": f"Table service returned status {e.response.status_code}", "retryable": e.response.status_code >= 500}}

        except httpx.ConnectError:
            logger.error(f"Failed to connect to Table service at {self.base_url}")
            return {"success": False, "error": {"code": "CONNECTION_ERROR", "message": "Unable to connect to Table AI service.", "retryable": True}}

        except Exception as e:
            logger.exception(f"Unexpected error in table transformation: {e}")
            return {"success": False, "error": {"code": "INTERNAL_ERROR", "message": str(e), "retryable": False}}

    async def analyze(
        self,
        source_content: str,
        element_id: str,
        context: Dict[str, Any],
        analysis_type: str = "summary"
    ) -> Dict[str, Any]:
        """
        Analyze table data.

        Args:
            source_content: HTML table to analyze
            element_id: Element identifier
            context: Presentation context
            analysis_type: Type of analysis (summary, trends, statistics)

        Returns:
            Dict with success status and analysis results or error
        """
        request_body = {
            "sourceContent": source_content,
            "elementId": element_id,
            "context": context,
            "analysisType": analysis_type
        }

        logger.info(f"Analyzing table: type={analysis_type}, element={element_id}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/ai/table/analyze",
                    json=request_body
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"Table analyzed successfully: {element_id}")
                return result

        except httpx.TimeoutException:
            logger.error(f"Table analyze timeout for element {element_id}")
            return {"success": False, "error": {"code": "TIMEOUT", "message": "Table analysis timed out.", "retryable": True}}

        except httpx.HTTPStatusError as e:
            logger.error(f"Table analyze HTTP error: {e.response.status_code}")
            try:
                error_data = e.response.json()
                return {"success": False, "error": error_data.get("error", {"code": f"HTTP_{e.response.status_code}", "message": str(e), "retryable": e.response.status_code >= 500})}
            except Exception:
                return {"success": False, "error": {"code": f"HTTP_{e.response.status_code}", "message": f"Table service returned status {e.response.status_code}", "retryable": e.response.status_code >= 500}}

        except httpx.ConnectError:
            logger.error(f"Failed to connect to Table service at {self.base_url}")
            return {"success": False, "error": {"code": "CONNECTION_ERROR", "message": "Unable to connect to Table AI service.", "retryable": True}}

        except Exception as e:
            logger.exception(f"Unexpected error in table analysis: {e}")
            return {"success": False, "error": {"code": "INTERNAL_ERROR", "message": str(e), "retryable": False}}

    def get_presets(self) -> Dict[str, Any]:
        """
        Get available table presets.

        Returns:
            Dict with presets array and descriptions
        """
        return {
            "success": True,
            "presets": [
                {"name": name, "description": desc}
                for name, desc in TABLE_PRESETS.items()
            ],
            "defaultPreset": "professional"
        }
