import threading

from app.inspection import InspectionPersistenceWorker
from app.vision import DEFECT, InspectionResult


def test_persistence_worker_retries_failed_event_without_blocking_submitter():
    persisted = threading.Event()
    attempts = []

    def persist(result):
        attempts.append(result)
        if len(attempts) == 1:
            raise RuntimeError("database temporarily unavailable")
        persisted.set()

    worker = InspectionPersistenceWorker(persist, queue_size=2, retry_seconds=0.01)
    worker.start()
    try:
        worker.submit(InspectionResult(overall_result=DEFECT))
        assert persisted.wait(2.0)
        assert len(attempts) == 2
        assert worker.persisted_count == 1
        assert worker.last_error is None
    finally:
        worker.stop()
