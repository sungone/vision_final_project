# 볼트·너트·와셔 Vision Inspection MVP

React + Spring Boot + Python Vision Service 기반 단일 이미지 검사 프로젝트입니다.

현재는 폴더 및 API 설계 단계입니다. 실행 코드, 빌드 설정, 학습 모델은 아직 없으므로 실행 명령은 구현 후 추가합니다.

## 흐름

React 이미지 업로드 → Spring Boot 검증 → Python Segmentation·두 판정·OpenCV 후처리 → Spring Boot 응답 → React 표시

반환값은 resultImageUrl, assemblySequenceResult, fasteningQualityResult 세 필드입니다. 두 판정은 NORMAL/DEFECT이며 실제 오류와 구분합니다.

## 기준 문서

- [API 명세](docs/API.md): 공개/내부 API, 오류, 저장 정책
- [폴더 구조](docs/STRUCTURE.md): 영역별 책임
- [MVP 요구사항](docs/requirements/MVP.md): 범위, 미확정 판정 기준, 완료 조건

## 구현 준비

React/Vite/TypeScript, Java/Spring Boot, Python/OpenCV/YOLO Segmentation을 사용할 예정입니다. 각 영역의 의존성과 실행 진입점은 후속 구현 대상입니다.

같은 PC의 별도 프로세스와 공유 결과 폴더를 전제로 설계합니다. Python은 JPEG를 생성하고 Spring Boot는 URL로 제공합니다. RESULT_IMAGE_DIR은 두 서비스에서 같은 절대 경로여야 합니다.

- 학습 입력: dataset/images 및 dataset/labels
- 학습 모델 배치 예정: vision-service/models/best.pt
- 결과 JPEG: storage/results
- 향후 원본 보관: storage/originals

모델뿐 아니라 클래스 정의와 검증된 판정 규칙이 필요합니다. 모델 준비 전에 실제 검사 성공 결과를 임의로 생성하지 않습니다.

DB, 이력, MES, 통계, 실시간 카메라는 후속 확장 범위입니다.
