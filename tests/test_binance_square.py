from types import SimpleNamespace

from content_studio import binance_square


def test_publish_text_post_extracts_success_metadata(monkeypatch):
    monkeypatch.setenv("BINANCE_SQUARE_OPENAPI_KEY", "test-key")
    monkeypatch.setattr(
        binance_square.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout="Success!\nID: 12345\nLink: https://www.binance.com/square/post/12345",
            stderr="",
        ),
    )

    result = binance_square.publish_text_post("Reviewed post")

    assert result["success"] is True
    assert result["external_post_id"] == "12345"
    assert result["external_post_url"] == "https://www.binance.com/square/post/12345"


def test_publish_text_post_requires_environment_key(monkeypatch):
    monkeypatch.delenv("BINANCE_SQUARE_OPENAPI_KEY", raising=False)

    result = binance_square.publish_text_post("Reviewed post")

    assert result["success"] is False
    assert result["uncertain"] is False
    assert "posting key" in result["message"].lower()


def test_publish_timeout_is_uncertain(monkeypatch):
    monkeypatch.setenv("BINANCE_SQUARE_OPENAPI_KEY", "test-key")

    def timeout(*args, **kwargs):
        raise binance_square.subprocess.TimeoutExpired("node", 90)

    monkeypatch.setattr(binance_square.subprocess, "run", timeout)
    result = binance_square.publish_text_post("Reviewed post")

    assert result["success"] is False
    assert result["uncertain"] is True


def test_provider_rejection_is_confirmed_failure(monkeypatch):
    monkeypatch.setenv("BINANCE_SQUARE_OPENAPI_KEY", "test-key")
    monkeypatch.setattr(
        binance_square.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="Failed: API error [220003]: API Key not found",
        ),
    )

    result = binance_square.publish_text_post("Reviewed post")

    assert result["success"] is False
    assert result["uncertain"] is False
