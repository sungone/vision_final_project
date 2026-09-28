# Backend 최종 구조 및 실행 가이드

현재 구현된 코드 기준의 Backend 아키텍처, 스레드, 파일 책임, DB/API와 실행 방법이다.

## 1. 전체 아키텍처

~~~mermaid
flowchart TD
    Camera["USB / UVC / DroidCam"] --> Capture["CameraCaptureWorker<br/>camera-capture"]
    Capture --> Raw["Latest Raw Frame Buffer"]
    Raw --> Processor["VisionProcessor<br/>U-Net / YOLO26 / Mask R-CNN"]
    Processor --> Post["Model PostProcessor"]
    Post --> Decision["InspectionDecisionEngine"]
    Decision --> Overlay["InspectionVisualizer"]
    Overlay --> Encode["JPEG Encoding"]
    Encode --> JPEG["Latest JPEG Buffer"]
    JPEG --> Stream["GET /api/v1/stream"] --> React["React / Browser"]
    Decision --> Event["InspectionEventManager"]
    Event -->|confirmed defect once| Queue["Bounded Persistence Queue"]
    Queue --> Persist["InspectionPersistenceWorker"]
    Persist --> Service["InspectionService"]
    Service --> Image["Defect JPEG Storage"]
    Service --> Repo["InspectionRepository"]
    Repo --> DB[("PostgreSQL")]
    DB --> History["Inspection GET APIs"] --> React
~~~

- 영상: 최신 프레임 하나 → 추론 → overlay → JPEG 하나 → MJPEG
- 이력: 연속 프레임 판정 → 확정된 불량 이벤트 하나 → PostgreSQL
- 매 프레임을 DB에 저장하지 않는다.
- 모델과 카메라는 HTTP 요청마다 만들지 않고 서버 시작 시 한 번 만든다.

## 2. 스레드 구조

~~~mermaid
flowchart LR
    Main["Main Flask Process"] --> HTTP["Flask Request Threads"]
    Main --> CameraT["camera-capture"]
    Main --> VisionT["vision-worker"]
    Main --> PersistT["inspection-persistence"]
    CameraT -->|LatestFrameBuffer| VisionT
    VisionT -->|Latest JPEG| HTTP
    VisionT -->|confirmed event| PersistT
    PersistT --> DB[("PostgreSQL")]
~~~

| 실행 경로 | 책임 |
|---|---|
| Flask main/request | REST, status, 이미 인코딩된 MJPEG 응답 |
| camera-capture | VideoCapture, 재연결, 최신 raw frame |
| vision-worker | 추론, 판정, overlay, JPEG 인코딩, 이벤트 전달 |
| inspection-persistence | bounded queue의 확정 이벤트를 이미지와 DB에 저장 |

MJPEG 요청은 추론하지 않는다. client가 증가해도 camera/model worker는 추가 생성되지 않는다. 시작 순서는 persistence → camera → vision이고 종료는 vision → camera → persistence다. Camera worker는 종료 시 VideoCapture.release를 호출한다.

## 3. Vision과 이벤트 흐름

~~~mermaid
flowchart TD
    Frame["BGR Raw Frame"] --> Select{VISION_PROCESSOR}
    Select -->|unet| UNet["Locator optional → Fine U-Net"]
    Select -->|yolo26| YOLO["Ultralytics YOLO Seg"]
    Select -->|mask_rcnn| Mask["Torchvision Mask R-CNN"]
    UNet --> Instances["DetectedInstance list"]
    YOLO --> Instances
    Mask --> Instances
    Instances --> Rules["Assembly + Tightness Rules"]
    Rules --> Result["InspectionResult"]
    Result --> Visual["Mask / Contour / BBox / Result Overlay"]
    Visual --> JPEG["cv2.imencode JPEG"]
~~~

공통 instance는 class_id, class_name, confidence, bbox, mask, contour, center, area_px를 가진다. DB에는 판정 재현용 요약값만 저장하며 mask 배열과 contour 전체 좌표는 저장하지 않는다.

~~~mermaid
stateDiagram-v2
    [*] --> NORMAL
    NORMAL --> CONFIRMED_DEFECT: 새 sampled signature / INSERT
    CONFIRMED_DEFECT --> CONFIRMED_DEFECT: 동일 signature / DROP
    CONFIRMED_DEFECT --> CONFIRMED_DEFECT: 변경 signature / INSERT
    CONFIRMED_DEFECT --> NORMAL: M회 sampled NORMAL / reset
    CONFIRMED_DEFECT --> NORMAL: 최초 event 전달 실패
~~~

EVENT_SAMPLE_FPS, DEFECT_GEOMETRY_TOLERANCE_RATIO, NORMAL_RESET_FRAMES는 backend/.env.local에서 조정한다. event_key unique 제약이 영속화 재시도의 중복 INSERT도 방어한다.

DefectSignature는 result enum, detectedCounts, assemblyReasons를 정확 비교한다. detection 순서를 class/y/x로 정규화한 뒤 객체 크기와 면적, 객체 쌍의 상대 dx/dy/distance, 선택적인 thread 측정 비율을 비교한다. 위치·거리에는 frame 대비 절대 허용 비율을, 크기·면적·thread 비율에는 상대 오차를 적용한다. confidence, inferenceTimeMs, timestamp, event_key와 image path는 비교하지 않는다.

## 4. Backend 파일별 책임

### 실행, 설정, API

| 파일 | 역할 |
|---|---|
| backend/run.py | Flask 실행 진입점 |
| backend/requirements.txt | Python 실행/테스트 의존성 |
| backend/.env.example | 로컬 설정 템플릿 |
| backend/.env.local | 실제 로컬 설정. Git 제외, app factory가 직접 로드 |
| backend/migrations/001_create_inspections.sql | PostgreSQL table/index 생성 |
| backend/storage/defects/.gitkeep | defect image 디렉터리 유지 |
| app/__init__.py | app factory, DB/blueprint/runtime/error/CORS 등록 |
| app/config.py | 환경변수 parsing, Config와 TestConfig |
| app/lifecycle.py | Runtime 조립, 모델 1회 로드, worker 시작/종료 |
| app/api/__init__.py | blueprint export |
| app/api/health.py | GET /api/v1/health |
| app/api/status.py | GET /api/v1/system/status |
| app/api/stream.py | MJPEG, stream-test, root redirect |
| app/api/inspections.py | 최신/목록/상세 검사와 defect image 조회 |

### Camera, streaming, Vision

| 파일 | 역할 |
|---|---|
| app/camera/__init__.py | camera class export |
| app/camera/capture.py | 단일 VideoCapture와 capture thread/reconnect/release |
| app/camera/frame_buffer.py | lock/condition 기반 latest-value buffer |
| app/streaming/__init__.py | MJPEG generator export |
| app/streaming/mjpeg.py | JPEG bytes를 multipart MJPEG chunk로 변환 |
| app/vision/__init__.py | 공통 contract/decision과 processor export |
| app/vision/contracts.py | DetectedInstance, FrameVisionResult, InspectionResult, protocol |
| app/vision/decision_engine.py | 부품 개수·역할과 나사산 길이 판정, metrics 생성 |
| app/vision/visualizer.py | frame copy에 mask/contour/bbox/result overlay |
| app/vision/worker.py | raw frame 처리, JPEG 1회 인코딩, buffer/event 갱신 |

### 모델별 패키지

| 파일 | 역할 |
|---|---|
| app/vision/unet/predictor.py | ResNet18 U-Net, locator/fine checkpoint 로딩·추론 |
| app/vision/unet/postprocessor.py | semantic mask component를 공통 instance로 변환 |
| app/vision/unet/processor.py | U-Net 전체 pipeline 조합 |
| app/vision/yolo26/predictor.py | Ultralytics .pt 로딩·추론 |
| app/vision/yolo26/postprocessor.py | YOLO mask/box/class를 공통 instance로 변환 |
| app/vision/yolo26/processor.py | YOLO 전체 pipeline 조합 |
| app/vision/mask_rcnn/predictor.py | metadata/state dict로 Mask R-CNN 구성·추론 |
| app/vision/mask_rcnn/postprocessor.py | score/mask threshold와 instance 변환 |
| app/vision/mask_rcnn/processor.py | Mask R-CNN pipeline과 명시적 test/mock processor |
| 각 모델의 __init__.py | package 공개 class export |

### 검사와 DB

| 파일 | 역할 |
|---|---|
| app/inspection/__init__.py | inspection class export |
| app/inspection/defect_signature.py | categorical/geometry signature 생성과 tolerance 비교 |
| app/inspection/event_manager.py | Vision과 독립적인 sampling, signature dedupe, normal reset |
| app/inspection/persistence_worker.py | 추론을 막지 않는 bounded DB queue와 retry |
| app/inspection/service.py | idempotency, JPEG 저장, entity 생성, rollback |
| app/database/__init__.py | SQLAlchemy export |
| app/database/db.py | Flask-SQLAlchemy instance/base |
| app/models/__init__.py | ORM model export |
| app/models/inspection.py | Inspection ORM과 API 직렬화 |
| app/repositories/__init__.py | repository export |
| app/repositories/inspection_repository.py | add/get/latest/page/event-key query |

### 회귀 테스트

| 파일 | 검증 대상 |
|---|---|
| tests/conftest.py | SQLite memory DB, Mock Vision, worker-off fixture |
| tests/test_api.py | health/status/inspection/image/error API |
| tests/test_camera_capture.py | capture/open/release |
| tests/test_frame_buffer.py | latest-value version/wait |
| tests/test_decision_engine.py | assembly/tightness/metrics |
| tests/test_event_manager.py | NG 확정, 중복 방지, reset |
| tests/test_persistence_worker.py | queue/retry/stop |
| tests/test_vision_worker.py | JPEG/event/error isolation |
| tests/test_unet_pipeline.py | U-Net contract |
| tests/test_yolo26_pipeline.py | YOLO contract |
| tests/test_mask_rcnn_pipeline.py | Mask R-CNN contract |

## 5. PostgreSQL 구조

~~~mermaid
erDiagram
    INSPECTIONS {
        bigint id PK
        timestamptz inspection_time
        varchar overall_result
        varchar missing_component_result
        varchar alignment_result
        varchar fastening_result
        jsonb metrics
        text defect_image_path
        varchar event_key UK
        timestamptz created_at
    }
~~~

| Column | 의미 |
|---|---|
| overall_result | 최종 NORMAL/DEFECT |
| missing_component_result | API assemblySequenceResult |
| alignment_result | 현재 미평가 시 NOT_EVALUATED |
| fastening_result | API fasteningQualityResult |
| metrics | 모델/검출/판정 재현용 JSONB |
| defect_image_path | DB binary가 아닌 JPEG 경로 |
| event_key | 동일 이벤트 중복 방지 |

metrics에는 modelType, detectedInstanceCount, inferenceTimeMs, detectedCounts, detections의 class/confidence/bbox/center/area, assemblyReasons, fasteningEvaluated, measuredThreadCm, threadThresholdCm, scaleCmPerPx가 저장된다.

## 6. 실제 API

| Method | Endpoint | 용도 |
|---|---|---|
| GET | /api/v1/health | service/model readiness |
| GET | /api/v1/system/status | camera/worker/model/DB 상태 |
| GET | /api/v1/stream | MJPEG |
| GET | /stream-test | MJPEG 수동 확인 |
| GET | /api/v1/inspection/latest | latest_results의 최신 실시간 검사, 없으면 204 |
| GET | /api/v1/inspections?page=0&size=20 | 검사 이력 |
| GET | /api/v1/inspections/{id} | 검사 상세 |
| GET | /api/v1/inspections/{id}/image | defect JPEG |

~~~json
{
  "id": 101,
  "inspectionTime": "2026-09-25T12:31:10+00:00",
  "overallResult": "DEFECT",
  "assemblySequenceResult": "NORMAL",
  "fasteningQualityResult": "DEFECT",
  "detectedInstanceCount": 4,
  "inferenceTimeMs": 82.4,
  "modelName": "u-net-resnet18",
  "defectImageUrl": "/api/v1/inspections/101/image"
}
~~~

현재 Backend에는 이미지 업로드용 POST /api/v1/inspections가 없다. 현재 구현은 camera 실시간 검사와 자동 이벤트 저장 방식이다. Frontend의 과거 수동 업로드 함수는 현재 Backend와 계약이 맞지 않아 호출하면 HTTP 405가 발생한다.

## 7. 전체 프로그램 실행

요구 사항은 Windows, Python 3.11 이상, Node.js/npm, Docker Desktop 또는 PostgreSQL 16, camera, 선택 모델 checkpoint다. PATH의 일반 python 대신 프로젝트 venv 실행 파일을 사용한다.

### Python 환경과 Backend 설정

~~~powershell
cd C:\sungwon\vision_final_project
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env.local
~~~

backend/.env.local에서 DATABASE_URL, CAMERA_INDEX, VISION_PROCESSOR와 선택 모델 경로를 확인한다.

~~~dotenv
DATABASE_URL=postgresql+psycopg://vision:vision@localhost:5432/vision_inspection
CAMERA_INDEX=0
VISION_PROCESSOR=unet
UNET_FINE_MODEL_PATH=../output/u-net/fine/best.pt
UNET_LOCATOR_MODEL_PATH=../output/u-net/locator/best.pt
EVENT_SAMPLE_FPS=1.0
DEFECT_GEOMETRY_TOLERANCE_RATIO=0.05
NORMAL_RESET_FRAMES=5
ALLOW_MOCK_FALLBACK=false
~~~

### PostgreSQL과 Backend

~~~powershell
docker compose up -d db
Get-Content -Raw backend\migrations\001_create_inspections.sql |
  docker compose exec -T db psql -U vision -d vision_inspection
.\.venv\Scripts\python.exe backend\run.py
~~~

상태와 영상 확인:

~~~powershell
Invoke-RestMethod http://127.0.0.1:5000/api/v1/health
Invoke-RestMethod http://127.0.0.1:5000/api/v1/system/status
~~~

브라우저 영상 주소는 http://127.0.0.1:5000/stream-test 다.

### Frontend

~~~powershell
cd C:\sungwon\vision_final_project\frontend
npm install
npm run dev
~~~

Vite는 /api를 http://localhost:5000으로 proxy하며 UI 주소는 http://localhost:5173 이다.

### Test/build

~~~powershell
cd C:\sungwon\vision_final_project
$env:PYTHONDONTWRITEBYTECODE = "1"
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider backend\tests -q
cd frontend
npm run lint
npm run build
~~~

### 종료

Backend/Frontend는 각 terminal에서 Ctrl+C로 종료하고 DB는 프로젝트 루트에서 docker compose stop db로 중지한다. docker compose down -v는 DB volume과 검사 이력을 삭제하므로 의도적으로 초기화할 때만 사용한다.

## 8. 정리 결과

- 유지: 세 모델 구현, 전체 회귀 테스트, migration, .env.local, storage .gitkeep, 명시적 Mock processor
- 삭제: app에서 로드하지 않던 구형 backend/.env, 자동 생성된 Backend __pycache__ 디렉터리
- Mock 자동 fallback은 ALLOW_MOCK_FALLBACK=false가 기본이므로 운영 오류를 자동으로 정상 판정하지 않는다.
