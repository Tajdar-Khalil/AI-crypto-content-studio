
import os
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PUBLISH_SCRIPT = (
    PROJECT_ROOT
    / "scripts"
    / "binance-square"
    / "post-text.mjs"
)


def publish_text_post(text: str) -> dict:
    """Publish one text post using Binance's official publishing script."""

    if not isinstance(text, str) or not text.strip():
        return {
            "success": False,
            "message": "Post text cannot be empty.",
            "uncertain": False,
        }

    if not PUBLISH_SCRIPT.is_file():
        return {
            "success": False,
            "message": f"Publishing script not found: {PUBLISH_SCRIPT}",
            "uncertain": False,
        }

    if not os.environ.get("BINANCE_SQUARE_OPENAPI_KEY", "").strip():
        return {
            "success": False,
            "message": (
                "The Binance publishing key is not available to this app. "
                "Restart Streamlit from a terminal where the key is available."
            ),
            "uncertain": False,
        }

    try:
        result = subprocess.run(
            [
                "node",
                str(PUBLISH_SCRIPT),
                "--text",
                text,
            ],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
        )
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": (
                "Publishing timed out. The result is uncertain. "
                "Check Binance Square before attempting another post."
            ),
            "uncertain": True,
        }
    except OSError as exc:
        return {
            "success": False,
            "message": f"Could not start the publishing script: {exc}",
            "uncertain": False,
        }

    output = "\n".join(
        part for part in (result.stdout, result.stderr) if part
    ).strip()

    if result.returncode == 0:
        return {
            "success": True,
            "message": output or "Binance returned a successful exit status.",
            "uncertain": False,
        }

    # Do not automatically retry: a failed response may not always prove
    # that the remote service did not accept the post.
    return {
        "success": False,
        "message": output or f"Publishing script exited with code {result.returncode}.",
        "uncertain": True,
    }
