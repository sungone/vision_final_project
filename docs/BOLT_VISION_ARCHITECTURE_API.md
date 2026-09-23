# 볼트·너트·와셔 머신비전 검사 시스템 아키텍처 및 API 명세

> 문서 버전: 1.0  
> 대상 UI: React 기반 MES 스타일 대시보드, 이미지검사(Desktop/Mobile), 검사이력, 환경설정  
> 대상 검사: 볼트–너트–와셔 조립 순서 불량 및 체결 강도 불량

## 1. 목적과 범위

본 문서는 사용자가 이미지 1장을 업로드하면 Backend가 YOLO Segmentation 기반 `vision-service`에 추론을 요청하고, 결과를 업무 규칙에 따라 정제하여 저장·반환하는 시스템의 구현 기준을 정의한다.

주요 범위는 다음과 같다.

- 통합 대시보드: 전체 검사 수, 정상/불량 수, 불량률, 최근 검사, 기간별 추이 및 불량 유형 분포
- 이미지검사: 단일 이미지 업로드, 검사 조건 입력, 추론 실행, 원본/오버레이 결과 및 판정 근거 표시
- 검사이력: 조건 검색, 페이지 조회, 상세 결과 확인, 원본·결과 이미지 열람
- 환경설정: 판정 임계값, 모델 버전, 파일 제한, 보존 기간 등 관리
- 데이터 저장: 사용자 입력, 검사 결과, 검출 객체, 판정 근거, 모델·설정 스냅샷 및 감사 정보

이 문서는 논리 아키텍처와 API 계약을 다룬다. 실제 SVG의 색상·간격·폰트 같은 시각 토큰은 프론트엔드 디자인 시스템에서 별도로 관리한다.

## 2. 핵심 업무 규칙

### 2.1 조립 순서 판정

모델이 검출한 부품의 클래스와 segmentation mask 위치를 조립축 방향으로 정렬하여 기대 순서와 비교한다.

- 예시 기대 순서: `BOLT_HEAD -> WASHER -> NUT`
- 정상: 필수 부품이 모두 존재하고, 중심축 투영 순서가 설정값과 일치
- 순서 불량: 부품은 존재하지만 순서가 다름
- 부품 누락: 필수 클래스 중 하나 이상이 없음
- 중복/이물: 허용 수량을 초과하거나 미등록 클래스가 검출됨
- 판정 불가: 이미지 품질 저하, confidence 부족, 조립축 계산 실패

주의: 카메라 방향에 따라 축의 정렬 방향이 반대일 수 있으므로 `inspection_profiles.axis_direction`과 `expected_sequence`를 설정으로 관리한다.

### 2.2 체결 강도 판정

이미지만으로 실제 토크를 직접 측정할 수 없는 경우, 영상 기반 체결 상태를 “체결 강도 대용 지표”로 판정한다. 실제 토크 센서 값이 제공되면 센서 값을 우선 기준으로 사용한다.

- 영상 추정 방식 예: 너트 체결 위치, 노출 나사산 길이, 와셔 압착 간격, 기준 마커 대비 거리
- 센서 연동 방식: `torqueNm`이 설정 범위 내인지 판정
- 최종 판정은 `sequenceJudgement`와 `fasteningJudgement`를 조합한다.
- 하나라도 `NG`이면 최종 `NG`, 판정 불가가 포함되고 `NG`가 없으면 `REVIEW`, 모두 정상이면 `OK`

### 2.3 판정 코드

| 코드 | 의미 |
|---|---|
| `OK` | 정상 |
| `NG_SEQUENCE` | 조립 순서 불량 |
| `NG_MISSING_PART` | 부품 누락 |
| `NG_FASTENING_LOW` | 체결 부족 |
| `NG_FASTENING_HIGH` | 과체결 |
| `NG_DUPLICATE_PART` | 부품 중복 |
| `NG_IMAGE_QUALITY` | 이미지 품질 불량 |
| `REVIEW` | 자동 판정 신뢰도 부족, 작업자 확인 필요 |
| `ERROR` | 시스템 오류로 검사 미완료 |

## 3. 전체 시스템 아키텍처

```text
[React Web / Mobile Web]
   | HTTPS REST (JSON, multipart/form-data)
   v
[Backend API]
   |- 인증/권한
   |- 입력 검증 및 파일 검사
   |- Inspection Orchestrator
   |- Result Normalizer / Rule Engine
   |- Dashboard Query Service
   |- History / Settings Service
   |        | HTTP 내부망
   |        v
   |   [vision-service]
   |      |- 전처리
   |      |- YOLO Segmentation 추론
   |      |- mask/box/class/confidence 반환
   |
   |- [PostgreSQL]
   |- [Object Storage: S3/MinIO 또는 로컬 볼륨]
   `- [선택: Redis / Queue]
```

### 3.1 권장 기술 구성

| 계층 | 권장 구성 | 책임 |
|---|---|---|
| FrontEnd | React + TypeScript, React Router, TanStack Query, Zustand/Context | 화면, 서버 상태, 입력 검증, 반응형 UI |
| Backend | FastAPI 또는 NestJS/Spring Boot | API, 인증, 업무 규칙, 저장, vision 연동 |
| Vision | Python + FastAPI, Ultralytics/PyTorch | 모델 로딩, 전처리, YOLO Segmentation 추론 |
| DB | PostgreSQL | 검사·판정·설정·감사 메타데이터 |
| 파일 | S3/MinIO | 원본 이미지와 결과 오버레이 저장 |
| 캐시/큐 | Redis 선택 | 대시보드 캐시, 비동기 작업, 중복 요청 방지 |

MVP는 동기식 REST로 구성한다. 일반 검사 시간이 API Gateway 제한보다 길어지거나 GPU 대기열이 필요하면 비동기 작업 API로 확장한다.

## 4. FrontEnd 아키텍처

### 4.1 화면별 책임

| 화면 | 주요 기능 | 주요 API |
|---|---|---|
| 통합 대시보드 | KPI, 추이, 불량 분포, 최근 검사 | `GET /dashboard/summary`, `/dashboard/trends`, `/inspections` |
| 이미지검사 | 파일 선택/드롭, 미리보기, 조건 입력, 검사, 결과 표시 | `POST /inspections` |
| 검사이력 | 기간·판정·품목·라인 검색, 페이지 조회, 상세 | `GET /inspections`, `GET /inspections/{id}` |
| 환경설정 | 프로파일/임계값/모델 설정 조회·수정 | `GET/PUT /settings/inspection`, `GET /models` |

### 4.2 상태 구분

- 서버 상태: TanStack Query로 API 데이터, 캐시, 재조회, 로딩/오류 관리
- 화면 전역 상태: 사용자, 권한, 선택 라인, 테마 정도만 저장
- 검사 입력 상태: React Hook Form 등 폼 단위로 관리
- 이미지 원본은 브라우저 영구 저장소에 넣지 않고 `File` 객체와 미리보기 URL로만 유지
- 검사 성공 후 서버가 반환한 `inspectionId`를 기준으로 상세 화면을 재조회할 수 있게 구성

### 4.3 이미지검사 UI 상태 머신

```text
IDLE -> FILE_SELECTED -> VALIDATING -> UPLOADING -> INFERENCING
  -> COMPLETED(OK/NG/REVIEW)
  -> FAILED(재시도 또는 파일 교체)
```

- 업로드 중 이중 제출을 방지한다.
- 성공 전에는 결과 영역을 이전 결과로 유지하지 않는다.
- 모바일에서는 업로드/촬영 입력, 핵심 판정, 재검사 버튼을 우선 배치한다.
- 데스크톱에서는 원본/결과 이미지 비교와 검출 상세를 2열로 표시한다.
- 서버 판정 코드와 화면 문구를 분리해 다국어·문구 변경이 API 계약을 깨지 않게 한다.

## 5. Backend 아키텍처

### 5.1 계층

```text
Controller/Router
  -> Application Service (use case)
     -> Domain Rule / Result Normalizer
        -> Repository (DB)
        -> Object Storage Adapter
        -> Vision Client Adapter
```

- Controller: HTTP 파싱, 인증 컨텍스트, DTO 검증
- Application Service: 검사 트랜잭션과 외부 호출 순서 조정
- Vision Client: vision-service 계약을 내부 도메인과 격리
- Normalizer/Rule Engine: 검출값 정제, 순서 계산, 임계값 적용, 최종 판정
- Repository: DB 영속화
- Storage Adapter: 원본·오버레이 이미지 저장 및 제한된 접근 URL 생성

### 5.2 단일 검사 처리 순서

1. FrontEnd가 `multipart/form-data`로 이미지 1장과 메타데이터를 전송한다.
2. Backend가 인증, 확장자, MIME, magic bytes, 용량, 해상도와 필수 입력을 검증한다.
3. `idempotencyKey` 중복 요청을 확인하고 검사 ID를 생성한다.
4. 원본 이미지를 Object Storage에 비공개로 저장한다.
5. DB에 검사 상태 `PROCESSING`을 기록한다.
6. Backend가 내부 `vision-service`에 이미지와 추론 옵션을 전달한다.
7. Vision이 모델 전처리·추론·후처리를 수행하고 원시 검출 결과를 반환한다.
8. Backend가 좌표 정규화, 클래스 매핑, 중복 제거, 순서·체결 규칙을 적용한다.
9. 결과 오버레이를 저장하고 검사, 검출 객체, 판정 근거, 설정 스냅샷을 트랜잭션으로 기록한다.
10. 정제된 검사 결과를 FrontEnd에 반환한다.
11. 실패 시 상태를 `FAILED`로 변경하고 내부 오류 원인은 로그/감사 데이터에만 남긴다.

DB 트랜잭션을 외부 추론 호출 동안 열어 두지 않는다. 상태 전이를 `RECEIVED -> PROCESSING -> COMPLETED/FAILED`로 관리한다.

## 6. Vision Service 연동 규약

### 6.1 내부 API

`POST /internal/v1/infer/segmentation`

- Content-Type: `multipart/form-data`
- 네트워크: 외부 비공개, Backend에서만 접근
- 인증: mTLS 또는 내부 서비스 토큰
- 타임아웃 권장: 연결 3초, 응답 30초
- 재시도: 연결 실패에 한해 최대 1회. 추론 요청에는 동일 `requestId` 사용

요청 파트:

| 파트 | 형식 | 필수 | 설명 |
|---|---|---:|---|
| `image` | binary | Y | 단일 이미지 |
| `request` | JSON string | Y | 모델과 추론 옵션 |

```json
{
  "requestId": "01J8V6H2Y7Q9M7X5K1E8P3A4BC",
  "modelVersion": "bolt-seg-2026.09.1",
  "confidenceThreshold": 0.65,
  "iouThreshold": 0.45,
  "returnMasks": true,
  "returnOverlay": true
}
```

응답:

```json
{
  "requestId": "01J8V6H2Y7Q9M7X5K1E8P3A4BC",
  "model": {
    "name": "bolt-nut-washer-seg",
    "version": "bolt-seg-2026.09.1"
  },
  "image": { "width": 1920, "height": 1080 },
  "latencyMs": { "preprocess": 18, "inference": 126, "postprocess": 21 },
  "detections": [
    {
      "classId": 0,
      "className": "bolt",
      "confidence": 0.9821,
      "bbox": { "x": 412.2, "y": 205.8, "width": 742.1, "height": 468.5 },
      "mask": {
        "encoding": "polygon",
        "points": [[412.2, 221.0], [1149.0, 210.4], [1138.7, 664.2]]
      }
    }
  ],
  "overlayImageBase64": null,
  "warnings": []
}
```

대용량 mask는 base64 이미지보다 polygon 또는 RLE를 권장한다. 운영 환경에서는 오버레이도 base64 대신 Object Storage로 저장할 수 있도록 Backend가 생성하거나 Vision이 임시 객체 키를 반환한다.

### 6.2 Backend 정제 규칙

- confidence 임계값 미만 검출 제거
- class alias를 도메인 표준 코드(`BOLT`, `NUT`, `WASHER`)로 매핑
- 겹치는 동일 클래스 검출을 IoU 기준으로 제거
- 이미지 좌표와 0~1 정규화 좌표를 모두 계산하되 외부 API는 정규화 좌표를 기본 사용
- mask 중심점 또는 주축 투영값으로 부품 순서를 계산
- 입력 시점의 모델 버전과 판정 설정을 결과에 스냅샷으로 저장
- Vision의 원시 출력은 디버깅 목적의 제한된 보존 정책을 적용하고 외부 응답에는 필요한 값만 노출

## 7. DB 구조와 저장 대상

### 7.1 관계 개요

```text
users 1---N inspections N---1 inspection_profiles
                     |
                     +---N inspection_detections
                     +---N judgement_reasons
                     +---N inspection_events

models 1---N inspections
system_settings / audit_logs
```

### 7.2 주요 테이블

#### `inspections`

| 컬럼 | 형식 | 설명 |
|---|---|---|
| `id` | UUID/ULID PK | 검사 ID |
| `inspection_no` | VARCHAR UNIQUE | 화면 표시용 번호 |
| `status` | VARCHAR | `RECEIVED/PROCESSING/COMPLETED/FAILED` |
| `judgement` | VARCHAR | `OK/NG/REVIEW/ERROR` |
| `defect_code` | VARCHAR NULL | 대표 불량 코드 |
| `product_code` | VARCHAR | 품목 코드 |
| `lot_no` | VARCHAR NULL | LOT 번호 |
| `line_code` | VARCHAR NULL | 라인 코드 |
| `equipment_code` | VARCHAR NULL | 설비 코드 |
| `operator_id` | FK NULL | 검사 작업자 |
| `profile_id` | FK | 검사 프로파일 |
| `model_version` | VARCHAR | 사용 모델 버전 |
| `original_object_key` | VARCHAR | 원본 이미지 객체 키 |
| `overlay_object_key` | VARCHAR NULL | 결과 이미지 객체 키 |
| `image_sha256` | CHAR(64) | 무결성·중복 확인 |
| `image_width/height` | INTEGER | 이미지 크기 |
| `sequence_judgement` | VARCHAR | 순서 판정 |
| `fastening_judgement` | VARCHAR | 체결 판정 |
| `fastening_score` | NUMERIC NULL | 영상 기반 체결 점수 |
| `torque_nm` | NUMERIC NULL | 센서 토크 값 |
| `confidence_summary` | NUMERIC NULL | 대표 신뢰도 |
| `processing_ms` | INTEGER NULL | 전체 처리 시간 |
| `settings_snapshot` | JSONB | 검사 당시 규칙/임계값 |
| `user_input` | JSONB | 확장 입력값 |
| `created_at/completed_at` | TIMESTAMPTZ | 시간 |

권장 인덱스: `(created_at DESC)`, `(judgement, created_at DESC)`, `(product_code, created_at DESC)`, `(lot_no)`, `(line_code, created_at DESC)`.

#### `inspection_detections`

`id`, `inspection_id`, `class_code`, `confidence`, `bbox_json`, `mask_json/object_key`, `centroid_x`, `centroid_y`, `axis_position`, `sequence_index`, `created_at`을 저장한다.

#### `judgement_reasons`

`inspection_id`, `code`, `severity`, `message_key`, `measured_value`, `expected_value`, `metadata`를 저장한다. 화면 문구보다 기계 판독 가능한 `code`를 기준으로 집계한다.

#### `inspection_profiles`

품목/라인별 `expected_sequence`, confidence·IoU 임계값, 체결 점수 또는 토크 범위, 조립축 방향, 활성 모델 버전, 버전 번호를 저장한다.

#### 기타

- `model_registry`: 모델명, 버전, 파일 digest, 클래스 목록, 배포 상태, 생성일
- `inspection_events`: 상태 전이와 처리 단계별 시간
- `audit_logs`: 설정 변경 주체, 대상, 변경 전/후, IP, 시간
- `users/roles`: 사용자와 역할
- `system_settings`: 파일 제한, 보존 기간 등 시스템 설정

이미지 binary를 DB에 직접 넣기보다 Object Storage에 보관하고 DB에는 객체 키와 메타데이터만 저장한다.

## 8. 외부 통신 공통 규약

- Base URL: `/api/v1`
- 전송: HTTPS/TLS 1.2 이상
- 일반 Content-Type: `application/json; charset=utf-8`
- 파일 업로드: `multipart/form-data`
- 시간: ISO 8601 UTC (`2026-09-22T03:15:20.123Z`)
- ID: UUID 또는 ULID 문자열
- 속성명: JSON `camelCase`, DB `snake_case`
- 금액/측정값: 단위를 필드명 또는 별도 `unit`으로 명시
- 페이지: `page`는 1부터 시작, `size` 기본 20, 최대 100
- 정렬: `sort=createdAt,desc`
- 추적: 응답 헤더 `X-Request-Id`
- 멱등성: 검사 생성 요청 헤더 `Idempotency-Key` 권장
- 버전: URL major version 사용, 호환 필드는 additive 방식으로 추가

성공 응답은 리소스를 직접 반환하고, 오류는 12장의 공통 오류 구조를 사용한다.

## 9. 이미지 업로드 및 검사 API

### 9.1 검사 생성

`POST /api/v1/inspections`

헤더:

```http
Authorization: Bearer <access-token>
Idempotency-Key: 66d513e6-8f83-48a8-8ee4-dcb50cdd48e2
Content-Type: multipart/form-data
```

폼 파트:

| 이름 | 형식 | 필수 | 제한/설명 |
|---|---|---:|---|
| `image` | File | Y | 이미지 1장 |
| `metadata` | JSON string | Y | 검사 입력 정보 |

```json
{
  "productCode": "BNW-M8-A",
  "lotNo": "LOT-20260922-01",
  "lineCode": "LINE-01",
  "equipmentCode": "CAM-01",
  "profileId": "01J8V5ZYJ8F8D9A8CP3X29AQJ7",
  "torqueNm": 18.4,
  "note": "초도 검사"
}
```

성공: `201 Created`

```json
{
  "id": "01J8V6H2Y7Q9M7X5K1E8P3A4BC",
  "inspectionNo": "INSP-20260922-000184",
  "status": "COMPLETED",
  "judgement": "NG",
  "defectCode": "NG_SEQUENCE",
  "sequenceJudgement": {
    "status": "NG",
    "expected": ["BOLT", "WASHER", "NUT"],
    "detected": ["BOLT", "NUT", "WASHER"],
    "score": 0.96
  },
  "fasteningJudgement": {
    "status": "OK",
    "method": "TORQUE_SENSOR",
    "measured": 18.4,
    "min": 17.0,
    "max": 20.0,
    "unit": "Nm"
  },
  "images": {
    "originalUrl": "/api/v1/inspections/01J8V6H2Y7Q9M7X5K1E8P3A4BC/training_images/original",
    "overlayUrl": "/api/v1/inspections/01J8V6H2Y7Q9M7X5K1E8P3A4BC/training_images/overlay",
    "width": 1920,
    "height": 1080
  },
  "detections": [
    {
      "id": "det-1",
      "classCode": "NUT",
      "confidence": 0.981,
      "bbox": { "x": 0.312, "y": 0.248, "width": 0.174, "height": 0.221 },
      "centroid": { "x": 0.399, "y": 0.359 },
      "sequenceIndex": 2,
      "mask": { "encoding": "polygon", "points": [[0.31, 0.25], [0.48, 0.27], [0.46, 0.46]] }
    }
  ],
  "reasons": [
    {
      "code": "PART_ORDER_MISMATCH",
      "severity": "ERROR",
      "message": "와셔와 너트의 조립 순서가 기준과 다릅니다."
    }
  ],
  "model": { "name": "bolt-nut-washer-seg", "version": "bolt-seg-2026.09.1" },
  "processingMs": 421,
  "createdAt": "2026-09-22T03:15:20.123Z",
  "completedAt": "2026-09-22T03:15:20.544Z"
}
```

### 9.2 이미지 조회

- `GET /api/v1/inspections/{inspectionId}/images/original`
- `GET /api/v1/inspections/{inspectionId}/images/overlay`

권한 확인 후 짧은 만료 시간의 서명 URL로 `302` 이동하거나 파일을 스트리밍한다. 객체 저장소 URL을 영구 공개하지 않는다.

### 9.3 비동기 확장안

추론이 장시간 걸리면 생성 API는 `202 Accepted`와 `status: PROCESSING`을 반환하고 `GET /inspections/{id}`를 폴링한다. 대규모 운영에서는 SSE/WebSocket 진행 이벤트를 별도 도입할 수 있으나, MVP 필수 규약은 아니다.

## 10. 검사이력 API

### 10.1 목록

`GET /api/v1/inspections?from=2026-09-01T00:00:00Z&to=2026-09-23T00:00:00Z&judgement=NG&defectCode=NG_SEQUENCE&productCode=BNW-M8-A&lotNo=LOT-20260922-01&lineCode=LINE-01&page=1&size=20&sort=createdAt,desc`

```json
{
  "items": [
    {
      "id": "01J8V6H2Y7Q9M7X5K1E8P3A4BC",
      "inspectionNo": "INSP-20260922-000184",
      "productCode": "BNW-M8-A",
      "lotNo": "LOT-20260922-01",
      "lineCode": "LINE-01",
      "judgement": "NG",
      "defectCode": "NG_SEQUENCE",
      "confidenceSummary": 0.96,
      "thumbnailUrl": "/api/v1/inspections/01J8V6H2Y7Q9M7X5K1E8P3A4BC/training_images/overlay?variant=thumbnail",
      "createdAt": "2026-09-22T03:15:20.123Z"
    }
  ],
  "page": 1,
  "size": 20,
  "totalElements": 184,
  "totalPages": 10
}
```

### 10.2 상세 및 작업자 재판정

- `GET /api/v1/inspections/{inspectionId}`: 생성 응답 수준의 상세 데이터 조회
- `PATCH /api/v1/inspections/{inspectionId}/review`: `REVIEW` 결과를 권한 있는 작업자가 확정

```json
{
  "judgement": "NG",
  "defectCode": "NG_FASTENING_LOW",
  "comment": "현장 확인 결과 체결 부족",
  "version": 3
}
```

`version`은 낙관적 잠금에 사용한다. 자동 판정 원본을 덮어쓰지 않고 재판정 이벤트와 최종 표시 판정을 분리해 감사 가능하게 유지한다.

## 11. 대시보드 API

### 11.1 요약 KPI

`GET /api/v1/dashboard/summary?from=2026-09-22T00:00:00Z&to=2026-09-23T00:00:00Z&lineCode=LINE-01&timezone=Asia/Seoul`

```json
{
  "period": {
    "from": "2026-09-22T00:00:00Z",
    "to": "2026-09-23T00:00:00Z",
    "timezone": "Asia/Seoul"
  },
  "kpi": {
    "total": 1248,
    "ok": 1192,
    "ng": 51,
    "review": 5,
    "defectRate": 0.0409,
    "averageProcessingMs": 438
  },
  "comparison": {
    "totalChangeRate": 0.082,
    "defectRateChangePoint": -0.006
  },
  "updatedAt": "2026-09-22T03:20:00Z"
}
```

### 11.2 추이 및 불량 분포

- `GET /api/v1/dashboard/trends?from=...&to=...&interval=hour&lineCode=LINE-01`
- `GET /api/v1/dashboard/defects?from=...&to=...&groupBy=defectCode&limit=10`

```json
{
  "interval": "hour",
  "series": [
    { "bucket": "2026-09-22T01:00:00Z", "total": 148, "ok": 141, "ng": 7, "review": 0 }
  ]
}
```

대시보드 집계는 `COMPLETED` 검사만 기본 포함한다. `ERROR/PROCESSING` 건수는 운영 지표로 별도 표시할 수 있다. 응답 캐시는 10~30초 수준을 권장한다.

## 12. 환경설정 API

### 12.1 검사 프로파일 조회/수정

- `GET /api/v1/settings/inspection-profiles`
- `GET /api/v1/settings/inspection-profiles/{profileId}`
- `POST /api/v1/settings/inspection-profiles`
- `PUT /api/v1/settings/inspection-profiles/{profileId}`

```json
{
  "name": "M8 기본 검사",
  "productCode": "BNW-M8-A",
  "expectedSequence": ["BOLT", "WASHER", "NUT"],
  "axisDirection": "TOP_TO_BOTTOM",
  "confidenceThreshold": 0.65,
  "iouThreshold": 0.45,
  "fastening": {
    "method": "TORQUE_SENSOR",
    "minTorqueNm": 17.0,
    "maxTorqueNm": 20.0,
    "reviewScoreThreshold": 0.7
  },
  "activeModelVersion": "bolt-seg-2026.09.1",
  "enabled": true,
  "version": 4
}
```

- 수정 권한: `ADMIN` 또는 `ENGINEER`
- 모든 수정은 감사 로그에 변경 전/후를 남긴다.
- 이미 완료된 검사는 당시 `settingsSnapshot`을 사용하므로 설정 변경의 영향을 받지 않는다.

### 12.2 모델 목록과 활성화

- `GET /api/v1/models`
- `POST /api/v1/models/{version}/activate`

모델 활성화는 즉시 운영 영향을 주므로 배포 상태, health check, 클래스 호환성 확인 후 실행한다. 모델 파일 자체 업로드 API는 일반 UI와 분리하고 관리자 전용 배포 절차를 권장한다.

## 13. 오류 규약

오류 응답은 RFC 7807 스타일의 `application/problem+json`을 사용한다.

```json
{
  "type": "https://api.example.com/problems/unsupported-image-format",
  "title": "지원하지 않는 이미지 형식",
  "status": 415,
  "code": "IMG_UNSUPPORTED_FORMAT",
  "detail": "JPEG, PNG 또는 WebP 이미지 1장만 업로드할 수 있습니다.",
  "instance": "/api/v1/inspections",
  "requestId": "req-8afaa2c19d8b",
  "errors": [
    { "field": "image", "reason": "UNSUPPORTED_MEDIA_TYPE" }
  ],
  "timestamp": "2026-09-22T03:15:20.180Z"
}
```

| HTTP | 코드 예시 | 의미 |
|---:|---|---|
| 400 | `VALIDATION_FAILED` | 필드/메타데이터 오류 |
| 401 | `AUTH_REQUIRED` | 인증 필요 또는 토큰 만료 |
| 403 | `ACCESS_DENIED` | 권한 부족 |
| 404 | `INSPECTION_NOT_FOUND` | 리소스 없음 |
| 409 | `DUPLICATE_REQUEST`, `VERSION_CONFLICT` | 멱등성 충돌/동시 수정 |
| 413 | `IMG_TOO_LARGE` | 용량 초과 |
| 415 | `IMG_UNSUPPORTED_FORMAT` | 미지원 이미지 |
| 422 | `IMG_INVALID_DIMENSION`, `PROFILE_INVALID` | 처리 불가능한 입력 |
| 429 | `RATE_LIMITED` | 요청 제한 초과 |
| 502 | `VISION_INVALID_RESPONSE` | Vision 응답 계약 오류 |
| 503 | `VISION_UNAVAILABLE` | Vision/GPU 서비스 불가 |
| 504 | `VISION_TIMEOUT` | 추론 시간 초과 |

클라이언트에는 stack trace, 파일 시스템 경로, DB 쿼리, 내부 호스트명 또는 모델 파일 경로를 반환하지 않는다.

## 14. 보안 및 파일 제한

### 14.1 인증·인가

- OIDC/OAuth 2.1 기반 짧은 수명의 access token 권장
- 역할 예: `VIEWER`, `OPERATOR`, `ENGINEER`, `ADMIN`
- 조회는 라인/사업장 범위 권한 적용
- 설정 변경, 모델 활성화, 재판정은 별도 권한과 감사 로그 필수
- 브라우저 쿠키 인증 사용 시 `HttpOnly`, `Secure`, `SameSite` 및 CSRF 보호 적용

### 14.2 이미지 업로드 제한

권장 기본값:

| 항목 | 제한 |
|---|---|
| 파일 수 | 정확히 1장 |
| 형식 | JPEG, PNG, WebP |
| 최대 크기 | 10 MiB |
| 최소 해상도 | 320×320 |
| 최대 해상도 | 8192×8192 및 최대 40MP |
| 파일명 | 화면 표시용으로만 사용, 저장 키로 사용 금지 |
| 검증 | 확장자 + MIME + magic bytes 동시 확인 |

- SVG, 실행 파일, 다중 프레임 GIF/TIFF, 손상 이미지 거부
- 디코딩 후 실제 픽셀 수를 검사하여 decompression bomb 방지
- EXIF/GPS 메타데이터 제거 권장
- 업로드 파일을 실행하거나 원본 파일명 경로로 저장하지 않음
- Object Storage는 private bucket 사용, 암호화 at rest 및 만료되는 서명 URL 적용
- 악성 파일 검사와 파일 digest 기록을 권장
- CORS는 허용된 FrontEnd origin만 명시
- 사용자별/장비별 rate limit 적용

### 14.3 데이터 보존

- 검사 메타데이터와 이미지 보존 기간을 분리 설정
- 원본/오버레이 삭제 후에도 집계에 필요한 판정 메타데이터는 정책에 따라 유지
- 삭제는 Object Storage와 DB 참조를 함께 처리하고 감사 이벤트 기록
- 로그에는 access token, 원본 이미지 binary, 민감한 메모를 남기지 않음

## 15. 권장 폴더 구조

```text
project-root/
├─ apps/
│  ├─ web/
│  │  └─ src/
│  │     ├─ app/                 # router, providers, query client
│  │     ├─ pages/
│  │     │  ├─ dashboard/
│  │     │  ├─ inspection/
│  │     │  ├─ history/
│  │     │  └─ settings/
│  │     ├─ features/
│  │     │  ├─ inspection-upload/
│  │     │  ├─ inspection-result/
│  │     │  ├─ dashboard-metrics/
│  │     │  └─ history-filter/
│  │     ├─ entities/inspection/
│  │     ├─ shared/
│  │     │  ├─ api/
│  │     │  ├─ ui/
│  │     │  ├─ lib/
│  │     │  └─ types/
│  │     └─ assets/
│  ├─ api/
│  │  └─ src/
│  │     ├─ modules/
│  │     │  ├─ inspections/
│  │     │  ├─ dashboard/
│  │     │  ├─ settings/
│  │     │  ├─ models/
│  │     │  └─ auth/
│  │     ├─ domain/
│  │     │  ├─ judgement/
│  │     │  └─ inspection/
│  │     ├─ infrastructure/
│  │     │  ├─ db/
│  │     │  ├─ storage/
│  │     │  └─ vision-client/
│  │     └─ common/
│  └─ vision-service/
│     ├─ app/
│     │  ├─ api/
│     │  ├─ inference/
│     │  ├─ preprocessing/
│     │  ├─ postprocessing/
│     │  ├─ schemas/
│     │  └─ observability/
│     ├─ models/                 # 운영 시 외부 모델 저장소 권장
│     └─ tests/
├─ packages/
│  ├─ api-contract/              # OpenAPI 생성 타입
│  ├─ ui-kit/
│  └─ eslint-config/
├─ infra/

│  ├─ kubernetes/
│  └─ migrations/
├─ docs/
│  ├─ architecture/
│  ├─ api/
│  └─ adr/
├─ openapi/
│  └─ openapi.yaml

```

FrontEnd와 Backend가 같은 저장소가 아니라면 `api-contract`는 OpenAPI 문서를 단일 진실 공급원으로 두고 CI에서 TypeScript 타입/클라이언트를 생성한다.

## 16. 운영·관측성·테스트 기준

### 16.1 로그와 지표

- 모든 요청에 `requestId`, 검사 요청에 `inspectionId`를 연계
- 지표: 요청 수, 성공/실패율, 추론 p50/p95/p99, GPU 대기시간, NG율, REVIEW율, 오류 코드별 수
- `/health/live`, `/health/ready` 분리
- Vision readiness는 모델 로드 및 간단한 warm-up 결과를 포함
- 모델 버전별 품질·처리시간을 비교할 수 있게 결과에 버전을 항상 기록

### 16.2 테스트

- 단위 테스트: 순서 계산, 임계값 경계, 최종 판정 조합
- 계약 테스트: Backend–Vision request/response schema
- 통합 테스트: 이미지 저장, DB 상태 전이, 실패 복구
- E2E: 정상, 순서 불량, 누락, 저신뢰도, 대용량/미지원 파일, Vision timeout
- 회귀 데이터셋: 승인된 골든 이미지와 기대 판정 유지
- 성능 테스트: 동시 검사 수, GPU 큐, 대시보드 집계 쿼리

## 17. 권장 구현 순서

1. 검사 도메인 코드와 OpenAPI 계약 확정
2. DB migration 및 Object Storage 연결
3. Vision 내부 API와 계약 테스트 구현
4. 이미지 업로드–추론–정제–저장 동기 흐름 구현
5. 이미지검사 UI와 결과 오버레이 구현
6. 검사이력/상세 조회 구현
7. 대시보드 집계와 캐시 구현
8. 환경설정·권한·감사 로그 구현
9. 장애·부하·회귀 테스트 후 비동기 처리 필요성 판단

## 18. 주요 설계 결정 요약

- FrontEnd는 Vision 서비스에 직접 접근하지 않고 반드시 Backend를 경유한다.
- 모델 원시 출력과 업무 판정을 분리한다. Vision은 검출, Backend는 규칙과 최종 판정을 책임진다.
- 완료된 검사에는 모델 및 설정 스냅샷을 저장하여 재현성과 감사 가능성을 보장한다.
- 이미지 binary는 Object Storage, 검색·집계 데이터는 PostgreSQL에 저장한다.
- 초기 버전은 단일 이미지 동기 REST로 단순하게 시작하고 처리시간/부하 근거가 생길 때 큐 기반 비동기로 확장한다.
- 실제 토크 센서가 없으면 “체결 강도”를 영상 대용 지표로 명시해 물리 측정값과 혼동하지 않는다.


