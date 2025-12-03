"""
Layout Service Client

Handles direct content injection into Layout Service presentations.
This enables the Orchestrator to update elements directly after AI generation,
reducing latency by eliminating the frontend hop.

Layout Service API (Port 8504):
    - GET /api/presentations/{id} - Get presentation
    - PUT /api/presentations/{id}/slides/{index} - Update slide (with element arrays)
    - PUT /api/presentations/{id}/slides/{index}/textboxes/{id} - Update single textbox
    - PUT /api/presentations/{id}/slides/{index}/charts/{id} - Update single chart
    - PUT /api/presentations/{id}/slides/{index}/images/{id} - Update single image
    - PUT /api/presentations/{id}/slides/{index}/infographics/{id} - Update single infographic
    - PUT /api/presentations/{id}/slides/{index}/diagrams/{id} - Update single diagram
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)


class LayoutServiceClient:
    """
    Client for injecting AI-generated content into Layout Service presentations.

    Features:
        - Direct element updates without frontend hop
        - Support for all element types (text, chart, image, infographic, diagram)
        - Error handling with graceful fallbacks
        - Version tracking via created_by metadata
    """

    def __init__(self):
        self.base_url = settings.LAYOUT_SERVICE_URL
        self.timeout = settings.SERVICE_TIMEOUT

    async def get_presentation(self, presentation_id: str) -> Dict[str, Any]:
        """
        Get a presentation by ID.

        Args:
            presentation_id: Presentation identifier

        Returns:
            Dict with presentation data or error
        """
        logger.debug(f"Fetching presentation {presentation_id}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/presentations/{presentation_id}"
                )
                response.raise_for_status()
                return {"success": True, "data": response.json()}

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {
                    "success": False,
                    "error": f"Presentation {presentation_id} not found"
                }
            logger.error(f"Layout service HTTP error: {e.response.status_code}")
            return {
                "success": False,
                "error": f"Layout service error: {e.response.status_code}"
            }

        except httpx.ConnectError:
            logger.error(f"Failed to connect to Layout service at {self.base_url}")
            return {
                "success": False,
                "error": "Unable to connect to Layout service"
            }

        except Exception as e:
            logger.exception(f"Unexpected error fetching presentation: {e}")
            return {"success": False, "error": str(e)}

    async def get_slide(
        self,
        presentation_id: str,
        slide_index: int
    ) -> Dict[str, Any]:
        """
        Get a specific slide from a presentation.

        Args:
            presentation_id: Presentation identifier
            slide_index: Zero-based slide index

        Returns:
            Dict with slide data or error
        """
        result = await self.get_presentation(presentation_id)
        if not result["success"]:
            return result

        presentation = result["data"]
        slides = presentation.get("slides", [])

        if slide_index < 0 or slide_index >= len(slides):
            return {
                "success": False,
                "error": f"Slide index {slide_index} out of range (0-{len(slides)-1})"
            }

        return {"success": True, "data": slides[slide_index]}

    async def update_slide(
        self,
        presentation_id: str,
        slide_index: int,
        updates: Dict[str, Any],
        created_by: str = "orchestrator"
    ) -> Dict[str, Any]:
        """
        Update a slide with new content.

        Args:
            presentation_id: Presentation identifier
            slide_index: Zero-based slide index
            updates: Dict of fields to update (can include element arrays)
            created_by: Attribution for the update

        Returns:
            Dict with success status and updated slide or error
        """
        logger.info(f"Updating slide {slide_index} in presentation {presentation_id}")
        logger.debug(f"Updates: {list(updates.keys())}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Add created_by as query param
                response = await client.put(
                    f"{self.base_url}/api/presentations/{presentation_id}/slides/{slide_index}",
                    json=updates,
                    params={"created_by": created_by}
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"Slide {slide_index} updated successfully")
                return {"success": True, "data": result}

        except httpx.HTTPStatusError as e:
            logger.error(f"Layout service HTTP error: {e.response.status_code}")
            try:
                error_data = e.response.json()
                return {
                    "success": False,
                    "error": error_data.get("detail", str(e))
                }
            except Exception:
                return {
                    "success": False,
                    "error": f"Layout service error: {e.response.status_code}"
                }

        except httpx.ConnectError:
            logger.error(f"Failed to connect to Layout service at {self.base_url}")
            return {
                "success": False,
                "error": "Unable to connect to Layout service"
            }

        except Exception as e:
            logger.exception(f"Unexpected error updating slide: {e}")
            return {"success": False, "error": str(e)}

    async def update_element(
        self,
        presentation_id: str,
        slide_index: int,
        element_type: str,
        element_id: str,
        content: Dict[str, Any],
        position: Optional[Dict[str, str]] = None,
        created_by: str = "orchestrator"
    ) -> Dict[str, Any]:
        """
        Update a specific element within a slide.

        This method:
        1. Fetches the current slide
        2. Finds the element by ID in the appropriate array
        3. Updates the element's content fields
        4. Saves the updated slide

        Args:
            presentation_id: Presentation identifier
            slide_index: Zero-based slide index
            element_type: Type of element (textboxes, charts, images, infographics, diagrams)
            element_id: Element identifier
            content: Content fields to update on the element
            position: Optional grid position update
            created_by: Attribution for the update

        Returns:
            Dict with success status and updated element or error
        """
        logger.info(f"Updating {element_type} element {element_id} in slide {slide_index}")

        # First, get the current slide
        slide_result = await self.get_slide(presentation_id, slide_index)
        if not slide_result["success"]:
            return slide_result

        slide = slide_result["data"]

        # Get the element array for this type
        element_array = slide.get(element_type, [])

        # Find the element by ID
        element_found = False
        for i, element in enumerate(element_array):
            if element.get("id") == element_id:
                # Update the element with new content
                element_array[i].update(content)
                if position:
                    element_array[i]["position"] = position
                element_found = True
                break

        if not element_found:
            # Element doesn't exist - need to create it
            logger.info(f"Element {element_id} not found, will create new element")
            new_element = {
                "id": element_id,
                **content
            }
            if position:
                new_element["position"] = position
            element_array.append(new_element)

        # Update the slide with the modified element array
        updates = {element_type: element_array}

        return await self.update_slide(
            presentation_id=presentation_id,
            slide_index=slide_index,
            updates=updates,
            created_by=created_by
        )

    async def inject_chart(
        self,
        presentation_id: str,
        slide_index: int,
        element_id: str,
        chart_config: Optional[Dict[str, Any]] = None,
        chart_html: Optional[str] = None,
        chart_type: Optional[str] = None,
        position: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Inject chart content into a chart element.

        Args:
            presentation_id: Presentation identifier
            slide_index: Zero-based slide index
            element_id: Chart element identifier
            chart_config: Chart.js configuration object
            chart_html: Pre-rendered chart HTML
            chart_type: Type of chart (bar, line, pie, etc.)
            position: Optional grid position

        Returns:
            Dict with success status and result
        """
        content = {}
        if chart_config is not None:
            content["chart_config"] = chart_config
        if chart_html is not None:
            content["chart_html"] = chart_html
        if chart_type is not None:
            content["chart_type"] = chart_type

        return await self.update_element(
            presentation_id=presentation_id,
            slide_index=slide_index,
            element_type="charts",
            element_id=element_id,
            content=content,
            position=position,
            created_by="orchestrator-chart"
        )

    async def inject_diagram(
        self,
        presentation_id: str,
        slide_index: int,
        element_id: str,
        svg_content: Optional[str] = None,
        mermaid_code: Optional[str] = None,
        diagram_type: Optional[str] = None,
        position: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Inject diagram content into a diagram element.

        Args:
            presentation_id: Presentation identifier
            slide_index: Zero-based slide index
            element_id: Diagram element identifier
            svg_content: SVG markup
            mermaid_code: Mermaid diagram syntax
            diagram_type: Type of diagram
            position: Optional grid position

        Returns:
            Dict with success status and result
        """
        content = {}
        if svg_content is not None:
            content["svg_content"] = svg_content
        if mermaid_code is not None:
            content["mermaid_code"] = mermaid_code
        if diagram_type is not None:
            content["diagram_type"] = diagram_type

        return await self.update_element(
            presentation_id=presentation_id,
            slide_index=slide_index,
            element_type="diagrams",
            element_id=element_id,
            content=content,
            position=position,
            created_by="orchestrator-diagram"
        )

    async def inject_text(
        self,
        presentation_id: str,
        slide_index: int,
        element_id: str,
        html_content: str,
        position: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Inject text content into a text box element.

        Args:
            presentation_id: Presentation identifier
            slide_index: Zero-based slide index
            element_id: Text box element identifier
            html_content: HTML content
            position: Optional grid position

        Returns:
            Dict with success status and result
        """
        return await self.update_element(
            presentation_id=presentation_id,
            slide_index=slide_index,
            element_type="text_boxes",
            element_id=element_id,
            content={"content": html_content},
            position=position,
            created_by="orchestrator-text"
        )

    async def inject_table(
        self,
        presentation_id: str,
        slide_index: int,
        element_id: str,
        html_content: str,
        position: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Inject table content into a text box element.
        Tables are stored as HTML within text_boxes.

        Args:
            presentation_id: Presentation identifier
            slide_index: Zero-based slide index
            element_id: Text box element identifier
            html_content: HTML table content
            position: Optional grid position

        Returns:
            Dict with success status and result
        """
        return await self.update_element(
            presentation_id=presentation_id,
            slide_index=slide_index,
            element_type="text_boxes",
            element_id=element_id,
            content={"content": html_content},
            position=position,
            created_by="orchestrator-table"
        )

    async def inject_image(
        self,
        presentation_id: str,
        slide_index: int,
        element_id: str,
        image_url: Optional[str] = None,
        image_base64: Optional[str] = None,
        alt_text: Optional[str] = None,
        position: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Inject image content into an image element.

        Args:
            presentation_id: Presentation identifier
            slide_index: Zero-based slide index
            element_id: Image element identifier
            image_url: URL of the image
            image_base64: Base64-encoded image data
            alt_text: Alternative text for accessibility
            position: Optional grid position

        Returns:
            Dict with success status and result
        """
        content = {}
        if image_url is not None:
            content["image_url"] = image_url
        elif image_base64 is not None:
            # Convert base64 to data URI if needed
            if not image_base64.startswith("data:"):
                content["image_url"] = f"data:image/png;base64,{image_base64}"
            else:
                content["image_url"] = image_base64
        if alt_text is not None:
            content["alt_text"] = alt_text

        return await self.update_element(
            presentation_id=presentation_id,
            slide_index=slide_index,
            element_type="images",
            element_id=element_id,
            content=content,
            position=position,
            created_by="orchestrator-image"
        )

    async def inject_infographic(
        self,
        presentation_id: str,
        slide_index: int,
        element_id: str,
        svg_content: Optional[str] = None,
        html_content: Optional[str] = None,
        infographic_type: Optional[str] = None,
        items: Optional[List[Dict[str, Any]]] = None,
        position: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Inject infographic content into an infographic element.

        Args:
            presentation_id: Presentation identifier
            slide_index: Zero-based slide index
            element_id: Infographic element identifier
            svg_content: SVG content (for dynamic infographics)
            html_content: HTML content (for template infographics)
            infographic_type: Type of infographic
            items: Data items for the infographic
            position: Optional grid position

        Returns:
            Dict with success status and result
        """
        content = {}
        if svg_content is not None:
            content["svg_content"] = svg_content
        if html_content is not None:
            # Store HTML in svg_content field (Layout Service handles both)
            content["svg_content"] = html_content
        if infographic_type is not None:
            content["infographic_type"] = infographic_type
        if items is not None:
            content["items"] = items

        return await self.update_element(
            presentation_id=presentation_id,
            slide_index=slide_index,
            element_type="infographics",
            element_id=element_id,
            content=content,
            position=position,
            created_by="orchestrator-infographic"
        )

    async def health_check(self) -> Dict[str, Any]:
        """
        Check if Layout Service is available.

        Returns:
            Dict with health status
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()
                return {"success": True, "status": "healthy", "url": self.base_url}

        except Exception as e:
            logger.warning(f"Layout service health check failed: {e}")
            return {
                "success": False,
                "status": "unhealthy",
                "url": self.base_url,
                "error": str(e)
            }


# Singleton instance for use across routers
layout_service = LayoutServiceClient()
