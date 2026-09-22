# Vision 내부 HTTP API

Backend만 호출하는 YOLO segmentation 추론 서비스다. 품질 판정과 Rule Engine은 이 서비스의 책임이 아니다.

## 실행

로컬 segmentation 가중치 경로를 지정한다. 파일이 없으면 Ultralytics가 모델을 자동 다운로드하도록 넘기지 않고 `MODEL_NOT_AVAILABLE`을 반환한다.

```powershell
$env:MODEL_PATH = "C:\models\best.pt"
uvicorn api.main:app --host 0.0.0.0 --port 8001
```

의존성 설치와 테스트:

```powershell
pip install -r requirements.txt
pip install -r requirements-test.txt  # 모델을 로드하지 않는 contract/unit test 최소 의존성
pytest -q
```

개발 환경 전체 의존성은 `requirements-dev.txt`로 한 번에 설치할 수 있다.

환경 변수:

- `MODEL_PATH`: 로컬 YOLO segmentation weights. 기본값 `vision-service/models/best.pt` (Docker는 `/models/best.pt`)
- `MAX_IMAGE_BYTES`: 업로드 제한. 기본값 10 MiB
- `MAX_IMAGE_PIXELS`: 디코딩 이미지 픽셀 수 제한. 기본값 40,000,000
- `MAX_IMAGE_DIMENSION`: 한 변의 최대 픽셀. 기본값 8,192
- `MAX_TOTAL_POLYGON_POINTS`: 단일 응답 전체 polygon point 제한. 기본값 200,000
- `VISION_SERVICE_TOKEN`: 선택값. 설정하면 요청의 `X-Vision-Service-Token`과 일치해야 한다.

개별 응답 한도는 detection 1,000개, polygon당 point 10,000개다. polygon 일부를 잘라 의미를 바꾸지 않으며 한도를 넘으면 추론 실패로 처리한다. Backend 호출자의 read timeout은 60초로 구성되어 있다.

## API

`POST /internal/v1/infer/segmentation`, `multipart/form-data`

- `image` (필수): JPEG, PNG 또는 WebP
- `confidenceThreshold` (선택): `0.0`~`1.0`, 기본값 `0.01`

성공 응답:

```json
{
  "modelVersion": "<weights SHA-256 hex>",
  "width": 1280,
  "height": 720,
  "detections": [
    {
      "className": "bolt",
      "confidence": 0.97,
      "bbox": {"x1": 100.0, "y1": 120.0, "x2": 300.0, "y2": 450.0},
      "segmentation": [[100.0, 120.0], [300.0, 120.0], [300.0, 450.0]]
    }
  ]
}
```

`modelVersion`은 요청에 실제 사용된 weights 파일 바이트의 SHA-256이다. 추론은 프로세스 내 lock으로 직렬화하며 모델은 첫 요청에서 lazy load한다. 좌표는 유한성을 검사하고 원본 이미지 경계로 제한한다. class label은 앞뒤 공백 제거 후 소문자로 정규화한다. 모델 label은 `bolt`, `nut`, `washer`를 사용하며 의미가 다른 alias는 자동 치환하지 않는다.

오류 응답은 항상 다음 형태다.

```json
{"code": "MODEL_NOT_AVAILABLE", "message": "The segmentation model is not available."}
```

주요 코드는 `INVALID_IMAGE`, `IMAGE_TOO_LARGE`, `INVALID_REQUEST`, `MODEL_NOT_AVAILABLE`, `VISION_INFERENCE_FAILED`다. 내부 예외와 stack trace는 응답에 포함하지 않는다.

구현은 Ultralytics 공식 Predict/Segmentation 결과 계약의 `boxes.xyxy`, `boxes.conf`, `boxes.cls`, `masks.xy`를 사용한다.
