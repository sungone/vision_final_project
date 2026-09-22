# DB 스키마

실행 가능한 단일 기준은 `backend/src/main/resources/db/migration/V1__inspection.sql`입니다. Spring Boot 시작 시 Flyway가 PostgreSQL에 적용합니다. 이 폴더에 별도의 CREATE TABLE 사본을 두지 않아 마이그레이션 간 불일치를 방지합니다.

inspection(검사/판정 스냅샷) → inspection_detection(검출/벡터 polygon), inspection_rule_settings(현재 설정)로 구성됩니다. 상세 설명은 `docs/BACKEND_IMPLEMENTATION.md`를 참고하세요.
