from .health import bp as health_bp
from .inspections import bp as inspections_bp
from .status import bp as status_bp
from .stream import bp as stream_bp

__all__ = ["health_bp", "inspections_bp", "status_bp", "stream_bp"]
