from __future__ import annotations

import cv2


def check_cameras(max_index: int = 9) -> None:
    found = []

    print("OpenCV에서 사용할 수 있는 카메라를 확인합니다.")
    print("다른 카메라 앱과 백엔드 서버를 먼저 종료하세요.\n")

    for index in range(max_index + 1):
        capture = cv2.VideoCapture(index)
        try:
            if not capture.isOpened():
                continue

            ok, frame = capture.read()
            if not ok or frame is None:
                continue

            height, width = frame.shape[:2]
            try:
                backend = capture.getBackendName()
            except cv2.error:
                backend = "unknown"

            found.append(index)
            print(
                f"인덱스 [{index}]: 사용 가능 "
                f"({width}x{height}, backend={backend})"
            )
        finally:
            capture.release()

    if not found:
        print("사용 가능한 카메라를 찾지 못했습니다.")
        print("Windows 카메라 권한과 다른 앱의 카메라 사용 여부를 확인하세요.")
        return

    print("\nbackend/.env.local의 CAMERA_INDEX에 사용할 번호:")
    print(", ".join(str(index) for index in found))


if __name__ == "__main__":
    check_cameras()
