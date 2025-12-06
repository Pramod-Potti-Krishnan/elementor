"""
Image AI Service Client

Handles communication with the Image Builder v2.0 endpoints.

Endpoints:
    - POST /api/ai/image/generate - Generate image
    - GET /api/ai/image/styles - Get available styles
    - GET /api/ai/image/credits/{presentationId} - Check credits
"""

import logging
from typing import Any, Dict, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)


# Image quality tiers with credit costs
IMAGE_QUALITY_CREDITS = {
    "draft": {"resolution": 512, "credits": 1},
    "standard": {"resolution": 1024, "credits": 2},
    "high": {"resolution": 1536, "credits": 4},
    "ultra": {"resolution": 2048, "credits": 8}
}

# Image styles with descriptions
IMAGE_STYLES = {
    "realistic": {
        "name": "Realistic",
        "description": "Photo-realistic imagery",
        "bestFor": ["Business", "Corporate", "Marketing"]
    },
    "illustration": {
        "name": "Illustration",
        "description": "Hand-drawn illustration style",
        "bestFor": ["Educational", "Storytelling", "Children's content"]
    },
    "abstract": {
        "name": "Abstract",
        "description": "Abstract and artistic imagery",
        "bestFor": ["Creative", "Art", "Conceptual"]
    },
    "minimal": {
        "name": "Minimal",
        "description": "Clean, minimalist design",
        "bestFor": ["Tech", "Startup", "Modern presentations"]
    },
    "photo": {
        "name": "Photo",
        "description": "High-quality photography style",
        "bestFor": ["Marketing", "Advertising", "Product showcases"]
    }
}


class ImageService:
    """
    Client for the Image AI Service.

    Features:
        - Async HTTP calls with configurable timeout
        - Credits tracking per presentation
        - Support for multiple image styles and quality tiers
        - Response caching for styles
        - Error handling with retryable status
    """

    def __init__(self):
        self.base_url = settings.IMAGE_SERVICE_URL
        self.timeout = settings.IMAGE_TIMEOUT
        self._styles_cache: Optional[Dict[str, Any]] = None

    async def generate(
        self,
        prompt: str,
        presentation_id: str,
        slide_id: str,
        element_id: str,
        context: Dict[str, Any],
        constraints: Dict[str, int],
        style: str = "realistic",
        quality: str = "standard",
        aspect_ratio: str = "16:9",
        negative_prompt: Optional[str] = None,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate an image via Image AI Service.

        Args:
            prompt: Description of the image
            presentation_id: Presentation identifier
            slide_id: Slide identifier
            element_id: Element identifier
            context: Presentation context (title, slide info)
            constraints: Grid dimensions (gridWidth, gridHeight)
            style: Image style (realistic, illustration, abstract, minimal, photo)
            quality: Quality tier (draft, standard, high, ultra)
            aspect_ratio: Aspect ratio (16:9, 4:3, 1:1, 9:16, 21:9)
            negative_prompt: What to avoid in the image
            seed: Random seed for reproducibility

        Returns:
            Dict with success status and either image_url/image_base64 or error details
        """
        # Build context object matching backend LayoutImageContext schema
        # Required fields: presentationTitle, slideIndex
        backend_context = {
            "presentationTitle": context.get("presentationTitle", "Untitled"),
            "slideIndex": context.get("slideIndex", 0),
        }
        # Optional context fields
        if context.get("presentationTheme"):
            backend_context["presentationTheme"] = context["presentationTheme"]
        if context.get("slideTitle"):
            backend_context["slideTitle"] = context["slideTitle"]
        if context.get("brandColors"):
            backend_context["brandColors"] = context["brandColors"]

        # Build config object matching backend LayoutImageConfig schema
        config = {
            "style": style,
            "aspectRatio": aspect_ratio,
            "quality": quality
        }

        # Build options object if optional fields provided
        options = {}
        if negative_prompt:
            options["negativePrompt"] = negative_prompt
        if seed is not None:
            options["seed"] = seed

        request_body = {
            "prompt": prompt,
            "presentationId": presentation_id,
            "slideId": slide_id,
            "elementId": element_id,
            "context": backend_context,
            "config": config,
            "constraints": constraints,
        }

        if options:
            request_body["options"] = options

        logger.info(f"Generating image: style={style}, quality={quality}, element={element_id}")
        logger.debug(f"Request body: {request_body}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/ai/image/generate",
                    json=request_body
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"Image generated successfully: {element_id}")
                return result

        except httpx.TimeoutException:
            logger.error(f"Image service timeout for element {element_id}")
            return {
                "success": False,
                "error": {
                    "code": "TIMEOUT",
                    "message": "Image generation timed out. Please try again.",
                    "retryable": True
                }
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"Image service HTTP error: {e.response.status_code}")
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
                        "message": f"Image service returned status {e.response.status_code}",
                        "retryable": e.response.status_code >= 500
                    }
                }

        except httpx.ConnectError:
            logger.error(f"Failed to connect to Image service at {self.base_url}")
            return {
                "success": False,
                "error": {
                    "code": "CONNECTION_ERROR",
                    "message": "Unable to connect to Image AI service. Please try again later.",
                    "retryable": True
                }
            }

        except Exception as e:
            logger.exception(f"Unexpected error in image generation: {e}")
            return {
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e),
                    "retryable": False
                }
            }

    async def get_styles(self) -> Dict[str, Any]:
        """
        Get available image styles.

        Results are cached after first successful call.

        Returns:
            Dict with styles array and their descriptions
        """
        if self._styles_cache is not None:
            logger.debug("Returning cached image styles")
            return self._styles_cache

        logger.info("Fetching image styles from service")

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/ai/image/styles")
                response.raise_for_status()
                self._styles_cache = response.json()
                return self._styles_cache

        except Exception as e:
            logger.error(f"Failed to fetch image styles: {e}")
            # Return default styles if service is unavailable
            return {
                "success": True,
                "styles": [
                    {
                        "style": key,
                        "name": value["name"],
                        "description": value["description"],
                        "bestFor": value["bestFor"]
                    }
                    for key, value in IMAGE_STYLES.items()
                ],
                "qualities": [
                    {
                        "quality": key,
                        "resolution": f"{value['resolution']}px",
                        "credits": value["credits"]
                    }
                    for key, value in IMAGE_QUALITY_CREDITS.items()
                ],
                "defaultStyle": "realistic",
                "defaultQuality": "standard",
                "_cached": False,
                "_fallback": True
            }

    async def get_credits(self, presentation_id: str) -> Dict[str, Any]:
        """
        Get image credits for a presentation.

        Args:
            presentation_id: Presentation identifier

        Returns:
            Dict with used, remaining, and total credits
        """
        logger.info(f"Fetching image credits for presentation {presentation_id}")

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.base_url}/api/ai/image/credits/{presentation_id}"
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # New presentation, return default credits
                return {
                    "success": True,
                    "presentationId": presentation_id,
                    "used": 0,
                    "remaining": 100,  # Default credit allowance
                    "total": 100,
                    "qualityCosts": {
                        "draft": 1,
                        "standard": 2,
                        "high": 4,
                        "ultra": 8
                    }
                }
            logger.error(f"Failed to fetch credits: HTTP {e.response.status_code}")
            return {
                "success": False,
                "error": {
                    "code": f"HTTP_{e.response.status_code}",
                    "message": f"Failed to fetch credits: {e.response.status_code}",
                    "retryable": e.response.status_code >= 500
                }
            }

        except Exception as e:
            logger.error(f"Failed to fetch image credits: {e}")
            return {
                "success": False,
                "error": {
                    "code": "CONNECTION_ERROR",
                    "message": "Unable to fetch image credits. Please try again later.",
                    "retryable": True
                }
            }

    def get_credit_cost(self, quality: str) -> int:
        """
        Get the credit cost for a quality tier.

        Args:
            quality: Quality tier (draft, standard, high, ultra)

        Returns:
            Credit cost for the quality tier
        """
        return IMAGE_QUALITY_CREDITS.get(quality, IMAGE_QUALITY_CREDITS["standard"])["credits"]

    def clear_cache(self):
        """Clear cached styles"""
        self._styles_cache = None
        logger.info("Image service cache cleared")
