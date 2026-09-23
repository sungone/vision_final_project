from app.inspection import InspectionEventManager, InspectionState
from app.vision import DEFECT, NORMAL, InspectionResult


def result(value):
    return InspectionResult(overall_result=value)


def test_emits_once_until_normal_recovery():
    manager = InspectionEventManager(confirm_frames=3, reset_frames=2)
    assert manager.consume(result(DEFECT)) is None
    assert manager.consume(result(DEFECT)) is None
    assert manager.consume(result(DEFECT)) is not None
    assert manager.state == InspectionState.CONFIRMED_DEFECT
    assert manager.consume(result(DEFECT)) is None
    assert manager.consume(result(NORMAL)) is None
    assert manager.consume(result(NORMAL)) is None
    assert manager.state == InspectionState.NORMAL
    assert manager.consume(result(DEFECT)) is None
    assert manager.consume(result(DEFECT)) is None
    assert manager.consume(result(DEFECT)) is not None

