# Visual Elements Orchestrator - Frontend API Documentation

## Overview

The Visual Elements Orchestrator (Port 8090) is the central gateway for all AI-generated content in presentations. It coordinates between the frontend, AI services, and Layout Service to provide a seamless content generation experience.

### Key Features

- **Direct Injection**: AI-generated content is automatically injected into Layout Service presentations
- **Unified Interface**: Single API for all visual element types (charts, diagrams, text, tables, images, infographics)
- **Grid Conversion**: Automatic conversion between Layout Service (24x14) and AI Service (12x8) grids
- **Error Handling**: Comprehensive error responses with retry guidance

### Architecture Flow

```
┌──────────┐    1. Generate Request      ┌─────────────────────┐
│ Frontend │ ──────────────────────────▶ │    Orchestrator     │
│ (React)  │                             │    (Port 8090)      │
└────┬─────┘                             └──────────┬──────────┘
     │                                              │
     │                                    2. Call AI Service
     │                                              │
     │                                              ▼
     │                                   ┌─────────────────────┐
     │                                   │   AI Services       │
     │                                   │ (Chart/Diagram/etc) │
     │                                   └──────────┬──────────┘
     │                                              │
     │                                    3. Generated Content
     │                                              │
     │                                              ▼
     │    5. Success + Injection Status  ┌─────────────────────┐
     │ ◀─────────────────────────────────│    Orchestrator     │
     │                                   └──────────┬──────────┘
     │                                              │
     │                                    4. Direct Injection
     │                                              │
     │                                              ▼
     │                                   ┌─────────────────────┐
     └───────────────────────────────────│   Layout Service    │
              (iframe refresh)           │   (Port 8504)       │
                                         └─────────────────────┘
```

---

## Base URL

```
http://localhost:8090
```

All endpoints return JSON. Content-Type: application/json

---

## Core Concepts

### ElementContext (Required for all requests)

```typescript
interface ElementContext {
  presentation_id: string;    // Unique presentation identifier
  presentation_title: string; // Title of the presentation
  slide_id: string;           // Unique slide identifier
  slide_index: number;        // Zero-based slide index
  slide_title?: string;       // Optional slide title
  industry?: string;          // Optional industry context
  time_frame?: string;        // Optional time frame context
}
```

### GridPosition (Required for all requests)

Layout Service uses a 24x14 grid. Positions are specified as CSS grid values:

```typescript
interface GridPosition {
  grid_row: string;    // e.g., "4/14" (rows 4 to 13)
  grid_column: string; // e.g., "8/24" (columns 8 to 23)
}
```

The orchestrator automatically converts these to AI service dimensions (12x8 grid).

### Injection Status (Included in all responses)

```typescript
interface InjectionStatus {
  injected?: boolean;         // true if content was injected into Layout Service
  injection_error?: string;   // Error message if injection failed
}
```

**Important**: Even if `injected: false`, the generation may have succeeded. Check `success: true` first, then handle injection status separately.

---

## API Reference

### Health & Status

#### GET /
Root endpoint with service overview.

**Response:**
```json
{
  "service": "Visual Elements Orchestrator",
  "version": "1.0.0",
  "status": "operational",
  "endpoints": {
    "chart": "/chart",
    "diagram": "/diagram",
    "text": "/text",
    "table": "/table",
    "image": "/image",
    "infographic": "/infographic"
  }
}
```

#### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

---

### Chart Endpoints

#### POST /chart
Generate a Chart.js configuration.

**Request:**
```json
{
  "element_id": "chart-1",
  "context": {
    "presentation_id": "pres-123",
    "presentation_title": "Q4 Report",
    "slide_id": "slide-456",
    "slide_index": 2,
    "slide_title": "Revenue Overview",
    "industry": "technology"
  },
  "position": {
    "grid_row": "4/14",
    "grid_column": "2/14"
  },
  "prompt": "Show quarterly revenue growth for 2024",
  "chart_type": "bar",
  "palette": "professional",
  "show_legend": true,
  "show_data_labels": false,
  "data": [
    {"label": "Q1", "value": 150000},
    {"label": "Q2", "value": 175000},
    {"label": "Q3", "value": 200000},
    {"label": "Q4", "value": 225000}
  ],
  "generate_data": false
}
```

**Chart Types:**
- `bar`, `line`, `pie`, `doughnut`, `area`, `scatter`, `radar`, `polarArea`, `bubble`, `treemap`

**Palettes:**
- `default`, `professional`, `vibrant`, `pastel`, `monochrome`, `sequential`, `diverging`, `categorical`

**Response:**
```json
{
  "success": true,
  "element_id": "chart-1",
  "chart_config": {
    "type": "bar",
    "data": { ... },
    "options": { ... }
  },
  "raw_data": { ... },
  "metadata": {
    "chart_type": "bar",
    "data_point_count": 4,
    "dataset_count": 1,
    "suggested_title": "Quarterly Revenue 2024"
  },
  "insights": {
    "trend": "increasing",
    "highlights": ["Consistent 15% growth each quarter"]
  },
  "injected": true,
  "injection_error": null
}
```

#### GET /chart/constraints
Get grid size constraints for all chart types.

#### GET /chart/palettes
Get available color palettes.

#### POST /chart/validate
Validate a chart request before generation.

---

### Diagram Endpoints

#### POST /diagram
Generate a Mermaid diagram with SVG output.

**Request:**
```json
{
  "element_id": "diagram-1",
  "context": {
    "presentation_id": "pres-123",
    "presentation_title": "System Architecture",
    "slide_id": "slide-789",
    "slide_index": 3
  },
  "position": {
    "grid_row": "3/12",
    "grid_column": "4/20"
  },
  "prompt": "Show user authentication flow with login, 2FA, and session management",
  "diagram_type": "flowchart",
  "direction": "TB",
  "theme": "default",
  "complexity": "moderate"
}
```

**Diagram Types:**
- `flowchart`, `sequence`, `class`, `state`, `er`, `gantt`, `userjourney`, `gitgraph`, `mindmap`, `pie`, `timeline`

**Directions:**
- `TB` (top-bottom), `BT` (bottom-top), `LR` (left-right), `RL` (right-left)

**Response:**
```json
{
  "success": true,
  "element_id": "diagram-1",
  "job_id": "job-abc123",
  "mermaid_code": "flowchart TB\n  A[Login] --> B{Valid?}\n  ...",
  "svg_content": "<svg>...</svg>",
  "diagram_type": "flowchart",
  "injected": true,
  "injection_error": null
}
```

#### GET /diagram/status/{job_id}
Poll diagram generation status (for manual polling).

#### GET /diagram/types
Get supported diagram types with constraints.

---

### Text Endpoints

#### POST /text
Generate text content.

**Request:**
```json
{
  "element_id": "text-1",
  "context": {
    "presentation_id": "pres-123",
    "presentation_title": "Company Overview",
    "slide_id": "slide-101",
    "slide_index": 0
  },
  "position": {
    "grid_row": "2/8",
    "grid_column": "2/12"
  },
  "prompt": "Write an executive summary of our company's mission and values",
  "tone": "professional",
  "format": "paragraph",
  "max_words": 100,
  "language": "en"
}
```

**Tones:**
- `professional`, `conversational`, `academic`, `persuasive`, `casual`, `technical`

**Formats:**
- `paragraph`, `bullets`, `numbered`, `headline`, `quote`, `mixed`

**Response:**
```json
{
  "success": true,
  "element_id": "text-1",
  "html_content": "<p>Our company is dedicated to...</p>",
  "plain_text": "Our company is dedicated to...",
  "word_count": 95,
  "character_count": 520,
  "injected": true,
  "injection_error": null
}
```

#### POST /text/transform
Transform existing text.

**Transformations:**
- `expand`, `condense`, `simplify`, `formalize`, `casualize`, `bulletize`, `paragraphize`, `rephrase`, `proofread`, `translate`

#### POST /text/autofit
Auto-fit text to container size.

#### GET /text/constraints/{width}/{height}
Get text constraints for grid dimensions.

---

### Table Endpoints

#### POST /table
Generate a styled HTML table.

**Request:**
```json
{
  "element_id": "table-1",
  "context": {
    "presentation_id": "pres-123",
    "presentation_title": "Data Analysis",
    "slide_id": "slide-202",
    "slide_index": 5
  },
  "position": {
    "grid_row": "4/12",
    "grid_column": "3/21"
  },
  "prompt": "Create a comparison table of product features across three tiers",
  "preset": "professional",
  "columns": 4,
  "rows": 5,
  "has_header": true
}
```

**Presets:**
- `minimal`, `bordered`, `striped`, `modern`, `professional`, `colorful`

**Response:**
```json
{
  "success": true,
  "element_id": "table-1",
  "html_content": "<table class='professional'>...</table>",
  "columns": 4,
  "rows": 5,
  "preset_applied": "professional",
  "injected": true,
  "injection_error": null
}
```

#### POST /table/transform
Transform existing table.

**Transformations:**
- `add_column`, `add_row`, `remove_column`, `remove_row`, `sort`, `summarize`, `transpose`, `expand`, `merge_cells`, `split_column`

#### POST /table/analyze
Analyze table data for insights.

#### GET /table/presets
Get available table style presets.

---

### Image Endpoints

#### POST /image
Generate an AI image.

**Request:**
```json
{
  "element_id": "image-1",
  "context": {
    "presentation_id": "pres-123",
    "presentation_title": "Marketing Deck",
    "slide_id": "slide-303",
    "slide_index": 7
  },
  "position": {
    "grid_row": "2/14",
    "grid_column": "14/24"
  },
  "prompt": "Modern office building with glass facade, sunny day, professional photography",
  "style": "photo",
  "quality": "standard",
  "aspect_ratio": "16:9",
  "negative_prompt": "blurry, distorted, low quality"
}
```

**Styles:**
- `realistic`, `illustration`, `abstract`, `minimal`, `photo`

**Quality (affects credits):**
- `draft` (512px, 1 credit)
- `standard` (1024px, 2 credits)
- `high` (1536px, 4 credits)
- `ultra` (2048px, 8 credits)

**Aspect Ratios:**
- `1:1`, `16:9`, `9:16`, `21:9`, `4:3`

**Response:**
```json
{
  "success": true,
  "element_id": "image-1",
  "image_url": "https://storage.example.com/images/abc123.png",
  "image_base64": null,
  "alt_text": "Modern office building with glass facade",
  "width": 1920,
  "height": 1080,
  "style_applied": "photo",
  "quality_applied": "standard",
  "credits_used": 2,
  "credits_remaining": 48,
  "seed_used": 12345,
  "injected": true,
  "injection_error": null
}
```

#### GET /image/styles
Get available image styles.

#### GET /image/credits/{presentation_id}
Get image credits for a presentation.

---

### Infographic Endpoints

#### POST /infographic
Generate an infographic.

**Request:**
```json
{
  "element_id": "infographic-1",
  "context": {
    "presentation_id": "pres-123",
    "presentation_title": "Process Overview",
    "slide_id": "slide-404",
    "slide_index": 10
  },
  "position": {
    "grid_row": "2/14",
    "grid_column": "2/24"
  },
  "prompt": "Show the 5-step customer onboarding process",
  "infographic_type": "process",
  "color_scheme": "professional",
  "icon_style": "outlined",
  "item_count": 5,
  "generate_data": true
}
```

**Infographic Types:**

Template-based (HTML):
- `pyramid`, `funnel`, `concentric_circles`, `concept_spread`, `venn`, `comparison`

Dynamic SVG:
- `timeline`, `process`, `statistics`, `hierarchy`, `list`, `cycle`, `matrix`, `roadmap`

**Color Schemes:**
- `professional`, `vibrant`, `pastel`, `monochrome`, `warm`, `cool`

**Icon Styles:**
- `outlined`, `filled`, `duotone`, `minimal`

**Response:**
```json
{
  "success": true,
  "element_id": "infographic-1",
  "html_content": null,
  "svg_content": "<svg>...</svg>",
  "generator_type": "svg",
  "infographic_type": "process",
  "item_count": 5,
  "color_scheme_applied": "professional",
  "injected": true,
  "injection_error": null
}
```

#### GET /infographic/types
Get supported infographic types with constraints.

---

## Error Handling

### Error Response Format

```json
{
  "success": false,
  "element_id": "chart-1",
  "error": {
    "code": "GRID_TOO_SMALL",
    "message": "Grid size 2x2 is too small for bar chart. Minimum size is 3x3.",
    "retryable": true,
    "suggestion": "Resize the chart element to at least 3x3 grid units."
  }
}
```

### Common Error Codes

| Code | Description | Retryable |
|------|-------------|-----------|
| `GRID_TOO_SMALL` | Element too small for content type | Yes (resize) |
| `MISSING_DATA` | Required data not provided | Yes (add data) |
| `AI_SERVICE_ERROR` | AI service unavailable | Yes (retry) |
| `INVALID_REQUEST` | Malformed request | No |
| `RATE_LIMITED` | Too many requests | Yes (wait) |
| `CREDITS_EXHAUSTED` | No image credits remaining | No |

---

## Integration Patterns

### Basic Usage

```typescript
async function generateChart(elementId: string, prompt: string) {
  const response = await fetch('http://localhost:8090/chart', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      element_id: elementId,
      context: getCurrentContext(),
      position: getElementPosition(elementId),
      prompt: prompt,
      chart_type: 'bar',
      palette: 'professional',
      generate_data: true
    })
  });

  const result = await response.json();

  if (result.success) {
    if (result.injected) {
      // Content was injected into Layout Service
      // Refresh the iframe to see changes
      refreshLayoutServiceIframe();
    } else {
      // Injection failed but we have the content
      // Manually update via postMessage
      sendToLayoutService(elementId, result.chart_config);
    }
  } else {
    handleError(result.error);
  }
}
```

### Handling Injection Status

```typescript
function handleGenerationResult(result: GenerationResponse) {
  if (!result.success) {
    showError(result.error.message);
    return;
  }

  // Content generated successfully
  showSuccess('Content generated!');

  if (result.injected) {
    // Content is already in the presentation
    // Just refresh the view
    refreshView();
  } else if (result.injection_error) {
    // Generation succeeded but injection failed
    // Show warning and offer manual injection
    showWarning(`Auto-injection failed: ${result.injection_error}`);
    offerManualInjection(result);
  }
}
```

### Error Retry Logic

```typescript
async function generateWithRetry(request: GenerationRequest, maxRetries = 3) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    const result = await generate(request);

    if (result.success) {
      return result;
    }

    if (!result.error.retryable || attempt === maxRetries) {
      throw new Error(result.error.message);
    }

    // Exponential backoff
    await sleep(1000 * Math.pow(2, attempt - 1));
  }
}
```

---

## Grid Size Reference

### Minimum Grid Sizes

| Element Type | Min Width | Min Height |
|--------------|-----------|------------|
| Bar Chart | 3 | 3 |
| Line Chart | 3 | 2 |
| Pie Chart | 3 | 3 |
| Flowchart | 3 | 2 |
| Sequence Diagram | 4 | 3 |
| Timeline Infographic | 8 | 3 |
| Process Infographic | 6 | 3 |

### Grid Conversion

Layout Service Grid (24x14) to AI Grid (12x8):
- Width: Divide by 2
- Height: Divide by ~1.75

Example:
- Layout: `grid_column: "4/16"` (12 units) → AI Width: 6
- Layout: `grid_row: "4/11"` (7 units) → AI Height: 4

---

## Best Practices

1. **Always include full context** - AI services use context for better generation
2. **Use appropriate grid sizes** - Check minimum sizes before generation
3. **Handle injection failures gracefully** - Have fallback to manual injection
4. **Use generate_data sparingly** - Real data produces better results
5. **Cache metadata requests** - Palettes, types, constraints change rarely
6. **Show loading states** - AI generation can take 2-10 seconds
7. **Provide clear prompts** - Specific prompts yield better results

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| Generation endpoints | 10 req/min per presentation |
| Metadata endpoints | 60 req/min |
| Health endpoints | No limit |

---

## Changelog

### v1.0.0 (Current)
- Initial release with all 6 element types
- Direct Layout Service injection
- Comprehensive error handling
- Grid conversion utilities
