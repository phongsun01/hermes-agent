"""
FastAPI service running on Windows host (NOT inside Docker).

Docker containers call this instead of running Playwright directly,
avoiding DPAPI cookie cross-OS issues.

Run:  py -m uvicorn msc_token_service:app --host 0.0.0.0 --port 8789

From Docker:
    requests.get("http://host.docker.internal:8789/msc/tokens")
"""

import threading

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from msc_get_tokens import get_tokens, SessionExpiredError

app = FastAPI(title="MSC Token Service")

# Playwright's launch_persistent_context holds an OS-level lock on PROFILE_DIR.
# If two requests arrive concurrently, the second would crash. Serialize access.
_lock = threading.Lock()


class TokenResponse(BaseModel):
    bearer_token: str | None
    jsessionid: str | None
    csrf_token: str | None


@app.get("/msc/tokens", response_model=TokenResponse)
def read_tokens() -> TokenResponse:
    """
    Open headless Playwright (reusing logged-in profile), force SSO re-auth,
    extract 3 tokens, close immediately. Takes ~10-15s per request.
    Serialized: only one extraction runs at a time.
    """
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
def health() -> dict:
    """Ping endpoint -- Hermes can check before calling /msc/tokens."""
    return {"status": "ok"}
