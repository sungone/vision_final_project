# 볼트·너트·와셔 Vision Inspection Backend

기존 Spring Boot + Python Vision Service 폴더 구조에 검사 파이프라인을 구현했습니다. React 화면 코드는 기존 저장소에 없으며, 화면에서 사용할 TypeScript API 클라이언트는 `frontend/src/api/inspections.ts`에 있습니다.

## 실행

Docker Desktop / Docker Compose 환경에서:

```sh
cp .env.example .env
# .env의 DB 비밀번호와 SETTINGS_API_KEY를 변경하세요.
# 학습한 segmentation 모델을 vision-service/models/best.pt 에 배치하세요.
docker compose up --build -d
```

- Backend: http://localhost:8080
- PostgreSQL: localhost:5432, database/user `vision`
- Vision은 Compose 내부망의 `vision:8001`에서만 접근합니다.
- Flyway가 Backend 시작 시 `backend/src/main/resources/db/migration`의 DB 스키마를 적용합니다.
- 모델이 없어도 조회 API는 사용할 수 있습니다. 업로드 검사는 `MODEL_NOT_AVAILABLE` 오류를 반환합니다. 모의 정상 결과로 대체하지 않습니다.
- DB와 이미지는 각각 `postgres-data`, `inspection-images` Docker volume에 보존합니다. `docker compose down -v`는 이 데이터를 삭제하므로 초기화할 때만 사용합니다.

```sh
curl -F "image=@sample.jpg" -F "productCode=P-001" http://localhost:8080/api/inspections
curl http://localhost:8080/api/dashboard/summary
curl 'http://localhost:8080/api/inspections?result=FAIL&page=0&size=20'
```

## 로컬 개발과 테스트

Java 17 이상, Maven 3.9, Python 3.11 이상, PostgreSQL 16을 사용합니다.

```sh
docker compose up -d postgres
cd vision-service
python -m venv .venv
# Windows: .venv\Scripts\activate / Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --host 127.0.0.1 --port 8001
```

별도 터미널에서:

```sh
cd backend
mvn spring-boot:run
# 전체 테스트: Docker 필요, 격리된 PostgreSQL 컨테이너를 생성하고 종료합니다.
mvn test
# Docker 없는 순수 Rule / 이미지 단위 테스트
mvn test -Dtest=InspectionRuleEngineTest,ImageValidatorTest,LocalImageStorageServiceTest,ProcessedImageRendererTest
mvn package -DskipTests
```

Vision 단위 테스트 실행 방법은 [Vision README](vision-service/api/README.md)를 확인하세요. 모델 없는 테스트는 HTTP·변환·오류 처리를 검증하며 실제 품질 정확도를 증명하지 않습니다.

## 구성

- `backend`: Controller → Service → Repository, 별도 `vision`, `rule`, `storage` 계층
- `vision-service`: Ultralytics segmentation 호출 및 원시 출력의 DTO 변환
- `frontend/src/api/inspections.ts`: 업로드/결과/이력/KPI/설정의 브라우저 클라이언트
- `backend/src/main/resources/db/migration`: PostgreSQL 스키마와 초기 Rule 설정
- [구현 아키텍처·API·판정 기준](docs/BACKEND_IMPLEMENTATION.md)

실제 배포 전에 승인된 촬영 조건·라벨 정의·정상/불량 이미지로 threshold를 보정해야 합니다. 현재 체결 지표는 **픽셀 간격과 정렬 오차**이며 물리적 토크나 mm 측정값이 아닙니다. 공장 외부 공개 시 TLS·사용자 인증/권한·rate limit을 갖춘 게이트웨이를 적용하세요. 기본 Compose는 호스트 loopback에만 포트를 노출합니다.

기존 `docs/MVP.md`, `docs/BOLT_VISION_ARCHITECTURE_API.md`는 초기 기획 자료입니다. 구현된 `/api` 계약과 확장 범위는 `docs/BACKEND_IMPLEMENTATION.md`를 따릅니다.
