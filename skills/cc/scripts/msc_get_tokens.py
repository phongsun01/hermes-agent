"""
Extract MSC tokens (Bearer, JSESSIONID, CSRF) from a pre-logged-in profile.

Two-step flow:
  1. Navigate to /c/portal/login  -> forces Keycloak SSO re-auth via stored
     KEYCLOAK_SESSION cookie (no user interaction needed).
  2. Navigate to /web/guest/profile-info -> Vue app receives bearerToken from
     Liferay, extractable via page.evaluate().

Run:   py msc_get_tokens.py
Requires: manual Chrome login at least once (profile stored in ~/.hermes/msc_profile).
Does NOT keep the browser running -- opens, captures, closes.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright, Request
from playwright.sync_api import TimeoutError as PWTimeout

PROFILE_DIR = Path.home() / ".hermes" / "msc_profile"

# Step 1: force SSO login (Keycloak auto-approves if session cookie is valid)
LOGIN_URL = "https://muasamcong.mpi.gov.vn/c/portal/login"
# Step 2: profile page where Vue injects bearerToken
PROFILE_URL = "https://muasamcong.mpi.gov.vn/web/guest/profile-info"

# URL hints for network-level bearer interception (bonus path)
API_HINTS = [
    "/o/egp-portal-personal-page/services/",
    "/o/egp-portal-",
    "/auth/realms/",
    "/api/jsonws/",
]

# Navigation / polling timeouts (ms)
GOTO_TIMEOUT_MS = 30_000
SIGNED_IN_TIMEOUT_MS = 12_000
BEARER_TIMEOUT_MS = 12_000

# Chrome executable paths (Windows)
_CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
]


def _get_chrome_user_agent() -> str:
    """
    Build a real-looking UA string using the installed Chrome version.

    In headless mode, Chrome sends 'HeadlessChrome' in the UA which gets
    blocked by MSC's WAF. We detect the real version to avoid both:
    - the HeadlessChrome marker
    - a hardcoded version drifting from the actual installed binary
    """
    import re
    version = None
    for path_str in _CHROME_PATHS:
        path = Path(path_str)
        if not path.exists():
            continue
            
        # 1. Try directory scan (works beautifully on Windows without spawning GUI processes)
        try:
            parent = path.parent
            if parent.exists():
                version_dirs = [
                    d.name for d in parent.iterdir()
                    if d.is_dir() and re.match(r'^\d+\.\d+\.\d+\.\d+$', d.name)
                ]
                if version_dirs:
                    version = sorted(version_dirs, key=lambda s: [int(x) for x in s.split('.')])[-1]
                    break
        except Exception:
            pass

        # 2. Fallback to subprocess (works on Linux/macOS)
        try:
            result = subprocess.run(
                [path_str, "--version"],
                capture_output=True, text=True, timeout=5,
            )
            parts = result.stdout.strip().split()
            if parts:
                version = parts[-1]
                break
        except Exception:
            continue
            
    if not version:
        raise RuntimeError("Không tìm thấy Chrome, không thể xác định UA an toàn để tránh block. Đảm bảo Chrome được cài đặt ở vị trí chuẩn.")

    return (
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        f"AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{version} Safari/537.36"
    )


class SessionExpiredError(Exception):
    """Keycloak session has expired -- manual re-login required."""

    def __init__(self, detail: str = "") -> None:
        super().__init__(f"Session expired. {detail}".strip())


class TokenCapture:
    """Intercept bearer tokens from outgoing request headers (bonus path)."""

    def __init__(self) -> None:
        self.bearer_token: Optional[str] = None

    def on_request(self, request: Request) -> None:
        if self.bearer_token:
            return
        url = request.url
        if not any(h in url for h in API_HINTS):
            return
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            self.bearer_token = auth.split(" ", 1)[1]
            print(f"  >> Bearer captured from header (len={len(self.bearer_token)})", flush=True)


def _wait_signed_in(page, timeout_ms: int = SIGNED_IN_TIMEOUT_MS) -> None:
    """Poll until Liferay.ThemeDisplay.isSignedIn() returns true."""
    try:
        page.wait_for_function(
            "() => { try { return Liferay.ThemeDisplay.isSignedIn(); } catch(e) { return false; } }",
            timeout=timeout_ms,
        )
    except PWTimeout as e:
        raise SessionExpiredError(
            "isSignedIn() did not become true within "
            f"{timeout_ms / 1000:.0f}s. Manual re-login required."
        ) from e


def _wait_bearer_token(page, timeout_ms: int = BEARER_TIMEOUT_MS) -> str:
    """Poll until Vue injects bearerToken on #personal-page-content, return it."""
    try:
        page.wait_for_function(
            """() => {
                try {
                    const el = document.querySelector('#personal-page-content');
                    return el && el.__vue__ && el.__vue__.bearerToken ? true : false;
                } catch(e) { return false; }
            }""",
            timeout=timeout_ms,
        )
    except PWTimeout:
        # bearerToken not injected within timeout -- will fall through to
        # extract_tokens_from_js() fallbacks (scan DOM, localStorage, etc.)
        pass


def extract_tokens_from_js(page) -> dict:
    """Extract bearer + CSRF directly from the Liferay/Vue JS context."""
    return page.evaluate("""() => {
        const result = {bearer: null, csrf: null};
        // CSRF: Liferay.authToken (p_auth)
        try { result.csrf = Liferay.authToken || null; } catch(e) {}
        // Bearer: Vue instance on #personal-page-content
        try {
            const el = document.querySelector('#personal-page-content');
            if (el && el.__vue__ && el.__vue__.bearerToken) {
                result.bearer = el.__vue__.bearerToken;
            }
        } catch(e) {}
        // Fallback: scan all Vue instances for bearerToken
        if (!result.bearer) {
            try {
                const all = document.querySelectorAll('*');
                for (const el of all) {
                    if (el.__vue__ && el.__vue__.bearerToken) {
                        result.bearer = el.__vue__.bearerToken;
                        break;
                    }
                }
            } catch(e) {}
        }
        // Fallback: localStorage
        if (!result.bearer) {
            try { result.bearer = localStorage.getItem('access_token') || null; } catch(e) {}
        }
        return result;
    }""")


def get_jsessionid(context) -> Optional[str]:
    for cookie in context.cookies():
        if cookie["name"].upper() == "JSESSIONID":
            return cookie["value"]
    return None


def get_tokens() -> dict:
    """
    Open the pre-logged-in profile, force SSO re-auth, then extract tokens.

    Returns dict with keys: bearer_token, jsessionid, csrf_token.

    Raises:
        FileNotFoundError: no profile directory yet.
        SessionExpiredError: Keycloak session expired or navigation timeout.
    """
    if not PROFILE_DIR.exists():
        raise FileNotFoundError(
            f"No profile at {PROFILE_DIR}. Run manual login first."
        )

    capture = TokenCapture()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=True,
            channel="chrome",
            user_agent=_get_chrome_user_agent(),
            ignore_default_args=["--enable-automation"],
        )
        try:
            page = context.new_page()
            page.on("request", capture.on_request)

            # --- Step 1: Force SSO login ---
            print("Step 1: Force SSO login...", flush=True)
            try:
                page.goto(LOGIN_URL, wait_until="commit", timeout=GOTO_TIMEOUT_MS)
            except PWTimeout as e:
                raise SessionExpiredError(
                    f"Timeout ({GOTO_TIMEOUT_MS/1000:.0f}s) loading {LOGIN_URL}. "
                    "Server may be unreachable or IP may be temporarily blocked."
                ) from e

            _wait_signed_in(page)
            print(f"  Signed in. URL: {page.url}", flush=True)

            # --- Step 2: Navigate to profile page for bearerToken ---
            print("Step 2: Navigate to profile-info...", flush=True)
            try:
                resp = page.goto(PROFILE_URL, wait_until="commit", timeout=GOTO_TIMEOUT_MS)
            except PWTimeout as e:
                raise SessionExpiredError(f"Timeout loading {PROFILE_URL}") from e

            if resp and resp.status in (401, 403):
                raise SessionExpiredError(f"HTTP {resp.status} on profile page.")

            # Poll for bearerToken in Vue (returns early when available)
            _wait_bearer_token(page)

            # --- Step 3: Extract tokens from JS context ---
            print("Step 3: Extract tokens from JS...", flush=True)
            js_tokens = extract_tokens_from_js(page)

            bearer = capture.bearer_token or js_tokens.get("bearer")
            csrf = js_tokens.get("csrf")
            jsessionid = get_jsessionid(context)

        finally:
            context.close()

    return {
        "bearer_token": bearer,
        "jsessionid": jsessionid,
        "csrf_token": csrf,
    }


def _mask(token: Optional[str], visible: int = 15) -> str:
    """Mask a token for safe logging: show first N chars + '...'."""
    if not token:
        return "None"
    return f"{token[:visible]}..." if len(token) > visible else token


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Extract tokens from logged-in profile")
    ap.add_argument("--raw", action="store_true", help="Print raw unmasked tokens to stdout")
    args = ap.parse_args()

    try:
        tokens = get_tokens()
    except FileNotFoundError as e:
        print(f"Error: {e}", flush=True)
        return 1
    except SessionExpiredError as e:
        print(f"Error: {e}", flush=True)
        print("Please re-login manually.", flush=True)
        return 2

    missing = [k for k, v in tokens.items() if not v]
    if missing:
        print(f"Warning: Missing tokens: {missing}", flush=True)

    # Log masked values to avoid leaking live tokens into logs
    print(f"  bearer_token: {_mask(tokens['bearer_token'])}", flush=True)
    print(f"  jsessionid:   {_mask(tokens['jsessionid'])}", flush=True)
    print(f"  csrf_token:   {_mask(tokens['csrf_token'])}", flush=True)

    if args.raw:
        # Full JSON to stdout for programmatic consumption (pipe to jq, etc.)
        print(json.dumps(tokens, ensure_ascii=False, indent=2), flush=True)
    return 0 if not missing else 3


if __name__ == "__main__":
    sys.exit(main())
