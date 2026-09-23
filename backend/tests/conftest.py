import pytest

from app import create_app


@pytest.fixture()
def app(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "START_BACKGROUND_WORKERS": False,
            "VISION_PROCESSOR": "mock",
            "DATABASE_AUTO_CREATE": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite+pysqlite:///:memory:",
            "SQLALCHEMY_ENGINE_OPTIONS": {},
            "DEFECT_STORAGE_DIR": str(tmp_path / "defects"),
        }
    )
    yield app
    app.extensions["vision_runtime"].stop()


@pytest.fixture()
def client(app):
    return app.test_client()
