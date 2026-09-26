"""
세그멘테이션 결과(볼트/와셔/나사산 인스턴스)를 받아서
  1) 결합 순서·부품 과부족 판정
  2) 체결 상태(나사산 노출 길이) 판정
을 내리는 의사결정 로직.

전제 (사용자 확인 완료):
- 카메라는 프레임 정중앙 · 수직 고정 -> 축 방향 = 이미지 y축. 회전 보정 불필요.
- 정상 결합 구조 (축 방향으로): 볼트(머리) - 와셔 - 와셔 - 볼트(너트 역할) - 나사산
  * "볼트" 클래스는 실제 볼트 머리와 너트를 구분 못 함 (둘 다 육각형이라 라벨링 단계에서
    같은 클래스로 묶음). 나사산에 인접한 쪽이 너트, 반대쪽이 진짜 볼트 머리.
- 나사산 노출 길이는 "완전히·정상적으로 조여졌을 때 최대(=2cm)"이고,
  느슨할수록 짧아짐 (너트가 나사산을 타고 머리 쪽으로 이동할수록 반대편
  노출 구간이 길어지는 구조).
- 체결 상태 확인은 "결합 순서가 정상"인 경우에만 수행 (순서 불량이면 스킵).

이 파일은 순수 판정 로직만 담당합니다. YOLO 추론 결과(ultralytics Results
객체)에서 인스턴스를 뽑아오는 부분은 파일 맨 아래 extract_instances_from_result()
에 분리해뒀으니, live_segment.py 등에서 그 함수만 불러 쓰면 됩니다.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Literal, Tuple

# ----------------------------------------------------------------------
# 실측 상수 (수정은 여기서만)
# ----------------------------------------------------------------------
REF_HEAD_CM = 1.0     # 볼트(머리) 짧은 쪽 길이 (축 방향)
REF_NUT_CM = 1.0      # 너트 역할 하는 "볼트" 인스턴스도 같은 부품 -> 동일 값
REF_WASHER_CM = 0.3   # 와셔 짧은 쪽 길이 (축 방향)
FULL_THREAD_CM = 2.0  # 완전 체결 시 나사산 노출 길이 (스펙값, 고정)

# TODO: 파일럿 데이터(정상/체결불량 샘플)로 실측해서 채우기.
# 예: 정상 샘플들의 노출 길이가 평균 1.95cm, 체결불량 샘플이 1.4cm 이하로
#     나온다면 1.7 정도로 잡는 식. 지금은 임시로 0.9(=1.8cm)로 넣어둠.
TIGHTNESS_MIN_RATIO = 1.08  # FULL_THREAD_CM 대비 이 비율 미만이면 불량


# ----------------------------------------------------------------------
# 데이터 구조
# ----------------------------------------------------------------------
@dataclass
class Instance:
    cls: str          # "bolt" | "washer" | "thread"
    y_min: float       # 축(y) 방향 시작 좌표 (px, 원본 이미지 기준)
    y_max: float       # 축(y) 방향 끝 좌표 (px)
    conf: float = 1.0  # YOLO confidence (참고용, 판정에는 안 씀)

    @property
    def length_px(self) -> float:
        return self.y_max - self.y_min

    @property
    def center(self) -> float:
        return (self.y_min + self.y_max) / 2


@dataclass
class OrderResult:
    status: Literal["정상", "불량"]
    reasons: List[Tuple[str, str]] = field(default_factory=list)  # (짧은 태그, 상세 설명)
    head: Optional[Instance] = None
    nut: Optional[Instance] = None
    washers: List[Instance] = field(default_factory=list)
    thread: Optional[Instance] = None
    ignored_extras: List[Instance] = field(default_factory=list)  # 화면에 우연히 걸린 별개 물체


@dataclass
class TightnessResult:
    status: Literal["정상", "체결불량"]
    measured_thread_cm: float
    scale_cm_per_px: float
    threshold_cm: float


@dataclass
class DecisionResult:
    order: OrderResult
    tightness: Optional[TightnessResult]  # order.status != "정상" 이면 None (검사 스킵)


# ----------------------------------------------------------------------
# 1) 결합 순서 · 부품 과부족 판정
# ----------------------------------------------------------------------
def check_order(instances: List[Instance]) -> OrderResult:
    threads = [i for i in instances if i.cls == "thread"]
    bolts = [i for i in instances if i.cls == "bolt"]
    washers = [i for i in instances if i.cls == "washer"]

    reasons: List[Tuple[str, str]] = []
    nut: Optional[Instance] = None
    head: Optional[Instance] = None
    extra_bolts: List[Instance] = []
    thread: Optional[Instance] = None

    # 나사산은 정확히 1개여야 함. 세그멘테이션 검증 결과 검출 실패가 거의
    # 없었으므로, 0개/2개 이상도 "판독불가"로 따로 두지 않고 그냥 불량으로 합침.
    if len(threads) == 0:
        reasons.append(("no_thread", "나사산 인스턴스를 찾지 못함"))
    elif len(threads) > 1:
        reasons.append((f"dup_thread({len(threads)})", f"나사산 인스턴스가 {len(threads)}개 검출됨 (1개여야 함)"))
    else:
        thread = threads[0]

    # 카메라가 부품 하나에 고정·중앙 정렬된 라이브 환경이라, 화면에 우연히
    # 걸리는 무관한 배경 물체는 사실상 없다고 보고 위치(어느 방향에 있는지)는
    # 따지지 않는다. 볼트/와셔가 몇 개 검출됐는지, 그 개수만으로 판정한다.
    if len(bolts) == 0:
        reasons.append(("no_bolt", "볼트/너트 인스턴스 없음"))
    elif len(bolts) == 1:
        # 볼트가 1개뿐이면, 볼트 머리는 프레이밍상 항상 잡히므로 이건 무조건
        # 머리 쪽이고 너트가 아예 빠진 것으로 확정한다.
        head = bolts[0]
        reasons.append(("no_nut", "너트 없음"))
    else:
        if thread is not None:
            by_dist = sorted(bolts, key=lambda b: abs(b.center - thread.center))
            nut = by_dist[0]     # thread에 가장 가까운 볼트 = 너트
            head = by_dist[-1]   # 가장 먼 볼트 = 머리
            extra_bolts = by_dist[1:-1]
        else:
            # thread를 못 찾아서 거리 기준 역할(머리/너트) 배정은 못 하지만,
            # 개수 자체는 그대로 확인할 수 있음.
            extra_bolts = bolts[2:]
        if len(bolts) > 2:
            reasons.append((f"extra_bolt({len(bolts)})", f"볼트/너트 인스턴스 {len(bolts)}개 검출됨 (2개여야 함, 과다)"))

    n_washer = len(washers)
    if n_washer < 2:
        reasons.append((f"washer_low({n_washer})", f"와셔 {2 - n_washer}개 부족 (검출 {n_washer}개)"))
    elif n_washer > 2:
        reasons.append((f"washer_high({n_washer})", f"와셔 {n_washer - 2}개 과다 (검출 {n_washer}개)"))

    status = "정상" if not reasons else "불량"
    return OrderResult(
        status=status, reasons=reasons,
        head=head, nut=nut, washers=washers, thread=thread,
        ignored_extras=extra_bolts,
    )


# ----------------------------------------------------------------------
# 2) 체결 상태(나사산 노출 길이) 판정 - 순서가 "정상"일 때만 호출
# ----------------------------------------------------------------------
def check_tightness(order: OrderResult) -> TightnessResult:
    assert order.status == "정상", "순서가 정상일 때만 체결 상태를 판정합니다."
    assert order.head is not None and order.nut is not None and order.thread is not None

    # 스케일: 머리·너트 둘 다 실제 길이가 같은 부품(1.0cm)이므로 평균 내서 노이즈를 줄임
    ref_px = (order.head.length_px + order.nut.length_px) / 2
    scale_cm_per_px = REF_HEAD_CM / ref_px

    measured_cm = order.thread.length_px * scale_cm_per_px
    threshold_cm = FULL_THREAD_CM * TIGHTNESS_MIN_RATIO

    status = "정상" if measured_cm >= threshold_cm else "체결불량"
    return TightnessResult(
        status=status, measured_thread_cm=measured_cm,
        scale_cm_per_px=scale_cm_per_px, threshold_cm=threshold_cm,
    )


# ----------------------------------------------------------------------
# 전체 파이프라인: 순서 불량이면 체결 상태는 스킵
# ----------------------------------------------------------------------
def decide(instances: List[Instance]) -> DecisionResult:
    order = check_order(instances)
    tightness = check_tightness(order) if order.status == "정상" else None
    return DecisionResult(order=order, tightness=tightness)


def format_result(result: DecisionResult) -> str:
    """상세 버전. txt 요약 파일 등 기록용으로 씀."""
    lines = [f"[순서] {result.order.status}"]
    if result.order.reasons:
        for _, msg in result.order.reasons:
            lines.append(f"  - {msg}")
    if result.order.ignored_extras:
        lines.append(f"  (참고: 별개 물체로 추정되어 무시한 인스턴스 {len(result.order.ignored_extras)}개)")

    if result.order.status != "정상":
        lines.append("[체결 상태] 순서 불량으로 검사 생략")
    else:
        t = result.tightness
        lines.append(f"[체결 상태] {t.status}  "
                     f"(측정 {t.measured_thread_cm:.2f}cm / 기준 {FULL_THREAD_CM:.1f}cm, "
                     f"임계값 {t.threshold_cm:.2f}cm)")
    return "\n".join(lines)


def format_result_short(result: DecisionResult) -> str:
    """실시간 화면 오버레이용 한 줄 요약. cv2.putText가 한글을 못 그리므로
    영어로만 구성한다 (상세 한글 사유는 format_result()의 txt 기록에만 남김)."""
    if result.order.status != "정상":
        tags = ",".join(code for code, _ in result.order.reasons)
        return f"FAIL [{tags}]"

    t = result.tightness
    if t.status == "정상":
        return f"OK ({t.measured_thread_cm:.1f}cm)"
    return f"LOOSE ({t.measured_thread_cm:.1f}cm)"


# ----------------------------------------------------------------------
# ultralytics Results 객체 -> Instance 리스트 변환
# (live_segment.py 등에서 model.predict() 결과를 여기에 그대로 넣으면 됨)
# ----------------------------------------------------------------------
def extract_instances_from_result(result, class_names: dict) -> List[Instance]:
    """
    result   : ultralytics Results 객체 (model.predict(...)[0] 또는 스트림의 각 원소)
    class_names : {0: "bolt", 1: "washer", 2: "thread"} 처럼 클래스 인덱스 -> 이름 매핑
                  (model.names 를 그대로 넘기면 됨)
    """
    instances: List[Instance] = []
    if result.masks is None:
        return instances  # 이 프레임에서 아무것도 검출 안 됨

    for poly, cls_idx, conf in zip(result.masks.xy, result.boxes.cls, result.boxes.conf):
        cls_name = class_names[int(cls_idx)]
        ys = poly[:, 1]  # 마스크 폴리곤의 y좌표들 (원본 이미지 픽셀 기준)
        instances.append(Instance(
            cls=cls_name,
            y_min=float(ys.min()),
            y_max=float(ys.max()),
            conf=float(conf),
        ))
    return instances


# ----------------------------------------------------------------------
# 데모 (실제 좌표 없이 로직만 확인용)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # 정상 케이스 예시: 머리(위) - 와셔 - 와셔 - 너트 - 나사산(아래), y가 클수록 아래쪽
    demo_normal = [
        Instance(cls="bolt", y_min=0, y_max=90),      # 머리, 길이 90px
        Instance(cls="washer", y_min=90, y_max=115),
        Instance(cls="washer", y_min=115, y_max=140),
        Instance(cls="bolt", y_min=140, y_max=230),   # 너트, 길이 90px (머리와 동일 스케일)
        Instance(cls="thread", y_min=230, y_max=410),  # 나사산, 길이 180px -> 2.0cm 근처가 되도록
    ]
    print("=== 정상 케이스 ===")
    print(format_result(decide(demo_normal)))

    print("\n=== 와셔 1개 부족 ===")
    demo_missing_washer = [i for i in demo_normal if not (i.cls == "washer" and i.y_min == 115)]
    print(format_result(decide(demo_missing_washer)))

    print("\n=== 너트 없음 ===")
    demo_no_nut = [i for i in demo_normal if not (i.cls == "bolt" and i.y_min == 140)]
    print(format_result(decide(demo_no_nut)))

    print("\n=== 체결불량 (나사산 노출 짧음) ===")
    demo_loose = [i for i in demo_normal if i.cls != "thread"]
    demo_loose.append(Instance(cls="thread", y_min=230, y_max=310))  # 180px -> 80px로 축소
    print(format_result(decide(demo_loose)))