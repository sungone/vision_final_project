# Database Schema

## Storage model

PostgreSQL stores inspection events, not camera frames. Vision 결과는 기본 1 FPS로 평가되며 동일한 `DefectSignature`는 한 행만 만든다. NORMAL 없이도 categorical 또는 geometry가 tolerance 밖으로 바뀌면 새 행을 만든다.

DefectSignature 자체는 비교용 메모리 객체이므로 별도 column으로 저장하지 않는다. 기존 categorical column과 metrics JSONB가 판정 결과 및 재현용 metadata를 계속 저장한다.

The schema is intentionally small. It contains the stable fields needed for list/detail APIs and a JSONB object for model-dependent measurements.

## `inspections`

| Column | PostgreSQL type | Null | Description |
| --- | --- | --- | --- |
| `id` | `BIGSERIAL` | No | Inspection event identifier. |
| `inspection_time` | `TIMESTAMPTZ` | No | Time the event was confirmed. |
| `overall_result` | `VARCHAR(20)` | No | `NORMAL` or `DEFECT`. |
| `missing_component_result` | `VARCHAR(20)` | No | Missing-component result. |
| `alignment_result` | `VARCHAR(20)` | No | Final assembly/alignment result. |
| `fastening_result` | `VARCHAR(20)` | No | Fastening result. |
| `metrics` | `JSONB` | No | Model name, inference summary and compact detection metadata; defaults to `{}`. |
| `defect_image_path` | `TEXT` | Yes | Server-controlled evidence-image filesystem path. |
| `event_key` | `VARCHAR(120)` | Yes | Optional event identity; unique when present. A future tracker or PLC cycle ID can supply this value. |
| `created_at` | `TIMESTAMPTZ` | No | Row creation time. |

Recommended constraints and indexes:

```sql
CHECK (overall_result IN ('NORMAL', 'DEFECT'))
CHECK (missing_component_result IN ('NORMAL', 'DEFECT', 'NOT_EVALUATED'))
CHECK (alignment_result IN ('NORMAL', 'DEFECT', 'NOT_EVALUATED'))
CHECK (fastening_result IN ('NORMAL', 'DEFECT', 'NOT_EVALUATED'))
CREATE INDEX ix_inspections_time ON inspections (inspection_time DESC);
CREATE UNIQUE INDEX ux_inspections_event_key
    ON inspections (event_key)
    WHERE event_key IS NOT NULL;
```

The partial unique index supports a later PLC/tracker identity without forcing the MVP state machine to invent a product ID.

## Why JSONB for metrics

Measurements and detection metadata will change as segmentation and rule algorithms mature. The MVP therefore stores compact query/display metadata while deliberately excluding full masks and contour coordinate arrays.

```json
{
  "modelType": "u-net-resnet18",
  "detectedInstanceCount": 5,
  "inferenceTimeMs": 82.4,
  "detections": [
    {
      "classId": 2,
      "className": "washer",
      "confidence": 0.96,
      "bbox": [10, 20, 30, 40],
      "center": [20.0, 30.0],
      "areaPx": 320
    }
  ]
}
```

JSONB is suitable now because:

- the metric set is sparse and model/rule-version dependent;
- the MVP does not filter, join, or aggregate heavily by individual metrics;
- adding a new measurement does not require a migration.

Stable search fields remain normal columns. If a metric becomes a frequent filter or KPI aggregation dimension, promote it to a typed column or add a purposeful expression index. Do not add a broad JSONB GIN index until a real query requires it.

## Evidence-image storage

The MVP stores evidence images in the filesystem and stores the resolved server path in PostgreSQL. The API never returns that path directly.

| Choice | Benefit | Cost |
| --- | --- | --- |
| PostgreSQL `BYTEA` | Single transaction and backup boundary | Database growth, larger backups, memory/I/O pressure when serving images |
| Filesystem/object storage + DB path | Small DB rows, direct image delivery, easy later object-storage migration | Must coordinate file and row lifecycle |

Filesystem storage matches a local MVP and keeps PostgreSQL focused on queryable event data. The application must:

- generate server-controlled filenames;
- resolve every generated path inside the configured image root;
- reject path traversal;
- write the image before committing its row or remove orphaned files after a failed transaction;
- return the detected MIME type from the image endpoint.

For deployment across multiple backend instances, replace local storage with object storage and migrate `defect_image_path` to a portable storage key.

## Duplicate-event prevention

The primary guard is the in-memory Event Manager described in [ARCHITECTURE.md](ARCHITECTURE.md). It samples independently from Vision FPS and persists only a signature that differs meaningfully from the last stored defect.

Database uniqueness becomes the second guard once a reliable tracker/PLC identity exists and is assigned to `event_key`:

```text
Rule result → 1 FPS sample → signature compare → changed defect only → INSERT
                                                              ↓
                                                   UNIQUE(event_key) safety net
```

Inference time, confidence jitter, timestamp, and event key are not signature features. Duplicate sampled frames never reach image saving or event-key generation.

## Transaction boundary

One confirmed event is one transaction:

1. Save the evidence frame using a generated relative key.
2. Insert the inspection row with result fields, metrics, and that key.
3. Commit.
4. On insert failure, delete the newly written image when safe.

Read APIs use newest-first pagination ordered by `(inspection_time DESC, id DESC)` so that equal timestamps produce deterministic pages.

## Configuration

The backend reads a PostgreSQL URL from `DATABASE_URL`, for example:

```text
postgresql+psycopg://vision:vision@localhost:5432/vision_inspection
```

Credentials belong in environment variables or secret management, not source control. The local PostgreSQL service defaults are development-only.

