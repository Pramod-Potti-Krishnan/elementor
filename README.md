# Visual Elements Orchestrator v1.0

Coordinates AI content generation for presentation visual elements (Charts, Images, Infographics, Diagrams).

## Architecture

```
┌─────────────┐     ┌─────────────────────┐     ┌──────────────────────┐
│  Frontend   │────▶│    Orchestrator     │────▶│   AI Services        │
│  (React)    │     │     Service         │     │                      │
│             │     │  Port 8090          │     │  • Chart AI (8080)   │
└─────────────┘     │                     │     │  • Image AI (8081)   │
       │            │  Coordinates:       │     │  • Infographic AI    │
       │            │  • Validates        │     │  • Diagram AI        │
       │            │  • Routes           │     └──────────────────────┘
       │            │  • Transforms       │
       │            │  • Handles errors   │
       │            └─────────────────────┘
       │                      │
       │                      │ postMessage
       ▼                      ▼
┌─────────────────────────────────────────┐
│           Layout Service v7.5            │
│  (iframe - presentation-viewer.html)     │
└──────────────────────────────────────────┘
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env

# Edit .env with your service URLs

# Run the server
python main.py
```

## Endpoints

### Chart Generation

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/generate/chart` | POST | Generate Chart.js configuration |
| `/api/generate/chart/constraints` | GET | Get grid size constraints |
| `/api/generate/chart/palettes` | GET | Get available color palettes |
| `/api/generate/chart/validate` | POST | Validate request before generation |

### Health

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/` | GET | Service info |

## Usage Example

### Generate a Chart

```bash
curl -X POST http://localhost:8090/api/generate/chart \
  -H "Content-Type: application/json" \
  -d '{
    "element_id": "chart-123",
    "context": {
      "presentation_id": "pres-456",
      "presentation_title": "Q4 Report",
      "slide_id": "slide-7",
      "slide_index": 6,
      "slide_title": "Revenue Analysis"
    },
    "position": {
      "grid_row": "4/12",
      "grid_column": "6/20"
    },
    "prompt": "Show quarterly revenue growth for 2024",
    "chart_type": "bar",
    "palette": "professional",
    "data": [
      {"label": "Q1", "value": 125000},
      {"label": "Q2", "value": 145000},
      {"label": "Q3", "value": 162000},
      {"label": "Q4", "value": 178000}
    ]
  }'
```

### Response

```json
{
  "success": true,
  "element_id": "chart-123",
  "chart_config": {
    "type": "bar",
    "data": {
      "labels": ["Q1", "Q2", "Q3", "Q4"],
      "datasets": [{
        "label": "Revenue",
        "data": [125000, 145000, 162000, 178000],
        "backgroundColor": ["#1E3A5F", "#2D5A87", "#3D7AAF", "#4D9AD7"]
      }]
    },
    "options": {
      "responsive": true,
      "maintainAspectRatio": true
    }
  },
  "metadata": {
    "chart_type": "bar",
    "data_point_count": 4,
    "dataset_count": 1,
    "suggested_title": "Quarterly Revenue Growth"
  },
  "insights": {
    "trend": "increasing",
    "highlights": ["Consistent growth across all quarters"]
  }
}
```

## Frontend Integration

After receiving the response, send the `chart_config` to the Layout Service iframe:

```typescript
// Frontend component
async function handleGenerateChart() {
  const result = await fetch('http://localhost:8090/api/generate/chart', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  }).then(r => r.json());

  if (result.success) {
    // Send to Layout Service iframe
    iframeRef.current.contentWindow.postMessage({
      command: 'updateChartConfig',
      elementId: result.element_id,
      chartConfig: result.chart_config,
      metadata: result.metadata,
      insights: result.insights
    }, '*');
  }
}
```

## Grid Conversion

The orchestrator converts between two grid systems:

| System | Columns | Rows | Used By |
|--------|---------|------|---------|
| Layout Service | 24 | 14 | CSS Grid positioning |
| Chart AI | 12 | 8 | Size constraints |

### Conversion Formula

```
Chart AI Width = Layout Columns / 2
Chart AI Height = Layout Rows × (8/14)
```

### Example

Layout position: `gridRow="4/12", gridColumn="6/20"`
- Row span: 12-4 = 8 rows
- Col span: 20-6 = 14 cols
- Chart AI Width: 14/2 = 7
- Chart AI Height: 8×(8/14) ≈ 5

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CHART_SERVICE_URL` | `http://localhost:8080` | Chart AI Service URL |
| `SERVICE_TIMEOUT` | `30.0` | HTTP timeout in seconds |
| `HOST` | `0.0.0.0` | Server bind host |
| `PORT` | `8090` | Server port |
| `CORS_ORIGINS` | `["*"]` | Allowed CORS origins |

## Error Handling

The orchestrator returns structured errors:

```json
{
  "success": false,
  "element_id": "chart-123",
  "error": {
    "code": "GRID_TOO_SMALL",
    "message": "Grid size 2x2 is too small for bar chart",
    "retryable": true,
    "suggestion": "Resize to at least 3x3 grid units"
  }
}
```

### Error Codes

| Code | Description | Retryable |
|------|-------------|-----------|
| `GRID_TOO_SMALL` | Element size below minimum | Yes |
| `MISSING_DATA` | No data and generate_data=false | Yes |
| `TIMEOUT` | Service call timed out | Yes |
| `CONNECTION_ERROR` | Cannot reach AI service | Yes |
| `INTERNAL_ERROR` | Unexpected error | No |

## Development

```bash
# Run with auto-reload
python main.py

# Or use uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8090
```

## Future Services

The orchestrator is designed to support additional visual element types:

- **Image Generation** - `/api/generate/image`
- **Infographic Generation** - `/api/generate/infographic`
- **Diagram Generation** - `/api/generate/diagram`

These will be added as the respective AI services become available.
