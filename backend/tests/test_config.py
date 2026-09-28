import pytest

from app.config import _optional_float, _strict_float


def test_optional_float_accepts_explicit_null(monkeypatch):
    monkeypatch.setenv("TEST_OPTIONAL_FLOAT", "null")

    assert _optional_float("TEST_OPTIONAL_FLOAT") is None


@pytest.mark.parametrize("value", ["invalid", "nan", "inf", "-inf"])
def test_optional_float_rejects_invalid_or_non_finite_values(monkeypatch, value):
    monkeypatch.setenv("TEST_OPTIONAL_FLOAT", value)

    with pytest.raises(ValueError, match="finite number or null"):
        _optional_float("TEST_OPTIONAL_FLOAT")


@pytest.mark.parametrize("value", ["invalid", "nan", "inf", "-inf"])
def test_strict_float_rejects_invalid_or_non_finite_values(monkeypatch, value):
    monkeypatch.setenv("TEST_STRICT_FLOAT", value)

    with pytest.raises(ValueError, match="finite number"):
        _strict_float("TEST_STRICT_FLOAT", 1.36)
