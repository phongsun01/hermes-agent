"""
FastAPI service running on Windows host (NOT inside Docker).

Docker containers call this instead of running Playwright directly,
avoiding DPAPI cookie cross-OS issues.

Run:  py -m uvicorn msc_token_service:app --host 0.0.0.0 --port 8789

From Docker:
    requests.get("http://host.docker.internal:8789/msc/tokens", headers={"X-MSC-Service-Key": "your_key"})
"""

import os
import secrets
import sys
import threading
from typing import Optional

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

from msc_get_tokens import get_tokens, SessionExpiredError

# Auth Configuration
MSC_SERVICE_KEY = os.environ.get("MSC_SERVICE_KEY", "").strip()

# Detect loopback vs non-loopback bindings to enforce fail-closed security
is_non_loopback = False
for idx, arg in enumerate(sys.argv):
    if arg == "--host" and idx + 1 < len(sys.argv):
        if sys.argv[idx + 1] not in ("127.0.0.1", "localhost"):
            is_non_loopback = True
    elif arg.startswith("--host="):
        if arg.split("=", 1)[1] not in ("127.0.0.1", "localhost"):
            is_non_loopback = True

env_host = os.environ.get("MSC_SERVICE_HOST", "127.0.0.1").strip()
if env_host not in ("127.0.0.1", "localhost"):
    is_non_loopback = True

if is_non_loopback and not MSC_SERVICE_KEY:
    print("CRITICAL: MSC_SERVICE_KEY must be set when binding to a non-loopback address!", file=sys.stderr)
    sys.exit(1)

app = FastAPI(title="MSC Token Service")

# Playwright's launch_persistent_context holds an OS-level lock on PROFILE_DIR.
# If two requests arrive concurrently, the second would crash. Serialize access.
_lock = threading.Lock()


class TokenResponse(BaseModel):
    bearer_token: str | None
    jsessionid: str | None
    csrf_token: str | None


def _verify_auth(x_msc_service_key: Optional[str]) -> None:
    if not MSC_SERVICE_KEY:
        return
    if not x_msc_service_key or not secrets.compare_digest(x_msc_service_key, MSC_SERVICE_KEY):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Invalid or missing X-MSC-Service-Key header."
        )


@app.get("/msc/tokens", response_model=TokenResponse)
def read_tokens(x_msc_service_key: Optional[str] = Header(None)) -> TokenResponse:
    """
    Open headless Playwright (reusing logged-in profile), force SSO re-auth,
    extract 3 tokens, close immediately. Takes ~10-15s per request.
    Serialized: only one extraction runs at a time.
    """
    _verify_auth(x_msc_service_key)

    acquired = _lock.acquire(timeout=30)
    if not acquired:
        raise HTTPException(
            status_code=503,
            detail="Another token extraction is in progress. Try again shortly.",
        )
    try:
        tokens = get_tokens()
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except SessionExpiredError as e:
        raise HTTPException(
            status_code=401,
            detail=f"{e}. Manual re-login required on the host machine.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during token extraction: {e}",
        )
    finally:
        _lock.release()

    missing = [k for k, v in tokens.items() if not v]
    if missing:
        raise HTTPException(
            status_code=502,
            detail=f"Missing tokens: {missing}. Check msc_get_tokens.py.",
        )

    return TokenResponse(**tokens)


@app.get("/msc/health")
def health(x_msc_service_key: Optional[str] = Header(None)) -> dict:
    """Ping endpoint -- Hermes can check before calling /msc/tokens."""
    _verify_auth(x_msc_service_key)
    return {"status": "ok"}
