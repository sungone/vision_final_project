# Backend 구현 계약

이 문서는 현재 실행 코드의 기준입니다. 초기 MVP의 3필드/NORMAL·DEFECT 계약을 이번 요청의 `/api`, `PASS`/`FAIL`, DB·이력·KPI 계약으로 확장했습니다. 저장소 조사 당시 실행 코드나 React API 호출, 학습 모델, DB 스키마는 없었으므로 기존 `backend`, `vision-service`, `frontend`, `storage` 경로를 그대로 사용했습니다.

## 계층과 검사 파이프라인

```text
React API client
 → InspectionController (multipart/metadata)
 → InspectionService
   → ImageValidator (확장자/MIME/실제 디코더/바이트/픽셀 제한)
   → SettingsRepository (불변 판정 스냅샷)
   → InspectionRepository.reserve (PROCESSING)
   → ImageStorageService.save (원본)
   → VisionService / YoloInferenceService (내부 HTTP, 응답 제한/검증)
      → Python YoloSegmentationService (local best.pt, segmentation 결과)
   → InspectionRuleEngine
      → ComponentRule / PostProcessor
      → AssemblyOrderRule
      → FasteningRule
   → ProcessedImageRenderer (마스크/박스/최종 판정)
   → ImageStorageService.save (JPEG)
   → InspectionRepository.complete + InspectionDetectionRepository (단일 DB 트랜잭션)
   → InspectionResponse
```

추론 동안 DB 트랜잭션을 열어 두지 않습니다. 이미지 유효성 검증 후 내구성 있는 PROCESSING 레코드를 먼저 예약하여 프로세스 중단도 검사 ID로 추적할 수 있게 했습니다. 공개 이력과 KPI에는 COMPLETED만 포함합니다. 검사 실패와 품질 FAIL은 다른 상태입니다.

## 실행 전제와 판정의 의미

- 한 장에 한 조립체, 필수 클래스는 `bolt`, `washer`, `nut` 각 1개입니다. 대소문자/주변 공백은 정규화합니다. 다른 라벨 이름은 모델/Adapter에서 명시적으로 매핑해야 합니다.
- `bolt` 마스크의 중심이 볼트 머리를 대표하고, `bolt → washer → nut`로 투영 순서가 나타나는 촬영 조건을 기본 가정으로 합니다. 전체 볼트 몸통을 하나의 마스크로 학습한 경우 중심 위치가 다를 수 있으므로 검증 데이터에 맞게 `AssemblyOrderRule` 또는 라벨 정책을 변경해야 합니다.
- `confidenceThreshold` 미만은 품질 판정에 사용하지 않되, 원래 검출과 최대 confidence는 이력에 보존합니다. 인식 Adapter의 모델 호출 confidence floor는 0.001입니다.
- 누락, 중복, 사용할 수 없는 마스크는 구성 검사 FAIL입니다. 낮은 confidence만으로 물리적 부품 누락을 확정하지 않으며 defect code를 함께 확인해야 합니다.
- `PostProcessor`는 polygon 면적 중심과 검사축 투영 구간을 계산합니다. 순서가 같거나 기대 순서와 다르면 ORDER_ERROR입니다.
- 체결 gap은 washer/nut 축 투영 구간 사이의 비음수 간격이며 겹치는 투영은 0px입니다. 3개 부품의 축 수직 방향 중심 최대 편차가 `alignmentTolerance` 이하여야 합니다. gap과 정렬 모두 임계값 이내이면 PASS입니다.
- 선행 검사에 실패하면 후속 검사는 `SKIPPED`, 측정 불가능한 gap은 `null`입니다. SKIPPED를 정상 또는 별도 불량 수로 세지 않습니다. 최종 결과는 PASS/FAIL입니다.
- gap/정렬 단위는 **px**입니다. 이미지 해상도·촬영 배율·각도에 민감합니다. mm 변환/실제 토크/가림 상태 판별/다중 조립체 분리는 구현하지 않았습니다. 이 알고리즘은 승인된 골든 데이터로 보정한 후 생산 판정에 사용해야 합니다.
- 모델은 로컬 파일만 로드하며 미준비 시 MODEL_NOT_AVAILABLE입니다. weight SHA-256이 `modelVersion`, 판정 코드 버전은 `geometry-v1`입니다. 모델 배포는 파일 변경 후 Vision 프로세스를 재시작합니다.

## API

| Method | 경로 | 기능 |
|---|---|---|
| POST | `/api/inspections` | 이미지 분석·저장, 성공 201 + Location |
| GET | `/api/inspections` | 0부터 시작하는 pagination 및 필터 |
| GET | `/api/inspections/{uuid}` | 저장 당시 결과·측정·설정·모델·검출 상세 |
| GET | `/api/inspections/{uuid}/images/original` | 검증된 원본 PNG/JPEG |
| GET | `/api/inspections/{uuid}/images/processed` | bbox/polygon/판정 JPEG |
| GET | `/api/dashboard/summary` | SQL 집계 KPI |
| GET | `/api/dashboard/recent-inspections?limit=8` | 최근 완료 검사(최대 100) |
| GET | `/api/settings/inspection-rules` | 현재 판정 설정 |
| PUT | `/api/settings/inspection-rules` | 설정 전체 교체, X-Settings-Key 필요 |

업로드 multipart field `image`는 JPEG/PNG 한 장입니다. `equipmentId`, `productCode`, `lotNumber`, `operatorId`는 각 최대 100자의 선택적 text field이며 생략 시 null입니다. 이미지 기본 제한은 10MiB/40MP/한 변 8,192px이고 서버 multipart 전체 요청 제한은 11MB입니다. 파일명은 저장 경로에 사용하지 않습니다.

이력 필터: `page=0`, `size=20` (1~100), `result=PASS|FAIL`, `startDate`, `endDate`, `productCode`, `equipmentId`, `lotNumber`. 날짜는 timezone을 포함한 ISO-8601 시각(`2026-09-22T00:00:00+09:00`)이며 양 끝을 포함합니다. URL에서 `+`는 `%2B`로 인코딩하세요. `startDate > endDate`는 400입니다. 시간과 UUID 역순으로 정렬하여 동률에서도 순서가 결정됩니다. 각 페이지의 count/list는 동일한 REPEATABLE_READ 스냅샷에서 조회합니다. 서로 다른 페이지 요청 사이의 신규 검사 삽입에는 offset pagination 특성이 적용됩니다.

Dashboard summary는 result/page/size를 제외한 위 필터를 받습니다. `passRate`/`failRate`는 0~100 백분율로 소수 둘째 자리까지 계산합니다. 검사가 없으면 count/rate는 0, 평균은 null입니다. 항목별 defect 수는 해당 검사 결과가 FAIL인 개수이며, 단순 합이 전체 FAIL 수와 같다고 가정하지 않습니다. 평균은 측정값이 있는 행만 대상으로 합니다.

### 검사 응답 예

```json
{
  "inspectionId": "02ccff4b-4009-4ae2-8b7b-71358877be17",
  "inspectionTime": "2026-09-22T05:30:00Z",
  "overallResult": "PASS",
  "componentCheck": {"result":"PASS","boltDetected":true,"nutDetected":true,"washerDetected":true,"detail":"..."},
  "orderCheck": {"result":"PASS","actualOrder":["bolt","washer","nut"],"expectedOrder":["bolt","washer","nut"],"axisDirection":"Y_POSITIVE","detail":"..."},
  "fasteningCheck": {"result":"PASS","gap":2.0,"threshold":3.0,"unit":"px","lateralOffset":0.0,"alignmentTolerance":10.0,"detail":"..."},
  "measurements": {"boltConfidence":0.97,"nutConfidence":0.95,"washerConfidence":0.94},
  "defectCodes": [],
  "images": {"originalUrl":"/api/inspections/02ccff4b-4009-4ae2-8b7b-71358877be17/images/original","processedUrl":"/api/inspections/02ccff4b-4009-4ae2-8b7b-71358877be17/images/processed"},
  "modelVersion": "weights-sha256",
  "ruleVersion": "geometry-v1",
  "ruleSnapshot": {"confidenceThreshold":0.7,"fasteningGapThreshold":3.0,"axisDirection":"Y_POSITIVE","expectedOrder":["bolt","washer","nut"],"alignmentTolerance":10.0,"ruleVersion":"geometry-v1"},
  "metadata": {"equipmentId":null,"productCode":null,"lotNumber":null,"operatorId":null},
  "imageSha256": "original-sha256",
  "detections": []
}
```

UUID를 사용하므로 Frontend에서 검사 ID를 숫자로 변환하지 않습니다. API timestamp는 UTC이며 화면에서 Asia/Seoul로 표시할 수 있습니다. `images` URL은 Backend 상대 경로입니다. Frontend와 Backend origin이 다르면 API client의 `imageUrl()`로 합칩니다. DB Entity나 물리 파일 경로를 응답하지 않습니다.

### 설정 변경

```sh
curl -X PUT http://localhost:8080/api/settings/inspection-rules \
  -H 'Content-Type: application/json' -H 'X-Settings-Key: YOUR_KEY' \
  -d '{"confidenceThreshold":0.7,"fasteningGapThreshold":3.0,"axisDirection":"Y_POSITIVE","expectedOrder":["bolt","washer","nut"],"alignmentTolerance":10.0,"ruleVersion":"geometry-v1"}'
```

PUT은 전체 필드를 요구합니다. confidence는 [0,1], gap/정렬 임계값은 유한한 0 이상 수치, 축은 X/Y_POSITIVE/NEGATIVE, 순서는 3개 클래스의 permutation입니다. ruleVersion은 배포된 코드 버전이므로 임의 변경하지 못합니다. 키가 미설정이면 읽기 전용, 잘못된 키는 403입니다. 키를 Frontend 소스나 공개 환경 변수에 넣지 말고 향후 관리자 인증 시스템으로 대체하세요.

## PostgreSQL과 저장소

- `inspection`: 상태, 시간, 경로, 결과별 검색/집계 컬럼, 모델 버전, `rule_snapshot` JSONB, `decision` JSONB, metadata, 원본 SHA-256, failure code.
- `inspection_detection`: inspection FK, confidence, bbox JSONB, segmentation polygon JSONB.
- `inspection_rule_settings`: singleton 설정, revision, updated_at. 완성된 검사는 이 테이블을 다시 참조해 판정하지 않습니다.
- 검사 시간/결과/품목/설비/LOT 및 detection FK에 인덱스가 있습니다. 평균/count는 SQL에서 집계합니다.
- Raster mask/이미지 binary를 DB에 넣지 않습니다. 비교적 작은 polygon만 저장하며 Vision 응답은 최대 8MiB, 1,000 detections, polygon당 10,000점으로 제한합니다. 대형 mask가 필요해지면 detection에 object key를 추가해 파일/Object Storage로 이전할 수 있습니다.
- 키: `inspections/YYYY/MM/DD/{uuid}/original.jpg|png`, `processed.jpg` (UTC 일자). `ImageStorageService`를 교체하면 S3/MinIO로 이전 가능합니다.
- 로컬 저장은 임시 파일 후 rename, root 경계·심볼릭 링크 검사를 수행합니다. 저장소는 서비스 전용 쓰기 권한으로 운영해야 합니다.

## 실패와 복구

1. 입력 오류는 파일/DB 저장 전에 반환합니다.
2. 추론·후처리·저장 실패는 PROCESSING → FAILED 후 해당 검사 폴더를 제거합니다.
3. 완료 UPDATE와 detection INSERT는 같은 DB 트랜잭션입니다. detection 저장 실패는 완료 상태까지 롤백됩니다.
4. commit 응답 유실처럼 완료 여부가 불명확할 때 DB 상태를 다시 확인합니다. 이미 COMPLETED라면 저장된 결과를 반환하고 이미지를 지우지 않습니다.
5. DB 자체가 불통이면 파일을 보존하고 검사 ID를 서버 로그에 기록합니다. 장애 중 무조건 삭제하면 실제 commit된 검사 이미지가 사라질 수 있기 때문입니다.
6. 프로세스 강제 종료나 파일 삭제 실패로 남는 PROCESSING/FAILED 자료는 운영자 reconciliation 대상입니다. 요청 처리 중인 인스턴스가 없는 점을 확인한 뒤 DB 상태에 따라 복구/정리합니다. 자동 보존기한 삭제 작업은 아직 없습니다. DB와 Object Storage는 하나의 ACID 트랜잭션이 아니며 이 제한을 숨기지 않습니다.

점검 조회:

```sql
SELECT id, status, inspection_time, failure_code, original_image_path, processed_image_path
FROM inspection WHERE status <> 'COMPLETED' ORDER BY inspection_time;
```

## 오류

```json
{"timestamp":"2026-09-22T05:30:00Z","status":503,"code":"MODEL_NOT_AVAILABLE","message":"Vision 모델이 준비되지 않았습니다."}
```

- 400: INVALID_IMAGE, INVALID_REQUEST, INVALID_RULE_SETTING
- 413: IMAGE_TOO_LARGE
- 404: INSPECTION_NOT_FOUND, IMAGE_NOT_FOUND
- 502: VISION_INFERENCE_FAILED (timeout/잘못된 내부 응답 포함)
- 503: MODEL_NOT_AVAILABLE, DATABASE_ERROR, SETTINGS_READ_ONLY
- 500: IMAGE_STORAGE_FAILED, INTERNAL_ERROR
- 403: FORBIDDEN

내부 exception/SQL/서버 경로/모델 stack trace는 공개 응답에 포함하지 않습니다. 서버 로그에서 확인합니다. Vision 서비스는 내부 API이며 선택적으로 서비스 토큰 인증을 지원합니다. `VISION_SERVICE_TOKEN`을 설정하면 Backend가 `X-Vision-Service-Token` 헤더로 전달합니다.

## 검증 범위

- 순수 Rule 테스트: 정상, 각 부품 누락, 저신뢰도, 중복, 순서 오류, gap 경계/초과, 역방향 축, 순서 permutation, 정렬 오류, 마스크/좌표 오류.
- 이미지 테스트: 유효 이미지, 실제 형식과 MIME/확장자 불일치, 손상 파일, 용량/픽셀 초과, 경로 탈출, 저장/조회/삭제, 오버레이.
- PostgreSQL 통합 테스트: Flyway, multipart 업로드, detection 저장, 이력 필터/KPI, 상세/이미지 조회, threshold 스냅샷, model/DB/storage 실패 정리, commit 응답 유실.
- HTTP Adapter 테스트: 실제 local HTTP multipart 전송, DTO 파싱, 내부 오류 정제, 비정상 응답.
- Python tests: 가짜 YOLO raw result로 변환 계약과 예외 처리 검증. 실제 학습 weights/승인 데이터가 저장소에 없으므로 실제 추론 품질/정확도 검증은 별도 필요합니다.

관련 구현 기준: [Spring multipart REST client](https://docs.spring.io/spring-framework/reference/6.2/integration/rest-clients.html), [Ultralytics prediction results](https://docs.ultralytics.com/modes/predict/).


