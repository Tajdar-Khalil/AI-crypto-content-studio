
import os
import re
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PUBLISH_SCRIPT = (
    PROJECT_ROOT
    / "scripts"
    / "binance-square"
    / "post-text.mjs"
)


def is_configured() -> bool:
    """Return whether the publishing script can find its dedicated posting key."""
    return bool(os.environ.get("BINANCE_SQUARE_OPENAPI_KEY", "").strip())


def publish_text_post(text: str) -> dict[str, Any]:
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
                "The dedicated Binance Square posting key is not available to this app. "
                "Set BINANCE_SQUARE_OPENAPI_KEY in the local environment and restart Streamlit."
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
            "message": f"Could not start the publishing script ({type(exc).__name__}).",
            "uncertain": False,
        }

    output = "\n".join(
        part for part in (result.stdout, result.stderr) if part
    ).strip()

    if result.returncode == 0:
        post_id_match = re.search(r"^ID:\s*(.+)$", output, flags=re.MULTILINE)
        post_url_match = re.search(r"^Link:\s*(.+)$", output, flags=re.MULTILINE)
        candidate_id = post_id_match.group(1).strip() if post_id_match else ""
        post_id = candidate_id if re.fullmatch(r"\d+", candidate_id) else ""
        candidate_url = post_url_match.group(1).strip() if post_url_match else ""
        parsed_url = urlparse(candidate_url)
        valid_url = (
            parsed_url.scheme == "https"
            and parsed_url.hostname in {"binance.com", "www.binance.com"}
            and bool(re.fullmatch(r"/square/post/\d+", parsed_url.path))
        )
        post_url = candidate_url if valid_url else ""
        return {
            "success": True,
            "message": output or "Binance returned a successful exit status.",
            "uncertain": False,
            "external_post_id": post_id or None,
            "external_post_url": post_url or None,
        }

    # Do not automatically retry: a failed response may not always prove
    # that the remote service did not accept the post.
    lower_output = output.casefold()
    provider_rejected = "api error [" in lower_output
    uncertain = not provider_rejected
    return {
        "success": False,
        "message": output or f"Publishing script exited with code {result.returncode}.",
        "uncertain": uncertain,
    }
