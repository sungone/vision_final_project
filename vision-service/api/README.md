# Vision 내부 HTTP API

구현 예정 영역이다. POST /internal/v1/inspections가 image 한 장을 받아 inference → inspection → postprocessing을 호출한다.

스키마와 오류는 [API 명세](../../docs/API.md)를 따른다. 결과 JPEG를 RESULT_IMAGE_DIR에 저장하고 resultImageId 및 두 판정을 반환한다. 프론트는 이 API를 직접 호출하지 않는다.
