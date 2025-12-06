"""
Pydantic models for Visual Elements Orchestrator

Defines request/response models for all visual element types:
- Charts (Analytics Microservice v3.0)
- Diagrams (Diagram Generator v3.0)
- Text & Tables (Text Table Builder v1.2)
- Images (Image Builder v2.0)
- Infographics (Illustrator v1.0)
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


# ============================================================================
# Shared Models
# ============================================================================

class GridPosition(BaseModel):
    """
    CSS Grid position from Layout Service.

    Layout Service uses 24×14 grid.
    AI Services use 12×8 grid.

    Example:
        grid_row: "4/14" (spans rows 4 to 13)
        grid_column: "8/24" (spans columns 8 to 23)
    """
    grid_row: str = Field(..., description="CSS grid-row value, e.g., '4/14'")
    grid_column: str = Field(..., description="CSS grid-column value, e.g., '8/24'")


class ElementContext(BaseModel):
    """Context information about the presentation and slide"""
    presentation_id: str
    presentation_title: str
    slide_id: str
    slide_index: int
    slide_count: int = Field(default=1, ge=1, description="Total number of slides in the deck")
    slide_title: Optional[str] = None
    industry: Optional[str] = None
    time_frame: Optional[str] = None
    presentation_theme: Optional[str] = Field(default=None, description="Theme/template of the presentation")
    brand_colors: Optional[List[str]] = Field(default=None, description="Brand colors as hex codes")


class ErrorDetail(BaseModel):
    """Error information for failed operations"""
    code: str
    message: str
    retryable: bool = False
    suggestion: Optional[str] = None


# ============================================================================
# Chart Models (Analytics Microservice v3.0)
# ============================================================================

class ChartType(str, Enum):
    """Supported chart types"""
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    DOUGHNUT = "doughnut"
    AREA = "area"
    SCATTER = "scatter"
    RADAR = "radar"
    POLAR_AREA = "polarArea"
    BUBBLE = "bubble"
    TREEMAP = "treemap"


class ChartPalette(str, Enum):
    """Available color palettes for charts"""
    DEFAULT = "default"
    PROFESSIONAL = "professional"
    VIBRANT = "vibrant"
    PASTEL = "pastel"
    MONOCHROME = "monochrome"
    SEQUENTIAL = "sequential"
    DIVERGING = "diverging"
    CATEGORICAL = "categorical"


class ChartDataPoint(BaseModel):
    """A single data point for charts"""
    label: str
    value: float


class ChartGenerateRequest(BaseModel):
    """
    Request to generate a Chart.js configuration.

    The orchestrator will:
    1. Convert grid position to Chart AI dimensions
    2. Forward request to Chart AI Service
    3. Return Chart.js config ready for rendering
    """
    element_id: str = Field(..., description="Unique identifier for the chart element")
    context: ElementContext
    position: GridPosition
    prompt: str = Field(..., min_length=1, max_length=2000, description="Description of chart data")
    chart_type: ChartType
    palette: ChartPalette = ChartPalette.DEFAULT
    data: Optional[List[ChartDataPoint]] = Field(
        None,
        description="User-provided data points. If not provided, set generate_data=true"
    )
    generate_data: bool = Field(
        False,
        description="Generate synthetic data if no data is provided"
    )
    show_legend: bool = True
    show_data_labels: bool = False
    legend_position: Optional[str] = Field(
        None,
        description="Legend position: top, bottom, left, right"
    )
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    stacked: bool = False


class ChartMetadata(BaseModel):
    """Metadata about the generated chart"""
    chart_type: str
    data_point_count: int
    dataset_count: int
    suggested_title: Optional[str] = None
    data_range: Optional[Dict[str, float]] = None


class ChartInsights(BaseModel):
    """AI-generated insights about the chart data"""
    trend: Optional[str] = None  # increasing, decreasing, stable, volatile
    outliers: Optional[List[int]] = None
    highlights: Optional[List[str]] = None


class ChartGenerateResponse(BaseModel):
    """Response from chart generation"""
    success: bool
    element_id: str
    chart_config: Optional[Dict[str, Any]] = Field(
        None,
        description="Chart.js configuration object ready for rendering"
    )
    raw_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Raw data in Chart.js format"
    )
    metadata: Optional[ChartMetadata] = None
    insights: Optional[ChartInsights] = None
    generation_id: Optional[str] = None
    error: Optional[ErrorDetail] = None
    # Layout Service injection status
    injected: Optional[bool] = Field(
        None,
        description="True if content was successfully injected into Layout Service"
    )
    injection_error: Optional[str] = Field(
        None,
        description="Error message if injection to Layout Service failed"
    )


# ============================================================================
# Diagram Models (Diagram Generator v3.0)
# ============================================================================

class DiagramType(str, Enum):
    """Supported diagram types (11 types)"""
    FLOWCHART = "flowchart"
    SEQUENCE = "sequence"
    CLASS = "class"
    STATE = "state"
    ER = "er"
    GANTT = "gantt"
    USER_JOURNEY = "userjourney"
    GIT_GRAPH = "gitgraph"
    MINDMAP = "mindmap"
    PIE = "pie"
    TIMELINE = "timeline"


class DiagramDirection(str, Enum):
    """Diagram layout direction"""
    TB = "TB"  # Top to bottom
    BT = "BT"  # Bottom to top
    LR = "LR"  # Left to right
    RL = "RL"  # Right to left


class DiagramTheme(str, Enum):
    """Mermaid diagram themes"""
    DEFAULT = "default"
    DARK = "dark"
    FOREST = "forest"
    NEUTRAL = "neutral"
    BASE = "base"


class DiagramComplexity(str, Enum):
    """Diagram complexity levels"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    DETAILED = "detailed"


class DiagramGenerateRequest(BaseModel):
    """
    Request to generate a diagram.

    Uses async polling pattern:
    1. Submit job → get jobId
    2. Poll status until complete/failed
    3. Return SVG result
    """
    element_id: str = Field(..., description="Unique identifier for the diagram element")
    context: ElementContext
    position: GridPosition
    prompt: str = Field(..., min_length=1, max_length=2000, description="Description of diagram")
    diagram_type: DiagramType
    direction: DiagramDirection = DiagramDirection.TB
    theme: DiagramTheme = DiagramTheme.DEFAULT
    complexity: DiagramComplexity = DiagramComplexity.MODERATE
    mermaid_code: Optional[str] = Field(
        None,
        description="Existing Mermaid code to render (bypasses AI generation)"
    )


class DiagramJobStatus(str, Enum):
    """Diagram generation job status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DiagramStatusResponse(BaseModel):
    """Response from diagram job status check"""
    job_id: str
    status: DiagramJobStatus
    progress: Optional[int] = None  # 0-100
    mermaid_code: Optional[str] = None
    svg_content: Optional[str] = None
    error: Optional[str] = None


class DiagramGenerateResponse(BaseModel):
    """Response from diagram generation"""
    success: bool
    element_id: str
    job_id: Optional[str] = Field(None, description="Job ID for async polling")
    mermaid_code: Optional[str] = None
    svg_content: Optional[str] = None
    diagram_type: Optional[str] = None
    error: Optional[ErrorDetail] = None
    # Layout Service injection status
    injected: Optional[bool] = Field(
        None,
        description="True if content was successfully injected into Layout Service"
    )
    injection_error: Optional[str] = Field(
        None,
        description="Error message if injection to Layout Service failed"
    )


class DiagramTypeInfo(BaseModel):
    """Information about a diagram type"""
    type: str
    name: str
    description: str
    min_grid_width: int
    min_grid_height: int
    supports_direction: bool


# ============================================================================
# Text Models (Text Table Builder v1.2)
# ============================================================================

class TextTone(str, Enum):
    """Text generation tones"""
    PROFESSIONAL = "professional"
    CONVERSATIONAL = "conversational"
    ACADEMIC = "academic"
    PERSUASIVE = "persuasive"
    CASUAL = "casual"
    TECHNICAL = "technical"


class TextFormat(str, Enum):
    """Text output formats"""
    PARAGRAPH = "paragraph"
    BULLETS = "bullets"
    NUMBERED = "numbered"
    HEADLINE = "headline"
    QUOTE = "quote"
    MIXED = "mixed"


class TextTransformation(str, Enum):
    """Text transformation types (10 types)"""
    EXPAND = "expand"
    CONDENSE = "condense"
    SIMPLIFY = "simplify"
    FORMALIZE = "formalize"
    CASUALIZE = "casualize"
    BULLETIZE = "bulletize"
    PARAGRAPHIZE = "paragraphize"
    REPHRASE = "rephrase"
    PROOFREAD = "proofread"
    TRANSLATE = "translate"


class TextGenerateRequest(BaseModel):
    """Request to generate text content"""
    element_id: str = Field(..., description="Unique identifier for the text element")
    context: ElementContext
    position: GridPosition
    prompt: str = Field(..., min_length=1, max_length=2000, description="Description of text content")
    tone: TextTone = TextTone.PROFESSIONAL
    format: TextFormat = TextFormat.PARAGRAPH
    max_words: Optional[int] = None
    language: Optional[str] = Field("en", description="ISO language code")


class TextGenerateResponse(BaseModel):
    """Response from text generation"""
    success: bool
    element_id: str
    html_content: Optional[str] = Field(None, description="Generated HTML content")
    plain_text: Optional[str] = Field(None, description="Plain text version")
    word_count: Optional[int] = None
    character_count: Optional[int] = None
    error: Optional[ErrorDetail] = None
    # Layout Service injection status
    injected: Optional[bool] = Field(
        None,
        description="True if content was successfully injected into Layout Service"
    )
    injection_error: Optional[str] = Field(
        None,
        description="Error message if injection to Layout Service failed"
    )


class TextTransformRequest(BaseModel):
    """Request to transform existing text"""
    element_id: str
    context: ElementContext
    position: GridPosition
    source_content: str = Field(..., description="HTML content to transform")
    transformation: TextTransformation
    target_language: Optional[str] = Field(None, description="For translate transformation")
    intensity: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Transformation intensity (0.0-1.0)"
    )


class TextTransformResponse(BaseModel):
    """Response from text transformation"""
    success: bool
    element_id: str
    html_content: Optional[str] = None
    transformation_applied: Optional[str] = None
    word_count: Optional[int] = None
    error: Optional[ErrorDetail] = None
    # Layout Service injection status
    injected: Optional[bool] = Field(
        None,
        description="True if content was successfully injected into Layout Service"
    )
    injection_error: Optional[str] = Field(
        None,
        description="Error message if injection to Layout Service failed"
    )


class TextAutofitRequest(BaseModel):
    """Request to auto-fit text to container size"""
    element_id: str
    context: ElementContext
    position: GridPosition
    source_content: str = Field(..., description="HTML content to fit")
    target_characters: Optional[int] = None
    preserve_structure: bool = True


class TextAutofitResponse(BaseModel):
    """Response from text autofit"""
    success: bool
    element_id: str
    html_content: Optional[str] = None
    original_length: Optional[int] = None
    fitted_length: Optional[int] = None
    reduction_percentage: Optional[float] = None
    error: Optional[ErrorDetail] = None
    # Layout Service injection status
    injected: Optional[bool] = Field(
        None,
        description="True if content was successfully injected into Layout Service"
    )
    injection_error: Optional[str] = Field(
        None,
        description="Error message if injection to Layout Service failed"
    )


class TextConstraints(BaseModel):
    """Text constraints for a given grid size"""
    grid_width: int
    grid_height: int
    max_characters: int
    max_lines: int
    recommended_font_size: str
    max_bullets: Optional[int] = None


# ============================================================================
# Table Models (Text Table Builder v1.2)
# ============================================================================

class TablePreset(str, Enum):
    """Table style presets (6 types)"""
    MINIMAL = "minimal"
    BORDERED = "bordered"
    STRIPED = "striped"
    MODERN = "modern"
    PROFESSIONAL = "professional"
    COLORFUL = "colorful"


class TableTransformationType(str, Enum):
    """Table transformation types (10 types)"""
    ADD_COLUMN = "add_column"
    ADD_ROW = "add_row"
    REMOVE_COLUMN = "remove_column"
    REMOVE_ROW = "remove_row"
    SORT = "sort"
    SUMMARIZE = "summarize"
    TRANSPOSE = "transpose"
    EXPAND = "expand"
    MERGE_CELLS = "merge_cells"
    SPLIT_COLUMN = "split_column"


class TableSortDirection(str, Enum):
    """Table sort directions"""
    ASC = "asc"
    DESC = "desc"


class TableSummarizeType(str, Enum):
    """Table summarize calculation types"""
    SUM = "sum"
    AVG = "avg"
    COUNT = "count"
    MIN = "min"
    MAX = "max"


class TableGenerateRequest(BaseModel):
    """Request to generate a table"""
    element_id: str = Field(..., description="Unique identifier for the table element")
    context: ElementContext
    position: GridPosition
    prompt: str = Field(..., min_length=1, max_length=2000, description="Description of table content")
    preset: TablePreset = TablePreset.PROFESSIONAL
    columns: Optional[int] = Field(None, ge=1, le=10, description="Number of columns")
    rows: Optional[int] = Field(None, ge=1, le=20, description="Number of data rows")
    has_header: bool = True
    data: Optional[List[List[str]]] = Field(
        None,
        description="Existing data as 2D array (first row is header if has_header=true)"
    )


class TableGenerateResponse(BaseModel):
    """Response from table generation"""
    success: bool
    element_id: str
    html_content: Optional[str] = Field(None, description="Generated HTML table")
    columns: Optional[int] = None
    rows: Optional[int] = None
    preset_applied: Optional[str] = None
    error: Optional[ErrorDetail] = None
    # Layout Service injection status
    injected: Optional[bool] = Field(
        None,
        description="True if content was successfully injected into Layout Service"
    )
    injection_error: Optional[str] = Field(
        None,
        description="Error message if injection to Layout Service failed"
    )


class TableTransformOptions(BaseModel):
    """Options for table transformations"""
    # For add_column/add_row
    content: Optional[str] = None
    position: Optional[int] = None

    # For remove_column/remove_row
    column_index: Optional[int] = None
    row_index: Optional[int] = None

    # For sort
    sort_column: Optional[int] = None
    sort_direction: TableSortDirection = TableSortDirection.ASC

    # For summarize
    summarize_type: Optional[TableSummarizeType] = None
    summarize_columns: Optional[List[int]] = None

    # For expand
    focus_area: Optional[str] = None

    # For merge_cells
    cells: Optional[List[Dict[str, int]]] = None

    # For split_column
    split_count: Optional[int] = None


class TableTransformRequest(BaseModel):
    """Request to transform existing table"""
    element_id: str
    context: ElementContext
    position: GridPosition
    source_content: str = Field(..., description="HTML table to transform")
    transformation: TableTransformationType
    options: Optional[TableTransformOptions] = None


class TableTransformResponse(BaseModel):
    """Response from table transformation"""
    success: bool
    element_id: str
    html_content: Optional[str] = None
    transformation_applied: Optional[str] = None
    columns: Optional[int] = None
    rows: Optional[int] = None
    error: Optional[ErrorDetail] = None
    # Layout Service injection status
    injected: Optional[bool] = Field(
        None,
        description="True if content was successfully injected into Layout Service"
    )
    injection_error: Optional[str] = Field(
        None,
        description="Error message if injection to Layout Service failed"
    )


class TableAnalyzeRequest(BaseModel):
    """Request to analyze table data"""
    element_id: str
    context: ElementContext
    source_content: str = Field(..., description="HTML table to analyze")
    analysis_type: Optional[str] = Field(
        "summary",
        description="Type of analysis: summary, trends, statistics"
    )


class TableAnalyzeResponse(BaseModel):
    """Response from table analysis"""
    success: bool
    element_id: str
    summary: Optional[str] = None
    statistics: Optional[Dict[str, Any]] = None
    trends: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None
    error: Optional[ErrorDetail] = None


# ============================================================================
# Image Models (Image Builder v2.0)
# ============================================================================

class ImageStyle(str, Enum):
    """Image generation styles (5 types)"""
    REALISTIC = "realistic"
    ILLUSTRATION = "illustration"
    ABSTRACT = "abstract"
    MINIMAL = "minimal"
    PHOTO = "photo"


class ImageQuality(str, Enum):
    """Image quality tiers with credit costs"""
    DRAFT = "draft"          # 512px, 1 credit
    STANDARD = "standard"    # 1024px, 2 credits
    HIGH = "high"            # 1536px, 4 credits
    ULTRA = "ultra"          # 2048px, 8 credits


class ImageAspectRatio(str, Enum):
    """Common image aspect ratios"""
    SQUARE = "1:1"
    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"
    WIDE = "21:9"
    STANDARD = "4:3"


class ImageGenerateRequest(BaseModel):
    """Request to generate an image"""
    element_id: str = Field(..., description="Unique identifier for the image element")
    context: ElementContext
    position: GridPosition
    prompt: str = Field(..., min_length=1, max_length=2000, description="Image description")
    style: ImageStyle = ImageStyle.REALISTIC
    quality: ImageQuality = ImageQuality.STANDARD
    aspect_ratio: ImageAspectRatio = ImageAspectRatio.LANDSCAPE
    negative_prompt: Optional[str] = Field(
        None,
        description="What to avoid in the image"
    )
    seed: Optional[int] = Field(
        None,
        description="Random seed for reproducibility"
    )


class ImageCreditsInfo(BaseModel):
    """Image credits information"""
    used: int
    remaining: int
    total: int
    quality_costs: Dict[str, int] = {
        "draft": 1,
        "standard": 2,
        "high": 4,
        "ultra": 8
    }


class ImageGenerateResponse(BaseModel):
    """Response from image generation"""
    success: bool
    element_id: str
    image_url: Optional[str] = Field(None, description="URL of generated image")
    image_base64: Optional[str] = Field(None, description="Base64 encoded image")
    alt_text: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    style_applied: Optional[str] = None
    quality_applied: Optional[str] = None
    credits_used: Optional[int] = None
    credits_remaining: Optional[int] = None
    seed_used: Optional[int] = None
    error: Optional[ErrorDetail] = None
    # Layout Service injection status
    injected: Optional[bool] = Field(
        None,
        description="True if content was successfully injected into Layout Service"
    )
    injection_error: Optional[str] = Field(
        None,
        description="Error message if injection to Layout Service failed"
    )


class ImageStyleInfo(BaseModel):
    """Information about an image style"""
    style: str
    name: str
    description: str
    best_for: List[str]


# ============================================================================
# Infographic Models (Illustrator v1.0)
# ============================================================================

class InfographicType(str, Enum):
    """
    Infographic types (14 total)

    Template-based (HTML, 6 types):
    - pyramid, funnel, concentric_circles, concept_spread, venn, comparison

    Dynamic SVG (Gemini 2.5 Pro, 8 types):
    - timeline, process, statistics, hierarchy, list, cycle, matrix, roadmap
    """
    # Template-based (HTML)
    PYRAMID = "pyramid"
    FUNNEL = "funnel"
    CONCENTRIC_CIRCLES = "concentric_circles"
    CONCEPT_SPREAD = "concept_spread"
    VENN = "venn"
    COMPARISON = "comparison"

    # Dynamic SVG
    TIMELINE = "timeline"
    PROCESS = "process"
    STATISTICS = "statistics"
    HIERARCHY = "hierarchy"
    LIST = "list"
    CYCLE = "cycle"
    MATRIX = "matrix"
    ROADMAP = "roadmap"


class InfographicColorScheme(str, Enum):
    """Color schemes for infographics"""
    PROFESSIONAL = "professional"
    VIBRANT = "vibrant"
    PASTEL = "pastel"
    MONOCHROME = "monochrome"
    WARM = "warm"
    COOL = "cool"


class InfographicIconStyle(str, Enum):
    """Icon styles for infographics"""
    OUTLINED = "outlined"
    FILLED = "filled"
    DUOTONE = "duotone"
    MINIMAL = "minimal"


class InfographicGenerateRequest(BaseModel):
    """Request to generate an infographic"""
    element_id: str = Field(..., description="Unique identifier for the infographic element")
    context: ElementContext
    position: GridPosition
    prompt: str = Field(..., min_length=1, max_length=2000, description="Description of infographic")
    infographic_type: InfographicType
    color_scheme: InfographicColorScheme = InfographicColorScheme.PROFESSIONAL
    icon_style: InfographicIconStyle = InfographicIconStyle.OUTLINED
    item_count: Optional[int] = Field(
        None,
        ge=2,
        le=15,
        description="Number of items (type-dependent limits)"
    )
    items: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Pre-defined items with title, description, icon, etc."
    )
    generate_data: bool = Field(
        False,
        description="Generate sample data if no items provided"
    )


class InfographicGeneratorType(str, Enum):
    """Infographic generator types"""
    TEMPLATE = "template"  # HTML-based templates
    SVG = "svg"           # Dynamic SVG generation


class InfographicGenerateResponse(BaseModel):
    """Response from infographic generation"""
    success: bool
    element_id: str
    html_content: Optional[str] = Field(None, description="HTML content (for template types)")
    svg_content: Optional[str] = Field(None, description="SVG content (for dynamic types)")
    generator_type: Optional[InfographicGeneratorType] = None
    infographic_type: Optional[str] = None
    item_count: Optional[int] = None
    color_scheme_applied: Optional[str] = None
    error: Optional[ErrorDetail] = None
    # Layout Service injection status
    injected: Optional[bool] = Field(
        None,
        description="True if content was successfully injected into Layout Service"
    )
    injection_error: Optional[str] = Field(
        None,
        description="Error message if injection to Layout Service failed"
    )


class InfographicTypeInfo(BaseModel):
    """Information about an infographic type"""
    type: str
    name: str
    description: str
    generator: InfographicGeneratorType
    min_grid_width: int
    min_grid_height: int
    min_items: int
    max_items: int
    supports_icons: bool


# ============================================================================
# Generic Response for Health/Status Endpoints
# ============================================================================

class ServiceHealth(BaseModel):
    """Health status of an AI service"""
    service: str
    status: str  # healthy, degraded, unhealthy
    latency_ms: Optional[float] = None
    last_check: Optional[str] = None
    error: Optional[str] = None


class OrchestratorHealth(BaseModel):
    """Overall orchestrator health status"""
    status: str
    version: str
    services: Dict[str, ServiceHealth]


# ============================================================================
# Batch/Multi-element Request Models
# ============================================================================

class ElementType(str, Enum):
    """Types of visual elements"""
    CHART = "chart"
    DIAGRAM = "diagram"
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    INFOGRAPHIC = "infographic"


class BatchElementRequest(BaseModel):
    """Single element in a batch request"""
    element_type: ElementType
    element_id: str
    context: ElementContext
    position: GridPosition
    config: Dict[str, Any] = Field(..., description="Type-specific configuration")


class BatchGenerateRequest(BaseModel):
    """Request to generate multiple elements"""
    elements: List[BatchElementRequest]
    parallel: bool = Field(True, description="Process elements in parallel")


class BatchElementResult(BaseModel):
    """Result for a single element in batch"""
    element_id: str
    element_type: ElementType
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[ErrorDetail] = None


class BatchGenerateResponse(BaseModel):
    """Response from batch generation"""
    success: bool
    total: int
    succeeded: int
    failed: int
    results: List[BatchElementResult]
