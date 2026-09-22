# 작업 폴더 안내

현재 단계는 디렉터리 구성 및 API 명세 작성이며, 실행 코드와 빌드/의존성 설정은 포함하지 않는다.

```text
vision_final_project/
├─ frontend/src/
│  ├─ assets/
│  ├─ components/
│  ├─ layouts/
│  ├─ pages/
│  ├─ services/
│  ├─ types/
│  └─ styles/
├─ backend/src/
│  ├─ main/java/com/vision/inspection/
│  │  ├─ controller/
│  │  ├─ service/
│  │  ├─ dto/
│  │  ├─ entity/
│  │  ├─ repository/
│  │  ├─ config/
│  │  ├─ client/
│  │  └─ exception/
│  ├─ main/resources/
│  └─ test/java/com/vision/inspection/
├─ vision-service/
│  ├─ api/                       # 내부 HTTP API 및 입출력 스키마
│  ├─ models/
│  ├─ inference/
│  ├─ inspection/
│  │  ├─ assembly_sequence/
│  │  └─ fastening_quality/
│  ├─ postprocessing/
│  ├─ training/
│  ├─ configs/
│  └─ tests/
├─ dataset/                       # 기존 촬영/학습 자료 유지
├─ storage/
│  ├─ originals/
│  └─ results/
├─ database/
│  ├─ schema/
│  └─ sample-data/
├─ design/
│  ├─ wireframes/
│  ├─ mockups/
│  └─ design-system/
├─ docs/
│  ├─ API.md
│  ├─ STRUCTURE.md
│  ├─ api/
│  ├─ requirements/
│  └─ database/
└─ infra/
```

- frontend: React/Vite/TypeScript 화면과 Spring Boot API 클라이언트.
- backend: 요청 검증, Vision 호출(client), 응답 검증, 결과 URL 생성, 이미지 조회. 판정은 Python이 담당한다.
- entity/repository 및 database: 향후 DB 연동용 예약 영역이며 MVP 필수 기능이 아니다.
- vision-service/api: POST /internal/v1/inspections와 Java DTO에 대응하는 응답 스키마.
- vision-service/inference: best.pt 기반 Segmentation 추론과 마스크 추출.
- vision-service/inspection: 구성/순서 검사와 체결 품질 검사를 분리.
- vision-service/postprocessing: 불량 영역, 측정선, 결과를 이미지에 표시.
- vision-service/training: 기존 dataset을 이용한 학습/평가. datasets 폴더를 중복 생성하지 않는다.
- storage/results: Python이 생성하고 Spring Boot가 읽는 공유 JPEG. 두 서비스의 RESULT_IMAGE_DIR을 동일하게 지정한다.
- storage/originals: 향후 원본 보관용. MVP는 원본 영구 보관을 요구하지 않는다.
- storage 내부 .gitignore로 런타임 이미지의 Git 업로드를 제외한다.
- docs/API.md: 공개 API의 기준 명세. docs/api는 향후 예제 및 보조 문서용.

기존 dataset과 루트 .gitignore를 유지한다. 빈 디렉터리는 Git에서 추적되지 않는다. package.json, build.gradle, settings.gradle, requirements.txt는 구현 시작 시 생성한다.

MVP 응답은 resultImageUrl, assemblySequenceResult, fasteningQualityResult 세 필드이다. docs/API.md가 공개/내부 계약의 기준이며 docs/requirements/MVP.md에서 현재 범위와 판정 기준을 관리한다.
