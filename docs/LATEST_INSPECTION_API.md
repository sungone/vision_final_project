# Latest Inspection API

## 1. 목적

React Dashboard가 VisionWorker가 생성한 가장 최근 InspectionResult를 조회하기 위한 프론트엔드 연동 명세다.

- 데이터 원본: 메모리의 Runtime.latest_results
- 용도: 현재 검사 상태와 KPI 표시
- 비포함 항목: 영상 바이트, segmentation mask, contour, DB 식별자, 저장 이미지 URL
- PostgreSQL, EventManager, InspectionRepository를 호출하지 않는다.

영상은 GET /api/v1/stream, 과거 검사 이력은 GET /api/v1/inspections를 사용한다.

## 2. 실제 백엔드 데이터 흐름

```text
CameraCaptureWorker
        ↓
LatestFrameBuffer
        ↓
VisionWorker
        ↓
VisionProcessor.process(frame)
        ↓
InspectionResult
        ├─ processed_frame → JPEG → encoded_frames → MJPEG API
        ├─ latest_results → Latest Inspection API → React Dashboard
        └─ EventManager → PersistenceWorker → PostgreSQL
```

관련 구현 위치:

| 역할 | 파일 / 심볼 |
|---|---|
| 최신값 1개 보관 | backend/app/camera/frame_buffer.py - LatestValueBuffer |
| 최신 검사 결과 기록 | backend/app/vision/worker.py - VisionWorker.run |
| Runtime 생성 및 주입 | backend/app/lifecycle.py - Runtime.latest_results |
| 응답 직렬화 | backend/app/vision/contracts.py - InspectionResult.to_live_dict |
| 지표 생성 | backend/app/vision/decision_engine.py - InspectionDecisionEngine.evaluate |
| HTTP Route | backend/app/api/inspections.py - latest_inspection |

LatestValueBuffer는 queue가 아니다. 가장 최근 값 하나만 유지하므로 느린 React polling이 오래된 결과를 쌓아 두었다가 순차 처리하지 않는다.

## 3. HTTP 규격

### GET /api/v1/inspection/latest

메모리에 있는 최신 실시간 검사 결과를 반환한다.

Request body와 query parameter는 없다.

```http
GET /api/v1/inspection/latest HTTP/1.1
Accept: application/json
```

### 성공 응답

```http
HTTP/1.1 200 OK
Content-Type: application/json
```

```json
{
  "inspectionTime": "2026-09-26T05:30:21.123000+00:00",
  "overallResult": "DEFECT",
  "assemblySequenceResult": "NORMAL",
  "fasteningQualityResult": "DEFECT",
  "missingComponentResult": "NORMAL",
  "alignmentResult": "NOT_EVALUATED",
  "fasteningResult": "DEFECT",
  "metrics": {
    "modelType": "u-net-resnet18",
    "detectedInstanceCount": 5,
    "inferenceTimeMs": 63.42,
    "detectedCounts": {
      "bolt": 2,
      "thread": 1,
      "washer": 2
    },
    "detections": [
      {
        "classId": 0,
        "className": "bolt",
        "confidence": 0.9921,
        "bbox": [120, 42, 302, 188],
        "center": [211.0, 115.0],
        "areaPx": 15420
      }
    ],
    "assemblyReasons": [],
    "fasteningEvaluated": true,
    "measuredThreadCm": 1.52,
    "threadThresholdCm": 2.16,
    "scaleCmPerPx": 0.01923
  }
}
```

위 JSON은 실제 serializer와 DecisionEngine 필드명을 사용한 예시다. 수치와 detection 개수는 프레임마다 달라진다.

## 4. 최상위 필드

| 필드 | Type | Nullable | 설명 | React 사용 예 |
|---|---|---:|---|---|
| inspectionTime | string | No | Vision 결과의 검사 시각. Python datetime.isoformat 형식 | 최근 검사 시각, 데이터 freshness 판단 |
| overallResult | ResultStatus | No | 조립과 체결 판정을 합친 전체 결과 | 메인 NORMAL/DEFECT 배지 |
| assemblySequenceResult | ResultStatus | No | missingComponentResult의 프론트엔드 친화 별칭 | 조립 순서/구성 카드 |
| fasteningQualityResult | ResultStatus | No | fasteningResult의 프론트엔드 친화 별칭 | 체결 상태 카드 |
| missingComponentResult | ResultStatus | No | 구성품 및 조립 판정 원본 필드 | 상세/진단 화면 |
| alignmentResult | ResultStatus | No | 정렬 판정. 현재 엔진에서는 NOT_EVALUATED | 정렬 상태 카드 또는 미평가 표시 |
| fasteningResult | ResultStatus | No | 체결 판정 원본 필드 | 상세/진단 화면 |
| metrics | object | No | 검출 수, 추론 시간, 판정 사유, 선택적 측정값 | KPI 및 상세 패널 |

assemblySequenceResult와 missingComponentResult는 현재 같은 값을 가진다. fasteningQualityResult와 fasteningResult도 현재 같은 값을 가진다. 일반 Dashboard는 별칭 필드를 사용하고, 진단 화면은 원본 필드를 사용할 수 있다.

## 5. metrics 필드

| 필드 | Type | Nullable / 생략 | 설명 | React 사용 예 |
|---|---|---:|---|---|
| modelType | string | No | 실제 추론 processor/model 식별값 | 모델 정보 |
| detectedInstanceCount | integer | No | 현재 프레임의 전체 검출 객체 수 | Total KPI |
| inferenceTimeMs | number | No | 해당 프레임 추론 시간(ms), 소수 둘째 자리 반올림 | 성능 KPI |
| detectedCounts | object<string, integer> | No | className별 객체 수. 검출되지 않은 클래스 key는 없을 수 있음 | Bolt/Washer/Thread count |
| detections | Detection[] | No | 객체별 검색 가능한 metadata | 상세 진단/객체 목록 |
| assemblyReasons | string[] | No | 조립 불량 사유 코드. 정상이면 빈 배열 | 불량 원인 목록 |
| fasteningEvaluated | boolean | No | 체결 측정을 실제 수행했는지 여부 | 측정값 표시 여부 |
| measuredThreadCm | number | 조건부 생략 | 측정한 나사산 노출 길이(cm) | 현재 측정값 |
| threadThresholdCm | number | 조건부 생략 | 체결 정상 판정 임계값(cm) | 기준값 |
| scaleCmPerPx | number | 조건부 생략 | 픽셀을 cm로 바꾸는 현재 scale | 진단/보정 정보 |

체결 측정 3개 필드는 fasteningEvaluated가 false이면 null이 아니라 metrics 객체에서 생략된다. React에서는 해당 key의 존재 여부 또는 fasteningEvaluated를 먼저 확인해야 한다.

detectedCounts도 모든 class key를 보장하지 않는다. 안전한 표시는 다음처럼 기본값 0을 사용한다.

```ts
const boltCount = data.metrics.detectedCounts.bolt ?? 0
const washerCount = data.metrics.detectedCounts.washer ?? 0
const threadCount = data.metrics.detectedCounts.thread ?? 0
```

## 6. Detection 필드

| 필드 | Type | Nullable | 설명 |
|---|---|---:|---|
| classId | integer | No | 모델의 class index |
| className | string | No | bolt, washer, thread 등의 class 이름 |
| confidence | number | No | confidence, 소수 넷째 자리 반올림 |
| bbox | [number, number, number, number] | No | [x1, y1, x2, y2] 픽셀 좌표 |
| center | [number, number] | No | [x, y] 중심 픽셀 좌표 |
| areaPx | integer | No | segmentation mask 면적(pixel) |

전체 numpy mask와 contour 좌표는 응답하지 않는다. 브라우저에 표시할 시각화는 별도의 MJPEG processed frame에 이미 반영된다.

## 7. 상태값 규약

ResultStatus는 다음 세 문자열 중 하나다.

| 값 | 의미 |
|---|---|
| NORMAL | 해당 판정 정상 |
| DEFECT | 해당 판정 불량 |
| NOT_EVALUATED | 해당 판정을 수행하지 않음 |

현재 DecisionEngine 규칙:

- overallResult: NORMAL 또는 DEFECT
- assemblySequenceResult / missingComponentResult: NORMAL 또는 DEFECT
- fasteningQualityResult / fasteningResult: 조립 불량 때문에 체결 검사를 건너뛰면 NOT_EVALUATED 가능
- alignmentResult: 현재 별도 정렬 규칙이 없어 NOT_EVALUATED

assemblyReasons의 현재 코드 예:

| 패턴 | 의미 |
|---|---|
| no_thread | 나사산 미검출 |
| dup_thread(N) | 나사산이 N개 검출됨 |
| no_bolt | 볼트/너트 미검출 |
| no_nut | 너트 역할 객체 미검출 |
| extra_bolt(N) | 볼트/너트 객체가 N개로 기대값보다 많음 |
| washer_low(N) | 와셔가 N개로 기대값보다 적음 |
| washer_high(N) | 와셔가 N개로 기대값보다 많음 |

이 코드는 사용자 표시 문구가 아니라 기계 판독용이다. React에서 한글 문구가 필요하면 code-to-label mapping을 둔다.

## 8. 아직 데이터가 없는 경우

서버 시작 직후 첫 Vision frame이 처리되기 전에는 다음을 반환한다.

```http
HTTP/1.1 204 No Content
```

응답 body는 없다. 이는 오류가 아니라 정상적인 초기 상태다. 204에서 response.json()을 호출하면 실패할 수 있으므로 status를 먼저 확인한다. 화면에는 카메라 준비 중 또는 첫 검사 대기 중 상태를 표시하고 polling을 계속한다.

PostgreSQL에 과거 이력이 있어도 latest_results가 비어 있으면 204다. 반대로 DB가 비어 있거나 중단되어도 메모리에 최신 결과가 있으면 이 API는 200을 반환할 수 있다.

## 9. 오류 응답

이 API에는 사용자 입력이 없어 일반적인 400 validation 오류는 없다. 예상하지 못한 직렬화/서버 오류는 공통 오류 handler를 따른다.

```http
HTTP/1.1 500 Internal Server Error
Content-Type: application/json
```

```json
{
  "error": "internal_server_error",
  "message": "Unexpected server error."
}
```

DB를 조회하지 않으므로 이 endpoint에서 DB 연결 실패만으로 503 database_unavailable이 발생하지 않는다.

## 10. TypeScript 타입 제안

```ts
export type ResultStatus = 'NORMAL' | 'DEFECT' | 'NOT_EVALUATED'

export interface Detection {
  classId: number
  className: string
  confidence: number
  bbox: [number, number, number, number]
  center: [number, number]
  areaPx: number
}

export interface InspectionMetrics {
  modelType: string
  detectedInstanceCount: number
  inferenceTimeMs: number
  detectedCounts: Record<string, number>
  detections: Detection[]
  assemblyReasons: string[]
  fasteningEvaluated: boolean
  measuredThreadCm?: number
  threadThresholdCm?: number
  scaleCmPerPx?: number
}

export interface LatestInspectionResponse {
  inspectionTime: string
  overallResult: ResultStatus
  assemblySequenceResult: ResultStatus
  fasteningQualityResult: ResultStatus
  missingComponentResult: ResultStatus
  alignmentResult: ResultStatus
  fasteningResult: ResultStatus
  metrics: InspectionMetrics
}
```

## 11. React 호출 예제

프로젝트는 VITE_API_BASE_URL을 사용하고, 값이 없으면 Vite proxy를 통한 상대 URL을 사용한다.

```ts
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export async function getLatestInspection(
  signal?: AbortSignal,
): Promise<LatestInspectionResponse | null> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/inspection/latest`,
    { method: 'GET', signal },
  )

  if (response.status === 204) {
    return null
  }

  if (!response.ok) {
    throw new Error(`Latest inspection request failed: HTTP ${response.status}`)
  }

  return response.json() as Promise<LatestInspectionResponse>
}
```

React 흐름:

```text
Dashboard
    ↓ GET /api/v1/inspection/latest
Flask route
    ↓ runtime.latest_results.get(timeout=0)
LatestValueBuffer
    ↓ InspectionResult.to_live_dict()
JSON response
    ↓
React state
    ↓
Status / KPI / Measurement components
```

## 12. 권장 polling 전략

기본 권장값은 1000ms다.

- 기본 VISION_FPS는 10이지만 Dashboard 상태/KPI가 100ms마다 바뀔 필요는 없다.
- latest_results는 최신값 하나만 유지하므로 1초 polling에서도 backlog가 생기지 않는다.
- 동일한 JSON을 초당 10~30번 반복 요청하는 비용을 피한다.
- 더 빠른 조작 피드백이 필요한 시험 화면에서만 500ms를 검토한다.

권장 구현 원칙:

- component mount 시 즉시 1회 호출 후 1000ms 간격으로 갱신
- 이전 요청이 끝나기 전에 다음 요청을 겹쳐 보내지 않음
- unmount 시 interval 정리 및 AbortController로 진행 중 요청 취소
- 204는 error banner가 아니라 대기 상태로 처리
- 일시적 오류에서는 마지막 정상 데이터를 유지하면서 연결 상태를 별도로 표시

```tsx
useEffect(() => {
  let disposed = false
  let requestInFlight = false
  const controller = new AbortController()

  const refresh = async () => {
    if (requestInFlight) return
    requestInFlight = true
    try {
      const next = await getLatestInspection(controller.signal)
      if (!disposed) setLatestInspection(next)
    } catch (error) {
      if (!disposed && !controller.signal.aborted) setInspectionError(error)
    } finally {
      requestInFlight = false
    }
  }

  void refresh()
  const timer = window.setInterval(() => void refresh(), 1000)

  return () => {
    disposed = true
    window.clearInterval(timer)
    controller.abort()
  }
}, [])
```

## 13. React UI 매핑

| Dashboard 영역 | 사용 필드 | 표시 방법 |
|---|---|---|
| Overall Status | overallResult | NORMAL 녹색, DEFECT 적색 |
| Assembly Status | assemblySequenceResult | NORMAL / DEFECT badge |
| Fastening Status | fasteningQualityResult | NORMAL / DEFECT / NOT_EVALUATED badge |
| Alignment Status | alignmentResult | 현재 NOT_EVALUATED 안내 |
| Bolt Count | metrics.detectedCounts.bolt ?? 0 | integer KPI |
| Washer Count | metrics.detectedCounts.washer ?? 0 | integer KPI |
| Thread Count | metrics.detectedCounts.thread ?? 0 | integer KPI |
| Total Instance Count | metrics.detectedInstanceCount | integer KPI |
| Inference Time | metrics.inferenceTimeMs | ms 표시 |
| Measured Thread | metrics.measuredThreadCm | fasteningEvaluated일 때 cm 표시 |
| Threshold | metrics.threadThresholdCm | fasteningEvaluated일 때 cm 표시 |
| Defect Reasons | metrics.assemblyReasons | code-to-label 후 목록 표시 |
| Last Inspection | inspectionTime | Date 파싱 후 사용자 지역 시간 표시 |

## 14. MJPEG, latest result, DB history의 차이

| 목적 | Endpoint / 경로 | 원본 | 호출 방식 |
|---|---|---|---|
| 실시간 영상 | GET /api/v1/stream | encoded_frames | img src로 연속 MJPEG 연결 |
| 현재 검사 상태/KPI | GET /api/v1/inspection/latest | latest_results | 1000ms polling 권장 |
| 과거 이벤트 목록 | GET /api/v1/inspections | PostgreSQL | 화면 진입, 필터/페이지 변경, 수동 새로고침 |
| 과거 이벤트 상세 | GET /api/v1/inspections/{id} | PostgreSQL | 항목 선택 시 |
| 저장 불량 이미지 | GET /api/v1/inspections/{id}/image | 파일 저장소 | 이력 상세에서 필요할 때 |

latest API의 JSON에는 resultImage나 image URL이 없다. 현재 처리 영상을 보여 줄 때는 MJPEG 영역을 함께 배치한다.

## 15. EventManager / PostgreSQL과 책임 분리

```text
                    InspectionResult
                           │
              ┌────────────┴────────────┐
              ↓                         ↓
        latest_results              EventManager
              ↓                         ↓
        Latest REST API        sampling / 중복 판정
              ↓                         ↓
            React              PersistenceWorker
                                        ↓
                                  PostgreSQL
                                        ↓
                                  History API
```

- latest_results: 매 Vision 처리의 현재 상태
- EventManager: 저장할 불량 이벤트인지 결정
- PostgreSQL: 확정된 과거 검사 이력
- encoded_frames: 브라우저용 MJPEG 영상

GET /api/v1/inspection/latest 요청은 EventManager를 실행하지 않고 DB INSERT도 만들지 않는다. latest API polling 주기와 EVENT_SAMPLE_FPS는 서로 독립적이다.

## 프론트엔드 빠른 요약

```text
영상:
GET /api/v1/stream → React 영상 영역

실시간 검사 데이터:
GET /api/v1/inspection/latest → React Dashboard/KPI

과거 검사 이력:
GET /api/v1/inspections → PostgreSQL

DB 저장 여부:
VisionWorker → EventManager → PersistenceWorker → PostgreSQL
```
