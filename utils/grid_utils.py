"""
Grid conversion utilities for Visual Elements Orchestrator

Converts between Layout Service grid positions (CSS Grid) and
Chart AI Service grid dimensions.

Layout Service Grid: 24 columns x 14 rows
Chart AI Grid: 12 columns x 8 rows
"""

import re
from typing import Dict, Tuple

from models import GridPosition


def parse_grid_value(value: str) -> Tuple[int, int]:
    """
    Parse a CSS grid value like "4/14" or "4 / 14" into start and end integers.

    Args:
        value: CSS grid value (e.g., "4/14", "4 / 14")

    Returns:
        Tuple of (start, end) as integers

    Raises:
        ValueError: If the value cannot be parsed
    """
    match = re.match(r'(\d+)\s*/\s*(\d+)', value.strip())
    if not match:
        raise ValueError(f"Invalid grid value: {value}")
    return int(match.group(1)), int(match.group(2))


def get_grid_dimensions(position: GridPosition) -> Dict[str, int]:
    """
    Get the raw grid dimensions (spans) from a GridPosition.

    Args:
        position: GridPosition with grid_row and grid_column

    Returns:
        Dict with row_span and col_span
    """
    try:
        row_start, row_end = parse_grid_value(position.grid_row)
        col_start, col_end = parse_grid_value(position.grid_column)

        return {
            "row_start": row_start,
            "row_end": row_end,
            "col_start": col_start,
            "col_end": col_end,
            "row_span": row_end - row_start,
            "col_span": col_end - col_start
        }
    except ValueError:
        # Return default dimensions if parsing fails
        return {
            "row_start": 4,
            "row_end": 12,
            "col_start": 4,
            "col_end": 20,
            "row_span": 8,
            "col_span": 16
        }


def convert_grid_position(position: GridPosition) -> Dict[str, int]:
    """
    Convert Layout Service grid position to Chart AI grid dimensions.

    Layout Service uses CSS Grid:
        - gridRow="4/14" (rows 4-13, 10 row span)
        - gridColumn="8/24" (cols 8-23, 16 col span)
        - Total grid: 24 columns x 14 rows

    Chart AI expects:
        - gridWidth (1-12)
        - gridHeight (1-8)

    Conversion:
        - Layout 24 cols -> Chart AI 12 cols (divide by 2)
        - Layout 14 rows -> Chart AI 8 rows (multiply by 8/14)

    Args:
        position: GridPosition from Layout Service

    Returns:
        Dict with "width" and "height" for Chart AI
    """
    dims = get_grid_dimensions(position)

    row_span = dims["row_span"]
    col_span = dims["col_span"]

    # Convert to Chart AI grid dimensions
    # Layout: 24 cols -> Chart: 12 cols (divide by 2)
    grid_width = round(col_span / 2)

    # Layout: 14 rows -> Chart: 8 rows (multiply by 8/14 = 0.571)
    grid_height = round(row_span * 8 / 14)

    # Clamp to valid ranges
    grid_width = max(1, min(12, grid_width))
    grid_height = max(1, min(8, grid_height))

    return {
        "width": grid_width,
        "height": grid_height
    }


def calculate_grid_area(position: GridPosition) -> int:
    """
    Calculate the grid area for size classification.

    Chart AI uses these size categories:
        - Small: area <= 16
        - Medium: 16 < area <= 48
        - Large: area > 48

    Args:
        position: GridPosition from Layout Service

    Returns:
        Grid area (width * height in Chart AI units)
    """
    dims = convert_grid_position(position)
    return dims["width"] * dims["height"]


def get_size_category(position: GridPosition) -> str:
    """
    Get the size category (small/medium/large) for a grid position.

    Args:
        position: GridPosition from Layout Service

    Returns:
        Size category string: "small", "medium", or "large"
    """
    area = calculate_grid_area(position)

    if area <= 16:
        return "small"
    elif area <= 48:
        return "medium"
    else:
        return "large"


def validate_minimum_size(position: GridPosition, chart_type: str) -> Dict[str, any]:
    """
    Validate that the grid position meets minimum size requirements for a chart type.

    Minimum sizes per chart type (in Chart AI grid units):
        - bar: 3x3
        - line: 3x2
        - pie: 3x3
        - doughnut: 3x3
        - area: 3x2
        - scatter: 4x3
        - radar: 4x4
        - polarArea: 3x3

    Args:
        position: GridPosition from Layout Service
        chart_type: Type of chart to validate

    Returns:
        Dict with "valid" bool and error details if invalid
    """
    MINIMUM_SIZES = {
        "bar": {"width": 3, "height": 3},
        "line": {"width": 3, "height": 2},
        "pie": {"width": 3, "height": 3},
        "doughnut": {"width": 3, "height": 3},
        "area": {"width": 3, "height": 2},
        "scatter": {"width": 4, "height": 3},
        "radar": {"width": 4, "height": 4},
        "polarArea": {"width": 3, "height": 3}
    }

    dims = convert_grid_position(position)
    min_size = MINIMUM_SIZES.get(chart_type, {"width": 3, "height": 3})

    if dims["width"] < min_size["width"] or dims["height"] < min_size["height"]:
        return {
            "valid": False,
            "current_width": dims["width"],
            "current_height": dims["height"],
            "min_width": min_size["width"],
            "min_height": min_size["height"],
            "message": f"Grid size {dims['width']}x{dims['height']} is too small for {chart_type} chart. Minimum size is {min_size['width']}x{min_size['height']}."
        }

    return {
        "valid": True,
        "width": dims["width"],
        "height": dims["height"]
    }
