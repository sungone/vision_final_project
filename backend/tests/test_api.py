from datetime import datetime, timezone

from app.inspection import InspectionService
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
                metrics={"washerGapPx": 12.4},
                inspection_time=datetime.now(timezone.utc),
            )
        )
    latest = client.get("/api/v1/inspection/latest")
    assert latest.status_code == 200
    assert latest.get_json()["fasteningResult"] == DEFECT
    assert client.get("/api/v1/inspections?page=-1").status_code == 400


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
