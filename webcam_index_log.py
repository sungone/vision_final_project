from pygrabber.dshow_graph import FilterGraph


def check_cameras():
    graph = FilterGraph()
    device_list = graph.get_input_devices()

    if not device_list:
        print("연결된 웹캠을 찾을 수 없습니다.")
        return

    print("--- 연결된 웹캠 및 인덱스 목록 ---")
    for index, name in enumerate(device_list):
        print(f"인덱스 [{index}]: {name}")


if __name__ == "__main__":
    check_cameras()