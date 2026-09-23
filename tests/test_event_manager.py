from backend.app.inspection.event_manager import InspectionEventManager
from backend.app.vision.contracts import InspectionResult


def result(overall: str) -> InspectionResult:
    component_result = "DEFECT" if overall == "DEFECT" else "NORMAL"
    return InspectionResult(
        overall_result=overall,
        missing_component_result=component_result,
        alignment_result="NORMAL",
        fastening_result="NORMAL",
        metrics={},
    )


def test_defect_is_emitted_once_after_consecutive_confirmation():
    manager = InspectionEventManager(confirm_frames=3, recovery_frames=2)

    assert manager.process(result("DEFECT")) is None
    assert manager.process(result("DEFECT")) is None
    event = manager.process(result("DEFECT"))
    assert event is not None
    assert event.overall_result == "DEFECT"

    for _ in range(20):
        assert manager.process(result("DEFECT")) is None


def test_normal_recovery_arms_manager_for_the_next_product():
    manager = InspectionEventManager(confirm_frames=2, recovery_frames=2)

    assert manager.process(result("DEFECT")) is None
    assert manager.process(result("DEFECT")) is not None

    assert manager.process(result("NORMAL")) is None
    assert manager.process(result("NORMAL")) is None

    assert manager.process(result("DEFECT")) is None
    assert manager.process(result("DEFECT")) is not None


def test_unstable_candidate_does_not_create_an_event():
    manager = InspectionEventManager(confirm_frames=3, recovery_frames=2)

    assert manager.process(result("DEFECT")) is None
    assert manager.process(result("DEFECT")) is None
    assert manager.process(result("NORMAL")) is None
    assert manager.process(result("DEFECT")) is None
    assert manager.process(result("NORMAL")) is None
