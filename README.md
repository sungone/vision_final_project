# Vision Inspection Backend MVP

USB/UVC 카메라 영상에서 Bolt, Nut, Washer 조립 상태를 검사하기 위한 Flask 기반 실시간 백엔드입니다. 현재 단계는 카메라 수집, 스레드 안전한 최신 프레임 전달, Mock Vision 처리, MJPEG 스트리밍, 검사 이벤트 중복 억제, PostgreSQL 조회 API에 집중합니다.

YOLO26 학습·추론, 실제 Missing/Alignment/Fastening 판정, KPI 계산, 완성된 React UI는 이 MVP의 범위가 아닙니다.

## 핵심 구조

```text
USB/UVC Camera → OpenCV Capture Worker → Latest Raw Frame
                                      ↓
                                Vision Worker
                                      ↓
                      Latest Processed Frame + Result
                              ↙                    ↘
                      JPEG / MJPEG              Event Manager
                              ↓                    ↓
                            React              PostgreSQL
                                                   ↓
                                             REST GET API
```

- Camera capture, vision processing, MJPEG response는 서로 다른 실행 경로를 사용합니다.
- 여러 브라우저가 접속해도 camera 또는 vision worker가 추가로 생성되지 않습니다.
- 최신 프레임 하나만 유지해 지연이 누적되는 queue backlog를 방지합니다.
- `DEFECT` frame마다 저장하지 않고 상태 전이로 확정된 inspection event만 저장합니다.
- Vision processor 경계를 유지하므로 추후 Mock 구현을 YOLO26 + Rule Engine으로 교체할 수 있습니다.

자세한 설계는 [Architecture](docs/ARCHITECTURE.md), API 계약은 [API](docs/API.md), 저장 모델은 [Database](docs/DATABASE.md)를 참고하세요.

## 요구 사항

- Python 3.11 이상
- PostgreSQL 16 권장
- OpenCV가 인식할 수 있는 USB/UVC 카메라
- Docker Compose는 PostgreSQL 실행에만 사용합니다.

## 로컬 실행

USB/UVC 카메라는 Windows 호스트의 OpenCV가 직접 사용합니다. PostgreSQL만 Docker Compose로 실행하고 Flask 백엔드는 Windows 호스트에서 실행합니다.

### 1. PostgreSQL 실행

```powershell
docker compose up -d db
```

기본 개발 DB는 다음과 같습니다.

```text
database: vision_inspection
user:     vision
password: vision
port:     5432
```

이 값은 로컬 개발 전용입니다. 공유 또는 운영 환경에서는 반드시 환경변수로 변경하세요.

### 2. Python 환경 준비

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
```

### 3. 환경변수 설정

PowerShell 예시:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://vision:vision@localhost:5432/vision_inspection"
$env:CAMERA_INDEX = "2"
$env:CAMERA_WIDTH = "1280"
$env:CAMERA_HEIGHT = "720"
$env:CAMERA_FPS = "30"
$env:VISION_FPS = "10"
$env:STREAM_FPS = "10"
$env:JPEG_QUALITY = "80"
$env:DEFECT_CONFIRM_FRAMES = "3"
$env:NORMAL_RESET_FRAMES = "5"
$env:EVENT_COOLDOWN_SECONDS = "0"
$env:DEFECT_STORAGE_DIR = "backend/storage/defects"
$env:START_BACKGROUND_WORKERS = "true"
```

`CAMERA_INDEX`는 USB/UVC 카메라가 등록된 장치 번호로 변경하세요.

### 4. Flask 실행

```powershell
.\.venv\Scripts\python backend\run.py
```

기본 주소는 `http://localhost:5000`입니다.

## 동작 확인

상태 조회:

```powershell
Invoke-RestMethod http://localhost:5000/api/v1/system/status
```

최신 검사 결과:

```powershell
Invoke-WebRequest http://localhost:5000/api/v1/inspection/latest
```

MJPEG 확인은 브라우저에서 다음 주소를 여세요.

```text
http://localhost:5000/api/v1/stream
```

또는 React/HTML에서 사용합니다.

```html
<img src="http://localhost:5000/api/v1/stream" alt="Inspection stream">
```

## 환경설정

| 변수 | 기본값 | 설명 |
| --- | ---: | --- |
| `DATABASE_URL` | 개발 환경별 설정 | PostgreSQL SQLAlchemy URL |
| `CAMERA_INDEX` | `0` | OpenCV camera index |
| `CAMERA_WIDTH` | `1280` | 요청 capture 폭 |
| `CAMERA_HEIGHT` | `720` | 요청 capture 높이 |
| `CAMERA_FPS` | `30` | camera capture 목표 FPS |
| `VISION_FPS` | `10` | mock/future vision 처리 목표 FPS |
| `STREAM_FPS` | `10` | MJPEG 전송 최대 FPS |
| `JPEG_QUALITY` | `80` | OpenCV JPEG quality, 1–100 |
| `DEFECT_CONFIRM_FRAMES` | `3` | defect 확정에 필요한 연속 frame 수 |
| `NORMAL_RESET_FRAMES` | `5` | 다음 event를 허용하기 위한 연속 normal frame 수 |
| `EVENT_COOLDOWN_SECONDS` | `0` | 상태머신을 보조하는 선택적 cooldown |
| `DEFECT_STORAGE_DIR` | `backend/storage/defects` | defect evidence 이미지 경로 |
| `DATABASE_AUTO_CREATE` | 환경별 설정 | 개발용 schema 자동 생성 여부 |
| `START_BACKGROUND_WORKERS` | `true` | camera/vision worker 시작 여부 |

Camera FPS, Vision FPS, Stream FPS는 독립적입니다. 30 FPS 카메라를 사용하더라도 vision과 browser stream은 5–15 FPS로 운영할 수 있습니다.

## REST API

| Method | Path | 목적 |
| --- | --- | --- |
| `GET` | `/api/v1/stream` | MJPEG processed-frame stream |
| `GET` | `/api/v1/inspection/latest` | 최근 inspection event |
| `GET` | `/api/v1/inspections?page=0&size=20` | 검사 이력 |
| `GET` | `/api/v1/inspections/{id}` | 검사 상세 |
| `GET` | `/api/v1/inspections/{id}/image` | 저장된 evidence image |
| `GET` | `/api/v1/system/status` | camera/worker/database 상태 |
| `GET` | `/stream-test` | 최소 MJPEG 브라우저 테스트 페이지 |

## 테스트

```powershell
.\.venv\Scripts\python -m pytest -q
```

현재 단위 테스트는 실제 USB/UVC 카메라나 PostgreSQL 없이 frame buffer, event manager, mock vision processor, MJPEG 생성기를 검증합니다. 실제 카메라와 PostgreSQL 연결은 로컬 smoke test로 별도 확인합니다.

## 현재 범위 밖

- YOLO26 segmentation 학습 및 `.pt` inference
- 실제 부품 누락·정렬·체결 판정
- 실제 KPI 계산
- 제품 추적 또는 PLC 연동
- WebRTC/H.264, SSE, WebSocket
- MES/ERP/재고/권한/생산계획 기능


