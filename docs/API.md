# REST API

## Conventions

- Base path: `/api/v1`
- JSON fields: `camelCase`
- Time: ISO 8601 with timezone
- Page numbering: zero-based
- Default page size: `20`
- Maximum page size: `100`
- Video is served as MJPEG, not JSON.

Inspection result values are `NORMAL` or `DEFECT`. A processor that has not evaluated an individual rule may use `NOT_EVALUATED` for that individual result; `overallResult` remains `NORMAL` or `DEFECT` for persisted events.

## Stream video

### `GET /api/v1/stream`

Returns the latest processed OpenCV frame as an MJPEG stream.

```http
HTTP/1.1 200 OK
Content-Type: multipart/x-mixed-replace; boundary=frame
Cache-Control: no-store
```

Each part is a JPEG image:

```http
--frame
Content-Type: image/jpeg
Content-Length: 12345

<JPEG bytes>
```

The endpoint reads a shared processed-frame/JPEG buffer. It does not open the camera or run the vision processor. Disconnecting the client ends only that response generator.

Minimal browser test:

```html
<img src="http://localhost:5000/api/v1/stream" alt="Inspection stream">
```

### `GET /stream-test`

Returns a minimal HTML page containing an `<img>` linked to `/api/v1/stream`. It exists only to verify the MJPEG path before a React screen is connected.

## Latest inspection

### `GET /api/v1/inspection/latest`

Returns the most recently persisted inspection event.

```json
{
  "id": 125,
  "inspectionTime": "2026-09-22T20:10:32+09:00",
  "overallResult": "DEFECT",
  "missingComponentResult": "NORMAL",
  "alignmentResult": "NORMAL",
  "fasteningResult": "DEFECT",
  "metrics": {
    "washerGapPx": 12.4,
    "threadExposurePx": 35.2
  },
  "defectImageUrl": "/api/v1/inspections/125/image",
  "createdAt": "2026-09-22T20:10:32.120+09:00"
}
```

Responses:

- `200 OK`: latest event returned.
- `204 No Content`: no inspection event exists yet.
- `503 Service Unavailable`: database is unavailable.

## Inspection history

### `GET /api/v1/inspections?page=0&size=20`

Returns newest events first.

```json
{
  "content": [
    {
      "id": 125,
      "inspectionTime": "2026-09-22T20:10:32+09:00",
      "overallResult": "DEFECT",
      "missingComponentResult": "NORMAL",
      "alignmentResult": "NORMAL",
      "fasteningResult": "DEFECT",
      "metrics": {
        "washerGapPx": 12.4
      },
      "defectImageUrl": "/api/v1/inspections/125/image",
      "createdAt": "2026-09-22T20:10:32.120+09:00"
    }
  ],
  "page": 0,
  "size": 20,
  "totalElements": 1,
  "totalPages": 1
}
```

Validation:

- `page` must be zero or greater.
- `size` must be between 1 and 100.
- Invalid query values return `400 Bad Request`.

## Inspection detail

### `GET /api/v1/inspections/{id}`

Returns one inspection in the same representation used by the latest endpoint.

Responses:

- `200 OK`: event returned.
- `404 Not Found`: no event has that ID.
- `503 Service Unavailable`: database is unavailable.

A non-integer ID does not match the Flask route and therefore returns `404 Not Found`.

## Defect image

### `GET /api/v1/inspections/{id}/image`

Returns the stored evidence image associated with an inspection event.

```http
HTTP/1.1 200 OK
Content-Type: image/jpeg
Content-Length: 45678
```

The server derives the content type from the stored file and returns an appropriate image media type such as `image/jpeg` or `image/png`. Paths are resolved inside the configured defect-image directory; arbitrary filesystem paths are never accepted from the URL.

Responses:

- `200 OK`: image bytes returned.
- `404 Not Found`: inspection or stored image does not exist.

## System status

### `GET /api/v1/system/status`

Provides lightweight operational state for the MVP.

```json
{
  "cameraConnected": true,
  "visionWorkerRunning": true,
  "databaseConnected": true,
  "eventState": "NORMAL",
  "lastCapturedAt": "2026-09-22T20:10:32.300+09:00",
  "lastProcessedAt": "2026-09-22T20:10:32.350+09:00",
  "cameraError": null,
  "visionError": null,
  "databaseError": null
}
```

The endpoint reports status; it does not start or restart resources.

## Error representation

HTTP errors use `error` and `message` fields:

```json
{
  "error": "Not Found",
  "message": "The requested URL was not found on the server."
}
```

Database failures return status `503` with `error: "database_unavailable"`. Pagination validation currently returns a single `error` string.

Do not expose stack traces, database credentials, or absolute storage paths.

## React usage

Use separate clients for the two paths:

```text
Video:  <img src="/api/v1/stream">
Data:   GET /api/v1/inspection/latest at a modest polling interval
History/detail: REST GET on navigation or explicit refresh
```

Polling the latest result once per second is sufficient for the MVP. If immediate event notification becomes necessary, add SSE or WebSocket for confirmed inspection events while retaining REST for history and detail.
