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
- backend: 요청 검증, Vision 호출(client), 결과/이미지 저장, 이력 조회. 판정 알고리즘은 Python 영역에 둔다.
- vision-service/inference: best.pt 기반 Segmentation 추론과 마스크 추출.
- vision-service/inspection: 구성/순서 검사와 체결 품질 검사를 분리.
- vision-service/postprocessing: 불량 영역, 측정선, 결과를 이미지에 표시.
- vision-service/training: 기존 dataset을 이용한 학습/평가. datasets 폴더를 중복 생성하지 않는다.
- storage: 런타임 원본/후처리 이미지. 내부 .gitignore로 이미지 업로드를 제외한다.
- docs/API.md: 공개 API의 기준 명세. docs/api는 향후 예제 및 보조 문서용.

기존 README.md, dataset, 루트 .gitignore는 변경하지 않았다. 빈 디렉터리는 로컬에만 존재하며 Git은 빈 폴더 자체를 추적하지 않는다. package.json, build.gradle, settings.gradle, requirements.txt는 구현 시작 시 생성한다.
