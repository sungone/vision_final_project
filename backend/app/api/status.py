from flask import Blueprint, current_app, jsonify
from sqlalchemy import text

from app.database import db


bp = Blueprint("status", __name__)


@bp.get("/api/v1/system/status")
def system_status():
    runtime = current_app.extensions["vision_runtime"]
    database_connected = True
    database_error = runtime.last_database_error
    try:
        db.session.execute(text("SELECT 1"))
    except Exception as exc:
        db.session.rollback()
        database_connected = False
        database_error = str(exc)
    return jsonify(
        {
            "cameraConnected": runtime.camera.connected,
            "visionWorkerRunning": runtime.vision.running,
            "modelLoaded": runtime.model_loaded,
            "modelType": runtime.model_type,
            "visionDevice": runtime.vision_device,
            "databaseConnected": database_connected,
            "eventState": runtime.event_manager.state.value,
            "lastCapturedAt": runtime.camera.last_frame_at.isoformat() if runtime.camera.last_frame_at else None,
            "lastProcessedAt": runtime.vision.last_processed_at.isoformat() if runtime.vision.last_processed_at else None,
            "lastInferenceTimeMs": runtime.vision.last_inference_time_ms,
            "lastDetectionCount": runtime.vision.last_detection_count,
            "cameraError": runtime.camera.last_error,
            "visionError": runtime.vision.last_error,
            "modelError": runtime.model_error,
            "databaseError": database_error,
        }
    )
