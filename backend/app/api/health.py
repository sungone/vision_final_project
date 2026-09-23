from flask import Blueprint, current_app, jsonify


bp = Blueprint("health", __name__)


@bp.get("/api/v1/health")
def health():
    runtime = current_app.extensions["vision_runtime"]
    healthy = runtime.model_loaded or runtime.model_type == "mock"
    return jsonify(
        {
            "status": "ok" if healthy else "degraded",
            "service": "vision-backend",
            "modelLoaded": runtime.model_loaded,
            "modelType": runtime.model_type,
        }
    ), 200 if healthy else 503
