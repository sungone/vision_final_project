USB/UVC 카메라를 기준으로 수정한 전체 아키텍처입니다.

```mermaid
flowchart TD
    %% Camera input
    CAMERA["USB / UVC Camera"]
    DEVICE["OS Camera Device<br/>Windows: Camera Index<br/>Linux: /dev/video*"]
    CAPTURE["CameraCaptureWorker<br/>OpenCV VideoCapture"]
    RAW_BUFFER["Latest Raw Frame Buffer<br/>최신 프레임 1장"]

    CAMERA --> DEVICE
    DEVICE --> CAPTURE
    CAPTURE --> RAW_BUFFER

    %% Vision pipeline
    VISION_WORKER["VisionWorker<br/>독립 Background Thread"]
    PROCESSOR["VisionProcessor Interface"]

    YOLO["YOLO26 Segmentation<br/>Future"]
    RULE_ENGINE["Rule Engine<br/>Future"]
    KPI["KPI Extraction<br/>Future"]
    MOCK["MockVisionProcessor<br/>Current MVP"]

    RESULT["InspectionResult<br/>NORMAL / DEFECT<br/>세부 판정 / Metrics"]
    VISUALIZATION["OpenCV Visualization<br/>Mask / Contour / Text / KPI"]
    PROCESSED_BUFFER["Latest Processed Frame Buffer"]

    RAW_BUFFER --> VISION_WORKER
    VISION_WORKER --> PROCESSOR

    PROCESSOR --> MOCK
    PROCESSOR -. "향후 교체" .-> YOLO

    YOLO --> RULE_ENGINE
    RULE_ENGINE --> KPI

    MOCK --> RESULT
    MOCK --> VISUALIZATION

    KPI --> RESULT
    KPI --> VISUALIZATION

    VISUALIZATION --> PROCESSED_BUFFER

    %% Video path
    JPEG["JPEG Encoding<br/>cv2.imencode"]
    JPEG_BUFFER["Latest Encoded JPEG Buffer"]
    MJPEG["MJPEG Streaming<br/>GET /api/v1/stream"]
    VIDEO_UI["React / Browser<br/>Video View"]

    PROCESSED_BUFFER --> JPEG
    JPEG --> JPEG_BUFFER
    JPEG_BUFFER --> MJPEG
    MJPEG --> VIDEO_UI

    %% Inspection data path
    EVENT_MANAGER["InspectionEventManager<br/>State Machine"]
    CONFIRMED_EVENT["Confirmed Inspection Event<br/>1회 생성"]
    SERVICE["InspectionService"]
    IMAGE_STORAGE["Local Image Storage<br/>Defect Evidence"]
    DATABASE[("PostgreSQL<br/>Inspection Events")]
    REST_API["Flask REST API"]
    DATA_UI["React / Browser<br/>Result View"]

    RESULT --> EVENT_MANAGER
    EVENT_MANAGER -->|"연속 DEFECT 확정"| CONFIRMED_EVENT
    CONFIRMED_EVENT --> SERVICE

    SERVICE --> IMAGE_STORAGE
    SERVICE --> DATABASE

    DATABASE --> REST_API
    IMAGE_STORAGE --> REST_API
    REST_API --> DATA_UI
```

### 실행 컴포넌트 관계

```mermaid
flowchart LR
    subgraph FLASK["Flask Backend Process"]
        direction TB

        subgraph CAPTURE_THREAD["Camera Capture Thread"]
            VIDEO_CAPTURE["cv2.VideoCapture"]
            CAPTURE_LOOP["capture.read loop"]
            VIDEO_CAPTURE --> CAPTURE_LOOP
        end

        RAW["Latest Raw Frame Buffer"]

        subgraph VISION_THREAD["Vision Worker Thread"]
            PROCESS["VisionProcessor"]
            DRAW["OpenCV Overlay"]
            ENCODE["JPEG Encoding"]
            EVENT["Event Manager"]
            PROCESS --> DRAW
            DRAW --> ENCODE
            PROCESS --> EVENT
        end

        JPEG["Latest JPEG Buffer"]
        DB[("PostgreSQL")]

        subgraph HTTP_THREADS["Flask HTTP Requests"]
            STREAM_API["/api/v1/stream"]
            INSPECTION_API["/api/v1/inspections"]
            STATUS_API["/api/v1/system/status"]
        end

        CAPTURE_LOOP --> RAW
        RAW --> PROCESS
        ENCODE --> JPEG
        EVENT -->|"확정 이벤트만"| DB

        JPEG --> STREAM_API
        DB --> INSPECTION_API
        RAW -. "상태 확인" .-> STATUS_API
    end

    STREAM_API --> CLIENT["React / Browser"]
    INSPECTION_API --> CLIENT
    STATUS_API --> CLIENT
```

### Event Manager 상태 머신

```mermaid
stateDiagram-v2
    [*] --> NORMAL

    NORMAL --> DEFECT_CANDIDATE: DEFECT frame 수신

    DEFECT_CANDIDATE --> DEFECT_CANDIDATE: 연속 DEFECT 수가 N 미만
    DEFECT_CANDIDATE --> NORMAL: NORMAL frame 수신
    DEFECT_CANDIDATE --> CONFIRMED_DEFECT: N frame 연속 DEFECT

    CONFIRMED_DEFECT --> CONFIRMED_DEFECT: DEFECT 유지\n추가 DB INSERT 금지
    CONFIRMED_DEFECT --> CONFIRMED_DEFECT: NORMAL 연속 수가 M 미만
    CONFIRMED_DEFECT --> NORMAL: M frame 연속 NORMAL

    note right of CONFIRMED_DEFECT
        최초 진입할 때만
        Inspection Event 1회 저장
    end note
```

### FPS 분리 구조

```mermaid
flowchart LR
    CAMERA["USB Camera<br/>CAMERA_FPS = 30"]
    RAW["Latest Raw Frame<br/>중간 프레임 제거"]
    VISION["Vision Worker<br/>VISION_FPS = 5~15"]
    JPEG["Latest JPEG"]
    STREAM["MJPEG Stream<br/>STREAM_FPS = 5~15"]
    UI["React / Browser"]

    CAMERA -->|"capture마다 갱신"| RAW
    RAW -->|"가장 최신 frame 처리"| VISION
    VISION --> JPEG
    JPEG -->|"가장 최신 JPEG 전송"| STREAM
    STREAM --> UI
```

### 배포 구조

```mermaid
flowchart TD
    subgraph DEVELOPMENT["Windows 개발 환경"]
        USB_WIN["USB / UVC Camera"]
        WIN_DEVICE["Windows Camera Device"]
        WIN_BACKEND["Flask + OpenCV Backend<br/>Windows Host"]
        WIN_DB[("PostgreSQL<br/>Docker")]

        USB_WIN --> WIN_DEVICE
        WIN_DEVICE --> WIN_BACKEND
        WIN_BACKEND --> WIN_DB
    end

    subgraph PRODUCTION["Linux 생산 / Edge 환경"]
        USB_LINUX["USB / UVC Camera"]
        VIDEO_DEVICE["/dev/video0"]
        BACKEND_CONTAINER["Flask + OpenCV<br/>Docker Container"]
        DB_CONTAINER[("PostgreSQL<br/>Docker Container")]

        USB_LINUX --> VIDEO_DEVICE
        VIDEO_DEVICE -->|"device passthrough"| BACKEND_CONTAINER
        BACKEND_CONTAINER --> DB_CONTAINER
    end
```

최종 핵심 흐름은 다음과 같습니다.

```text
USB/UVC Camera
→ OpenCV Camera Worker
→ Latest Raw Frame
→ Vision Worker
→ YOLO/Rule Engine
→ Processed Frame + Inspection Result
├── JPEG → MJPEG → React
└── Event Manager → PostgreSQL → REST API → React
```