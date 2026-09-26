from datetime import datetime, timezone

import numpy as np
import pytest

from app import create_app
from app.inspection import InspectionEventManager, InspectionService
from app.repositories import InspectionRepository
from app.vision import DEFECT, NORMAL, InspectionResult


def test_empty_latest_and_history(client):
    assert client.get("/api/v1/inspection/latest").status_code == 204
    response = client.get("/api/v1/inspections?page=0&size=20")
    assert response.status_code == 200
    assert response.get_json()["content"] == []


def test_persist_and_read_inspection(app, client):
    with app.app_context():
        InspectionService(InspectionRepository(), app.config["DEFECT_STORAGE_DIR"]).persist_event(
            InspectionResult(
                overall_result=DEFECT,
                missing_component_result=NORMAL,
                alignment_result=NORMAL,
                fastening_result=DEFECT,
                metrics={
                    "detectedInstanceCount": 3,
                    "inferenceTimeMs": 82.4,
                    "modelType": "u-net-resnet18",
                    "detections": [
                        {
                            "classId": 2,
                            "className": "washer",
                            "confidence": 0.96,
                            "bbox": [10, 20, 30, 40],
                            "center": [20.0, 30.0],
                            "areaPx": 320,
                        }
                    ],
                },
                processed_frame=np.zeros((24, 32, 3), dtype=np.uint8),
                inspection_time=datetime.now(timezone.utc),
            )
        )
    latest = client.get("/api/v1/inspection/latest")
    assert latest.status_code == 200
    assert latest.get_json()["fasteningResult"] == DEFECT
    assert latest.get_json()["assemblySequenceResult"] == NORMAL
    assert latest.get_json()["fasteningQualityResult"] == DEFECT
    assert latest.get_json()["detectedInstanceCount"] == 3
    assert latest.get_json()["inferenceTimeMs"] == 82.4
    assert latest.get_json()["modelName"] == "u-net-resnet18"
    image_response = client.get(latest.get_json()["defectImageUrl"])
    assert image_response.status_code == 200
    assert image_response.content_type == "image/jpeg"
    assert client.get("/api/v1/inspections?page=-1").status_code == 400


def test_persist_event_is_idempotent_for_same_event_key(app, client):
    result = InspectionResult(
        overall_result=DEFECT,
        missing_component_result=DEFECT,
        alignment_result=NORMAL,
        fastening_result=NORMAL,
        event_key="evt-fixed-retry-key",
    )
    with app.app_context():
        service = InspectionService(InspectionRepository(), app.config["DEFECT_STORAGE_DIR"])
        first = service.persist_event(result)
        second = service.persist_event(result)
        assert first.id == second.id

    history = client.get("/api/v1/inspections?page=0&size=20").get_json()
    assert history["totalElements"] == 1


def test_signature_filter_persists_only_distinct_defects(app, client):
    ticks = iter((0.0, 1.0, 2.0, 3.0))
    manager = InspectionEventManager(
        reset_frames=2,
        sample_fps=1.0,
        geometry_tolerance_ratio=0.05,
        clock=lambda: next(ticks),
    )
    defect_a = InspectionResult(
        overall_result=DEFECT,
        missing_component_result=DEFECT,
        alignment_result=NORMAL,
        fastening_result=NORMAL,
        metrics={
            "detectedCounts": {"bolt": 2, "washer": 1, "thread": 1},
            "assemblyReasons": ["washer_count_1"],
            "detections": [],
        },
    )
    defect_b = InspectionResult(
        overall_result=DEFECT,
        missing_component_result=DEFECT,
        alignment_result=NORMAL,
        fastening_result=NORMAL,
        metrics={
            "detectedCounts": {"bolt": 2, "washer": 0, "thread": 1},
            "assemblyReasons": ["washer_count_0"],
            "detections": [],
        },
    )

    with app.app_context():
        service = InspectionService(InspectionRepository(), app.config["DEFECT_STORAGE_DIR"])
        for result in (defect_a, defect_a, defect_b, defect_b):
            event = manager.consume(result)
            if event is not None:
                service.persist_event(event)

    history = client.get("/api/v1/inspections?page=0&size=20").get_json()
    assert history["totalElements"] == 2


def test_status_endpoint(client):
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    assert response.get_json()["databaseConnected"] is True


def test_health_endpoint_does_not_require_database_query(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.get_json()["service"] == "vision-backend"


def test_cors_allows_only_configured_frontend_origin(client):
    allowed = client.get("/api/v1/health", headers={"Origin": "http://localhost:5173"})
    blocked = client.get("/api/v1/health", headers={"Origin": "https://unknown.example"})
    assert allowed.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert "Access-Control-Allow-Origin" not in blocked.headers


def test_model_load_failure_does_not_silently_fall_back_to_normal_mock(tmp_path):
    with pytest.raises(RuntimeError, match="vision model could not be loaded"):
        create_app(
            {
                "TESTING": True,
                "START_BACKGROUND_WORKERS": False,
                "VISION_PROCESSOR": "unet",
                "UNET_FINE_MODEL_PATH": str(tmp_path / "missing-fine.pt"),
                "UNET_LOCATOR_MODEL_PATH": str(tmp_path / "missing-locator.pt"),
                "ALLOW_MOCK_FALLBACK": False,
                "DATABASE_AUTO_CREATE": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite+pysqlite:///:memory:",
                "SQLALCHEMY_ENGINE_OPTIONS": {},
                "DEFECT_STORAGE_DIR": str(tmp_path / "defects"),
            }
        )
