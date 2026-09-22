# Vision Inspection MVP

## 사용자 흐름

이미지 선택 → 검사 요청 → Loading → 후처리 이미지와 두 판정 표시. API 오류와 이미지 로딩 오류는 별도로 표시한다.

## 필수 결과

- resultImageUrl: Spring Boot의 후처리 JPEG URL
- assemblySequenceResult: NORMAL 또는 DEFECT
- fasteningQualityResult: NORMAL 또는 DEFECT

세부 규약은 [API 명세](../API.md)를 따른다.

## 제외 범위

작업지시, MES, 생산 통계, 검사 이력, DB 필수 연동, 실시간 영상, WebSocket, Kafka, Redis, confidence/gap/angle/defectType 공개 필드.

## 데이터로 확정할 항목

- Bolt/Washer/Nut 마스크 라벨 정의와 가림 처리.
- 대상 한 세트의 촬영 방향, 검사 축, 조명 및 배치 조건.
- 구성 검사: 기대 개수, 위치 관계, 부품 누락 판정 기준.
- 체결 검사: 안착/들뜸 등 관측 특징과 허용 기준. 영상으로 실제 토크를 측정한다고 가정하지 않는다.
- 가림/흐림/검출 실패와 실제 누락을 구분하는 기준.
- 학습과 분리한 정상/불량 검증 이미지. 유사 연속 촬영 이미지의 분할 누출 방지.

위 기준은 아직 데이터로 확정되지 않았다. best.pt 및 검증된 판정 알고리즘이 실제 검사 완료의 전제다.

## 완료 조건

1. 실제 모델 및 규칙으로 이미지 한 장을 처리한다.
2. 세 필드가 같은 이름과 타입으로 React까지 전달된다.
3. 정상/불량 모두 JPEG 조회가 가능하고 불량 영역이 표시된다.
4. 잘못된 이미지, 판정 불가, 추론 실패를 NORMAL/DEFECT로 위장하지 않는다.
5. React가 요청 진행, 오류 및 결과를 표시한다.

통합 흐름과 판정 정확도는 각각 검증한다. 모의 응답은 실제 모델 평가를 대체하지 않는다.
