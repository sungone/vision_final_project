from flask import Blueprint, Response, current_app, redirect, render_template_string, stream_with_context, url_for

from app.streaming import generate_mjpeg


bp = Blueprint("stream", __name__)


@bp.get("/")
def index():
    return redirect(url_for("stream.stream_test"))


@bp.get("/favicon.ico")
def favicon():
    return Response(status=204)


@bp.get("/api/v1/stream")
def stream():
    runtime = current_app.extensions["vision_runtime"]
    response = Response(
        stream_with_context(generate_mjpeg(runtime.encoded_frames, current_app.config["STREAM_FPS"])),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response


@bp.get("/stream-test")
def stream_test():
    return render_template_string(
        """<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\">
        <title>Vision MJPEG Test</title><style>body{font-family:sans-serif;background:#111;color:#eee;text-align:center}
        img{max-width:95vw;max-height:85vh;border:1px solid #555}</style></head>
        <body><h1>Vision MJPEG Test</h1><img src=\"/api/v1/stream\" alt=\"camera stream\"></body></html>"""
    )


