# Deckster Frontend Integration Guide

## Complete Reference for AI-Powered Presentation Builder

**Version**: 1.0
**Last Updated**: December 2024
**Status**: Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Service URLs](#service-urls)
4. [Quick Start](#quick-start)
5. [Elementor API Reference](#elementor-api-reference)
6. [Layout Service API Reference](#layout-service-api-reference)
7. [Data Models](#data-models)
8. [Integration Patterns](#integration-patterns)
9. [Error Handling](#error-handling)
10. [Examples](#examples)
11. [Reference Links](#reference-links)

---

## Overview

### What is Deckster?

Deckster is an AI-powered presentation builder that enables users to create professional presentations with intelligent content generation. The system consists of two main services that the frontend interacts with:

1. **Elementor** (Visual Elements Orchestrator) - Handles all AI content generation
2. **Layout Service** - Manages presentations, slides, and element rendering

### Key Capabilities

| Feature | Description |
|---------|-------------|
| **AI Charts** | Generate Chart.js visualizations from natural language prompts |
| **AI Diagrams** | Create Mermaid diagrams (flowcharts, sequences, ERDs, etc.) |
| **AI Text** | Generate, transform, and auto-fit text content |
| **AI Tables** | Create and manipulate styled HTML tables |
| **AI Images** | Generate images with multiple styles and quality tiers |
| **AI Infographics** | Create visual infographics (timelines, processes, pyramids, etc.) |

### How It Works

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         USER INTERACTION FLOW                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   User clicks "Generate Chart"                                              │
│            │                                                                │
│            ▼                                                                │
│   ┌─────────────┐                                                          │
│   │  Frontend   │ ◄────────────────────────────────────────────┐           │
│   │   (React)   │                                              │           │
│   └──────┬──────┘                                              │           │
│          │                                                     │           │
│          │ POST /api/generate/chart                            │           │
│          ▼                                                     │           │
│   ┌─────────────┐      ┌─────────────┐      ┌─────────────┐   │           │
│   │  Elementor  │ ───▶ │ AI Service  │ ───▶ │  Elementor  │   │           │
│   │             │      │ (Chart AI)  │      │             │   │           │
│   └──────┬──────┘      └─────────────┘      └──────┬──────┘   │           │
│          │                                         │           │           │
│          │                              Generated  │           │           │
│          │                              Content    │           │           │
│          │                                         ▼           │           │
│          │                                  ┌─────────────┐    │           │
│          │                                  │   Layout    │    │           │
│          │ ◄─────────────────────────────── │   Service   │    │           │
│          │   Direct Injection               └─────────────┘    │           │
│          │                                                     │           │
│          │ Response: { success: true, injected: true, ... }    │           │
│          └─────────────────────────────────────────────────────┘           │
│                                                                             │
│   Content appears in presentation automatically!                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Point**: When you call Elementor to generate content, it automatically injects the result into the Layout Service presentation. The frontend just needs to refresh the view.

---

## Architecture

### Service Responsibilities

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DECKSTER ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         FRONTEND (React)                            │   │
│  │                                                                     │   │
│  │  • User interface for presentation editing                          │   │
│  │  • Calls Elementor for AI content generation                        │   │
│  │  • Embeds Layout Service via iframe for rendering                   │   │
│  │  • Handles user interactions (typing, resizing, etc.)               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                           │                    │                            │
│              AI Requests  │                    │  iframe embed              │
│                           ▼                    ▼                            │
│  ┌──────────────────────────────┐    ┌──────────────────────────────┐      │
│  │         ELEMENTOR            │    │       LAYOUT SERVICE         │      │
│  │   (AI Orchestrator)          │    │   (Presentation Engine)      │      │
│  │                              │    │                              │      │
│  │  • Receives generation       │    │  • Stores presentations      │      │
│  │    requests from frontend    │◄───│  • Manages slides & elements │      │
│  │  • Calls AI services         │    │  • Renders via reveal.js     │      │
│  │  • Injects content into      │───▶│  • Handles user edits        │      │
│  │    Layout Service            │    │  • Version history           │      │
│  │  • Returns generation status │    │                              │      │
│  └──────────────────────────────┘    └──────────────────────────────┘      │
│                 │                                                           │
│                 │ Internal calls                                            │
│                 ▼                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      AI SERVICES (Backend)                          │   │
│  │                                                                     │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────┐   │   │
│  │  │ Chart   │ │ Diagram │ │ Text &  │ │ Image   │ │ Infographic │   │   │
│  │  │   AI    │ │   AI    │ │ Table   │ │   AI    │ │     AI      │   │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────────┘   │   │
│  │                                                                     │   │
│  │  Frontend does NOT call these directly - Elementor handles it       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### What Frontend Needs to Know

| Concern | Service | Notes |
|---------|---------|-------|
| Generate AI content | Elementor | All 6 element types |
| View/embed presentations | Layout Service | iframe embedding |
| User edits (typing) | Layout Service | postMessage to iframe |
| Get presentation data | Layout Service | REST API |
| Health checks | Both | `/health` endpoint |

---

## Service URLs

### Production Environment

| Service | URL | Purpose |
|---------|-----|---------|
| **Elementor** | `https://web-production-3b42.up.railway.app` | AI content generation |
| **Layout Service** | `https://web-production-f0d13.up.railway.app` | Presentation management |

### Local Development

| Service | URL | Purpose |
|---------|-----|---------|
| **Elementor** | `http://localhost:8090` | AI content generation |
| **Layout Service** | `http://localhost:8504` | Presentation management |

### Health Check URLs

```bash
# Production
curl https://web-production-3b42.up.railway.app/health
curl https://web-production-f0d13.up.railway.app/health

# Local
curl http://localhost:8090/health
curl http://localhost:8504/health
```

---

## Quick Start

### 1. Test Connection

```javascript
// Check if services are available
const checkServices = async () => {
  const elementor = await fetch('https://web-production-3b42.up.railway.app/health');
  const layout = await fetch('https://web-production-f0d13.up.railway.app/health');

  console.log('Elementor:', await elementor.json());
  console.log('Layout:', await layout.json());
};
```

### 2. Generate Your First Chart

```javascript
const generateChart = async () => {
  const response = await fetch('https://web-production-3b42.up.railway.app/api/generate/chart', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      element_id: 'chart-1',
      context: {
        presentation_id: 'your-presentation-id',
        presentation_title: 'Q4 Report',
        slide_id: 'slide-1',
        slide_index: 0,
        slide_title: 'Revenue Overview'
      },
      position: {
        grid_row: '4/12',
        grid_column: '2/14'
      },
      prompt: 'Show quarterly revenue: Q1 $150K, Q2 $175K, Q3 $200K, Q4 $225K',
      chart_type: 'bar',
      palette: 'professional',
      generate_data: false,
      data: [
        { label: 'Q1', value: 150000 },
        { label: 'Q2', value: 175000 },
        { label: 'Q3', value: 200000 },
        { label: 'Q4', value: 225000 }
      ]
    })
  });

  const result = await response.json();

  if (result.success && result.injected) {
    // Content was automatically injected into Layout Service
    // Refresh your iframe to see the chart!
    console.log('Chart generated and injected!');
  }
};
```

---

## Elementor API Reference

### Base URL
```
Production: https://web-production-3b42.up.railway.app
Local:      http://localhost:8090
```

### Chart Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/generate/chart` | Generate a chart |
| `GET` | `/api/generate/chart/constraints` | Get size constraints |
| `GET` | `/api/generate/chart/palettes` | Get color palettes |
| `POST` | `/api/generate/chart/validate` | Validate request |

**Full URLs (Production):**
```
POST https://web-production-3b42.up.railway.app/api/generate/chart
GET  https://web-production-3b42.up.railway.app/api/generate/chart/constraints
GET  https://web-production-3b42.up.railway.app/api/generate/chart/palettes
POST https://web-production-3b42.up.railway.app/api/generate/chart/validate
```

**Chart Types:** `bar`, `line`, `pie`, `doughnut`, `area`, `scatter`, `radar`, `polarArea`, `bubble`, `treemap`

**Palettes:** `default`, `professional`, `vibrant`, `pastel`, `monochrome`, `sequential`, `diverging`, `categorical`

---

### Diagram Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/generate/diagram` | Generate a diagram |
| `GET` | `/api/generate/diagram/status/{job_id}` | Poll job status |
| `GET` | `/api/generate/diagram/types` | Get diagram types |

**Full URLs (Production):**
```
POST https://web-production-3b42.up.railway.app/api/generate/diagram
GET  https://web-production-3b42.up.railway.app/api/generate/diagram/status/{job_id}
GET  https://web-production-3b42.up.railway.app/api/generate/diagram/types
```

**Diagram Types:** `flowchart`, `sequence`, `class`, `state`, `er`, `gantt`, `userjourney`, `gitgraph`, `mindmap`, `pie`, `timeline`

**Directions:** `TB` (top-bottom), `BT`, `LR` (left-right), `RL`

---

### Text Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/generate/text` | Generate text |
| `POST` | `/api/generate/text/transform` | Transform text |
| `POST` | `/api/generate/text/autofit` | Auto-fit text |
| `GET` | `/api/generate/text/constraints/{w}/{h}` | Get constraints |

**Full URLs (Production):**
```
POST https://web-production-3b42.up.railway.app/api/generate/text
POST https://web-production-3b42.up.railway.app/api/generate/text/transform
POST https://web-production-3b42.up.railway.app/api/generate/text/autofit
GET  https://web-production-3b42.up.railway.app/api/generate/text/constraints/{width}/{height}
```

**Tones:** `professional`, `conversational`, `academic`, `persuasive`, `casual`, `technical`

**Formats:** `paragraph`, `bullets`, `numbered`, `headline`, `quote`, `mixed`

**Transformations:** `expand`, `condense`, `simplify`, `formalize`, `casualize`, `bulletize`, `paragraphize`, `rephrase`, `proofread`, `translate`

---

### Table Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/generate/table` | Generate a table |
| `POST` | `/api/generate/table/transform` | Transform table |
| `POST` | `/api/generate/table/analyze` | Analyze table |
| `GET` | `/api/generate/table/presets` | Get style presets |

**Full URLs (Production):**
```
POST https://web-production-3b42.up.railway.app/api/generate/table
POST https://web-production-3b42.up.railway.app/api/generate/table/transform
POST https://web-production-3b42.up.railway.app/api/generate/table/analyze
GET  https://web-production-3b42.up.railway.app/api/generate/table/presets
```

**Presets:** `minimal`, `bordered`, `striped`, `modern`, `professional`, `colorful`

**Transformations:** `add_column`, `add_row`, `remove_column`, `remove_row`, `sort`, `summarize`, `transpose`, `expand`, `merge_cells`, `split_column`

---

### Image Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/generate/image` | Generate an image |
| `GET` | `/api/generate/image/styles` | Get image styles |
| `GET` | `/api/generate/image/credits/{id}` | Get credits |

**Full URLs (Production):**
```
POST https://web-production-3b42.up.railway.app/api/generate/image
GET  https://web-production-3b42.up.railway.app/api/generate/image/styles
GET  https://web-production-3b42.up.railway.app/api/generate/image/credits/{presentation_id}
```

**Styles:** `realistic`, `illustration`, `abstract`, `minimal`, `photo`

**Quality Tiers:**
| Quality | Resolution | Credits |
|---------|------------|---------|
| `draft` | 512px | 1 |
| `standard` | 1024px | 2 |
| `high` | 1536px | 4 |
| `ultra` | 2048px | 8 |

**Aspect Ratios:** `1:1`, `16:9`, `9:16`, `21:9`, `4:3`

---

### Infographic Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/generate/infographic` | Generate infographic |
| `GET` | `/api/generate/infographic/types` | Get types |

**Full URLs (Production):**
```
POST https://web-production-3b42.up.railway.app/api/generate/infographic
GET  https://web-production-3b42.up.railway.app/api/generate/infographic/types
```

**Template Types (HTML):** `pyramid`, `funnel`, `concentric_circles`, `concept_spread`, `venn`, `comparison`

**Dynamic Types (SVG):** `timeline`, `process`, `statistics`, `hierarchy`, `list`, `cycle`, `matrix`, `roadmap`

**Color Schemes:** `professional`, `vibrant`, `pastel`, `monochrome`, `warm`, `cool`

**Icon Styles:** `outlined`, `filled`, `duotone`, `minimal`

---

### Utility Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Service info |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Swagger UI |

**Full URLs (Production):**
```
GET https://web-production-3b42.up.railway.app/
GET https://web-production-3b42.up.railway.app/health
GET https://web-production-3b42.up.railway.app/docs
```

---

## Layout Service API Reference

### Base URL
```
Production: https://web-production-f0d13.up.railway.app
Local:      http://localhost:8504
```

### Presentation Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/presentations/{id}` | Get presentation |
| `PUT` | `/api/presentations/{id}/slides/{index}` | Update slide |
| `POST` | `/api/presentations` | Create presentation |

**Full URLs (Production):**
```
GET  https://web-production-f0d13.up.railway.app/api/presentations/{presentation_id}
PUT  https://web-production-f0d13.up.railway.app/api/presentations/{presentation_id}/slides/{slide_index}
POST https://web-production-f0d13.up.railway.app/api/presentations
```

### Viewer Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/viewer/{id}` | View presentation |
| `GET` | `/editor/{id}` | Edit presentation |

**Embedding Example:**
```html
<iframe
  src="https://web-production-f0d13.up.railway.app/viewer/your-presentation-id"
  width="100%"
  height="600"
></iframe>
```

---

## Data Models

### ElementContext (Required for all generation requests)

```typescript
interface ElementContext {
  presentation_id: string;    // Unique presentation ID
  presentation_title: string; // Title of the presentation
  slide_id: string;           // Unique slide ID
  slide_index: number;        // Zero-based slide index
  slide_title?: string;       // Optional slide title
  industry?: string;          // Optional industry context (e.g., "technology")
  time_frame?: string;        // Optional time context (e.g., "Q4 2024")
}
```

### GridPosition (Required for all generation requests)

```typescript
interface GridPosition {
  grid_row: string;    // CSS grid-row (e.g., "4/14")
  grid_column: string; // CSS grid-column (e.g., "8/24")
}
```

**Grid System:**
- Layout Service uses a **24x14** grid
- Grid positions are CSS format: `"start/end"`
- Example: `grid_row: "4/14"` spans rows 4-13 (10 rows)
- Example: `grid_column: "2/14"` spans columns 2-13 (12 columns)

### Response Format

All generation endpoints return:

```typescript
interface GenerationResponse {
  success: boolean;           // Whether generation succeeded
  element_id: string;         // The element ID you provided

  // Content (varies by type)
  chart_config?: object;      // For charts
  svg_content?: string;       // For diagrams/infographics
  html_content?: string;      // For text/tables/infographics
  image_url?: string;         // For images

  // Injection status
  injected?: boolean;         // true if auto-injected to Layout Service
  injection_error?: string;   // Error message if injection failed

  // Error (if success: false)
  error?: {
    code: string;
    message: string;
    retryable: boolean;
    suggestion?: string;
  };
}
```

---

## Integration Patterns

### Pattern 1: Generate and Auto-Refresh

```typescript
async function generateContent(type: string, request: object) {
  const baseUrl = 'https://web-production-3b42.up.railway.app';

  const response = await fetch(`${baseUrl}/api/generate/${type}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  });

  const result = await response.json();

  if (result.success) {
    if (result.injected) {
      // Content was auto-injected - refresh iframe
      refreshPresentationIframe();
      showSuccess('Content generated!');
    } else {
      // Injection failed - handle manually
      showWarning('Generated but injection failed: ' + result.injection_error);
      manuallyInjectContent(result);
    }
  } else {
    handleError(result.error);
  }

  return result;
}
```

### Pattern 2: Loading States

```typescript
async function generateWithLoading(type: string, request: object) {
  setLoading(true);
  setLoadingMessage('Generating content...');

  try {
    const result = await generateContent(type, request);

    if (result.success) {
      setLoadingMessage('Injecting into presentation...');
      await new Promise(resolve => setTimeout(resolve, 500)); // Brief delay for UX
      refreshPresentationIframe();
    }

    return result;
  } finally {
    setLoading(false);
  }
}
```

### Pattern 3: Retry Logic

```typescript
async function generateWithRetry(type: string, request: object, maxRetries = 3) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    const result = await generateContent(type, request);

    if (result.success) {
      return result;
    }

    if (!result.error?.retryable || attempt === maxRetries) {
      throw new Error(result.error?.message || 'Generation failed');
    }

    // Exponential backoff
    await new Promise(resolve =>
      setTimeout(resolve, 1000 * Math.pow(2, attempt - 1))
    );
  }
}
```

### Pattern 4: Batch Operations

```typescript
async function generateMultipleElements(requests: GenerationRequest[]) {
  const results = await Promise.all(
    requests.map(req => generateContent(req.type, req.data))
  );

  const successful = results.filter(r => r.success);
  const failed = results.filter(r => !r.success);

  if (successful.length > 0) {
    refreshPresentationIframe();
  }

  return { successful, failed };
}
```

---

## Error Handling

### Error Codes

| Code | Description | Retryable | Action |
|------|-------------|-----------|--------|
| `GRID_TOO_SMALL` | Element too small | Yes | Resize element |
| `MISSING_DATA` | Required data missing | Yes | Provide data |
| `AI_SERVICE_ERROR` | AI service unavailable | Yes | Retry |
| `INVALID_REQUEST` | Malformed request | No | Fix request |
| `RATE_LIMITED` | Too many requests | Yes | Wait and retry |
| `CREDITS_EXHAUSTED` | No credits remaining | No | Purchase credits |

### Error Response Example

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

### Handling Errors

```typescript
function handleGenerationError(error: GenerationError) {
  switch (error.code) {
    case 'GRID_TOO_SMALL':
      showResizeDialog(error.suggestion);
      break;

    case 'MISSING_DATA':
      showDataEntryDialog();
      break;

    case 'AI_SERVICE_ERROR':
    case 'RATE_LIMITED':
      scheduleRetry();
      break;

    case 'CREDITS_EXHAUSTED':
      showUpgradeDialog();
      break;

    default:
      showErrorMessage(error.message);
  }
}
```

---

## Examples

### Example 1: Complete Chart Generation

```typescript
const chartRequest = {
  element_id: 'revenue-chart-2024',
  context: {
    presentation_id: 'pres-abc123',
    presentation_title: 'Annual Report 2024',
    slide_id: 'slide-revenue',
    slide_index: 2,
    slide_title: 'Revenue Overview',
    industry: 'technology',
    time_frame: '2024'
  },
  position: {
    grid_row: '3/13',
    grid_column: '2/14'
  },
  prompt: 'Show monthly revenue growth for 2024 with trend line',
  chart_type: 'line',
  palette: 'professional',
  show_legend: true,
  show_data_labels: false,
  generate_data: true  // Let AI generate sample data
};

const result = await fetch(
  'https://web-production-3b42.up.railway.app/api/generate/chart',
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(chartRequest)
  }
).then(r => r.json());

console.log(result);
// {
//   success: true,
//   element_id: 'revenue-chart-2024',
//   chart_config: { type: 'line', data: {...}, options: {...} },
//   metadata: { chart_type: 'line', data_point_count: 12 },
//   insights: { trend: 'increasing' },
//   injected: true
// }
```

### Example 2: Generate Flowchart Diagram

```typescript
const diagramRequest = {
  element_id: 'auth-flow-diagram',
  context: {
    presentation_id: 'pres-abc123',
    presentation_title: 'System Architecture',
    slide_id: 'slide-auth',
    slide_index: 5
  },
  position: {
    grid_row: '2/14',
    grid_column: '4/20'
  },
  prompt: 'User authentication flow: login form, validate credentials, check 2FA, create session, redirect to dashboard. Include error paths.',
  diagram_type: 'flowchart',
  direction: 'TB',
  theme: 'default',
  complexity: 'moderate'
};

const result = await fetch(
  'https://web-production-3b42.up.railway.app/api/generate/diagram',
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(diagramRequest)
  }
).then(r => r.json());
```

### Example 3: Transform Existing Text

```typescript
const transformRequest = {
  element_id: 'intro-text',
  context: {
    presentation_id: 'pres-abc123',
    presentation_title: 'Product Launch',
    slide_id: 'slide-intro',
    slide_index: 0
  },
  position: {
    grid_row: '4/10',
    grid_column: '2/12'
  },
  source_content: '<p>Our new product is really good and has many features that customers will like. It does a lot of things.</p>',
  transformation: 'formalize',
  intensity: 0.8
};

const result = await fetch(
  'https://web-production-3b42.up.railway.app/api/generate/text/transform',
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(transformRequest)
  }
).then(r => r.json());

// Result: Professional, polished version of the text
```

### Example 4: Generate Process Infographic

```typescript
const infographicRequest = {
  element_id: 'onboarding-process',
  context: {
    presentation_id: 'pres-abc123',
    presentation_title: 'Employee Handbook',
    slide_id: 'slide-onboarding',
    slide_index: 3
  },
  position: {
    grid_row: '2/14',
    grid_column: '1/25'
  },
  prompt: 'Employee onboarding process: Application Review, Interview, Offer Letter, Background Check, First Day Orientation',
  infographic_type: 'process',
  color_scheme: 'professional',
  icon_style: 'outlined',
  item_count: 5,
  generate_data: true
};

const result = await fetch(
  'https://web-production-3b42.up.railway.app/api/generate/infographic',
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(infographicRequest)
  }
).then(r => r.json());
```

---

## Reference Links

### Documentation

| Resource | URL |
|----------|-----|
| **Elementor API Docs** | [FRONTEND_API.md](https://github.com/Pramod-Potti-Krishnan/elementor/blob/main/FRONTEND_API.md) |
| **Elementor Swagger UI** | https://web-production-3b42.up.railway.app/docs |
| **Elementor GitHub** | https://github.com/Pramod-Potti-Krishnan/elementor |
| **Layout Service GitHub** | https://github.com/Pramod-Potti-Krishnan/deck-builder-7.5 (branch: `element-v1`) |

### Production Services

| Service | Health Check | Swagger |
|---------|--------------|---------|
| **Elementor** | https://web-production-3b42.up.railway.app/health | https://web-production-3b42.up.railway.app/docs |
| **Layout Service** | https://web-production-f0d13.up.railway.app/health | - |

### Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DECKSTER API QUICK REFERENCE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ELEMENTOR BASE: https://web-production-3b42.up.railway.app                │
│                                                                             │
│  Charts:      POST /api/generate/chart                                      │
│  Diagrams:    POST /api/generate/diagram                                    │
│  Text:        POST /api/generate/text                                       │
│  Tables:      POST /api/generate/table                                      │
│  Images:      POST /api/generate/image                                      │
│  Infographics: POST /api/generate/infographic                               │
│                                                                             │
│  LAYOUT SERVICE BASE: https://web-production-f0d13.up.railway.app          │
│                                                                             │
│  Get Presentation: GET /api/presentations/{id}                              │
│  View:            GET /viewer/{id}                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Support

For issues or questions:
1. Check the Swagger UI at `/docs` for interactive API testing
2. Review error responses - they include suggestions
3. Check service health endpoints before reporting issues

---

*Document generated for Deckster Frontend Team - December 2024*
