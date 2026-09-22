# Vision Inspection MVP API

구현 예정 계약이며 실행 코드는 아직 없다.

## 책임

- React: 이미지 선택/업로드, Loading/Error, 결과 이미지와 두 판정 표시.
- Spring Boot: 입력 검증, Vision 호출, 응답 검증, 이미지 URL 생성/조회, 예외 처리.
- Python: Segmentation, 두 판정, OpenCV 후처리, 결과 JPEG 생성.

DB, MES, 이력, 작업지시, 통계는 후속 범위다. 현재는 검사 POST와 이미지 GET만 제공한다.

## 공개 검사 API

POST `/api/v1/inspections`

동기 multipart/form-data 요청. 필수 필드는 image 파일 한 장(JPG/JPEG/PNG)이다. 브라우저 FormData가 boundary를 생성하므로 Content-Type을 수동 고정하지 않는다.

빈 파일, 여러 image 파트, 미지원 형식, 디코딩 불가 파일을 거부한다. 확장자/MIME 선언만으로 검증하지 않는다.

초기 설계 기본 제한: 파일 10 MiB, 전체 요청 11 MiB, 이미지 25,000,000 pixels. 두 서비스에 같은 이미지 제한을 적용하고 실제 데이터로 조정한다.

HTTP 200, application/json:

```json
{
  "resultImageUrl": "/api/v1/inspections/550e8400-e29b-41d4-a716-446655440000/image",
  "assemblySequenceResult": "NORMAL",
  "fasteningQualityResult": "DEFECT"
}
```

세 필드는 필수이며 null을 허용하지 않는다. 두 판정과 JPEG 저장 완료 후 성공을 반환한다. JSON에 Base64를 넣지 않는다. 재요청은 별도 검사이므로 POST 자동 재시도를 하지 않는다.

## 타입 계약

- Java InspectionResult Enum: NORMAL, DEFECT.
- Python: 동일한 문자열 Enum 및 응답 스키마.
- TypeScript: NORMAL 또는 DEFECT 문자열 리터럴 유니온.
- InspectionResponse: resultImageUrl(String), assemblySequenceResult(InspectionResult), fasteningQualityResult(InspectionResult).
- 요청 image는 MultipartFile로 바인딩한다. 별도 업로드 DTO는 필수가 아니다.

## 결과 이미지

GET `/api/v1/inspections/{inspectionId}/image`

inspectionId는 서버 생성 UUID v4이며 DB Long ID가 아니다. 성공은 200 image/jpeg와 JPEG 바이너리다. 잘못된 ID는 400, 없는 파일은 404다. 정상도 JPEG를 생성하고 불량은 문제 영역을 표시한다.

resultImageUrl은 Spring Boot 기준 상대 URL이다. React는 /api 프록시 또는 API origin과 결합한다. 내부 주소나 파일 경로는 노출하지 않는다. 이미지 로드 오류도 UI에 표시한다.

## 내부 Vision API

MVP 전제: 같은 PC의 별도 프로세스가 결과 폴더를 공유한다. 컨테이너는 공유 볼륨을 연결한다. 공유 파일시스템 없는 배포는 후속 계약이 필요하다.

POST `/internal/v1/inspections`

Python이 제공하고 Spring Boot만 호출한다. multipart/form-data로 image 한 장을 받으며 Python도 검증한다.

HTTP 200, application/json:

```json
{
  "resultImageId": "550e8400-e29b-41d4-a716-446655440000",
  "assemblySequenceResult": "NORMAL",
  "fasteningQualityResult": "DEFECT"
}
```

Java VisionInspectionResponse: resultImageId(UUID), assemblySequenceResult(InspectionResult), fasteningQualityResult(InspectionResult). Python도 동일 필드와 enum을 사용한다.

1. Python은 추론/판정 후 UUID v4를 생성한다.
2. 공유 폴더의 임시 파일에 JPEG를 쓰고 완료 후 `<UUID>.jpg`로 원자적 교체한다.
3. 내부 응답을 반환한다.
4. Spring Boot는 필드, UUID v4, enum, JPEG 존재/읽기 가능 여부를 확인한다.
5. ID를 공개 URL로 변환한다. 품질을 재판정하지 않는다.

내부 필드 누락/null/잘못된 enum 또는 누락/손상 JPEG는 502 VISION_INVALID_RESPONSE다. 알 수 없는 값을 정상/불량으로 변환하지 않는다. 파일 경로를 클라이언트에서 받지 않는다.

## 설정과 보관

- Python URL 기본값: http://127.0.0.1:8000. Spring 설정으로 주입한다.
- RESULT_IMAGE_DIR: 두 서비스에 같은 절대 경로. 권장값 C:/project/vision_final_project/storage/results.
- 초기 연결 제한 3초, 내부 응답 60초, 프론트 대기 75초. 실측 후 조정한다.
- 원본 영구 보관은 필수가 아니다. 임시 입력은 성공/실패 후 정리한다.
- 결과는 자동 만료 없이 수동 정리 전까지 보관한다. 삭제 후 URL은 404다.
- 타임아웃은 Python 작업 취소를 보장하지 않는다. 늦게 생성된 미참조 이미지도 정리 대상이다.

## 판정 의미

assemblySequenceResult는 완성 이미지의 볼트 → 와셔 → 너트 구성과 공간적 순서다. 조립 작업의 시간 순서를 복원하지 않는다.

fasteningQualityResult는 관측 가능한 안착/기울어짐/간격 기준의 판정이다. Segmentation 외에 검증된 규칙이 필요하며 실제 토크 측정이 아니다.

가림/흐림 등으로 하나라도 판정 불가하면 422다. 명확한 누락은 구성 DEFECT일 수 있으나 다른 판정을 완료할 수 없으면 성공 응답을 만들지 않는다. 모델 준비 전 정상값을 임의 생성하지 않는다.

## 오류 계약

공개/내부 API 모두 application/json:

```json
{
  "code": "VISION_INFERENCE_FAILED",
  "message": "이미지 검사 중 오류가 발생했습니다."
}
```

| HTTP | code | 조건 |
| --- | --- | --- |
| 400 | EMPTY_IMAGE | 누락/빈 파일 |
| 400 | INVALID_IMAGE | 여러 이미지/미지원/손상 |
| 400 | INVALID_PARAMETER | UUID 형식 오류 |
| 404 | RESULT_IMAGE_NOT_FOUND | 공개 이미지 없음 |
| 413 | IMAGE_TOO_LARGE | 바이트/픽셀 초과 |
| 415 | UNSUPPORTED_MEDIA_TYPE | multipart 아닌 요청 |
| 422 | INSPECTION_UNDETERMINABLE | 판정 불가 |
| 500 | VISION_INFERENCE_FAILED | 추론 실패 |
| 500 | IMAGE_PROCESSING_FAILED | 후처리 실패 |
| 500 | RESULT_IMAGE_SAVE_FAILED | JPEG 저장 실패 |
| 500 | INTERNAL_ERROR | 그 외 내부 오류 |
| 502 | VISION_INVALID_RESPONSE | 내부 응답/파일 오류 |
| 503 | VISION_UNAVAILABLE | 연결 불가/모델 준비 안 됨 |
| 504 | VISION_TIMEOUT | 내부 시간 초과 |

Python의 문서화된 400/413/415/422/500/503 오류를 같은 상태/코드로 매핑한다. 다른 내부 오류 형식/상태는 502다. 프레임워크 오류도 공통 형식으로 정규화한다. 경로, 주소, 스택은 공개하지 않는다.

## 검증

세 필드 및 JPEG 조회, 두 판정의 네 조합, 입력 오류, 연결/추론/타임아웃/잘못된 enum을 검증한다. React의 중복 제출 방지와 오류 표시도 확인한다. 실제 정답 이미지로 판정 정확도를 별도 검증한다.

이력/상세 API, DB, MES, confidence/gap/angle/defectType, 실시간 카메라는 후속 범위다. Kafka, Redis, WebSocket은 추가하지 않는다.
