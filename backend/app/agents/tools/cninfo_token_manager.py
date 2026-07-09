"""Cninfo WebAPI access_token manager with automatic refresh.

The cninfo (深证信) ``access_token`` is a short-lived OAuth2 credential
(≈2h validity) that must be obtained from ``Access Key`` + ``Access Secret``.
Previously the token was stored as a static ``.env`` value and refreshed
manually, which caused the whole cninfo integration to break every 1-2h.

This module provides a process-wide singleton that:
1. Fetches a fresh token via OAuth2 ``client_credentials`` grant.
2. Caches it in memory (optionally on disk) and refreshes proactively before
   expiry (``CNINFO_TOKEN_REFRESH_BUFFER_SECONDS``).
3. Falls back to the legacy static ``CNINFO_ACCESS_TOKEN`` when Key/Secret are
   not configured, so existing deployments keep working.

The cninfo OAuth2 endpoint is not publicly documented in detail, so the token
fetch tries several authentication styles (Basic auth, JSON body, form body)
and tolerates a couple of response field-name variants
(``access_token``/``accessToken``, ``expires_in``/``expiresIn``).
"""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from app.config.settings import settings

logger = logging.getLogger(__name__)

_TOKEN_CACHE_FILE = "cninfo_token.json"


class _TokenManager:
    """Process-wide token cache with lazy refresh."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._token: Optional[str] = None
        self._expires_at: float = 0.0  # epoch seconds; 0 = unknown/invalid
        self._last_refresh_error: Optional[str] = None

    # ── public ──────────────────────────────────────────────────────
    def get_token(self) -> Optional[str]:
        """Return a valid access_token, refreshing if necessary.

        Resolution order:
        1. Cached token still valid (with refresh buffer) → return it.
        2. Access Key/Secret configured → fetch/refresh via OAuth2.
        3. Legacy static ``CNINFO_ACCESS_TOKEN`` configured → return as-is.
        4. Nothing configured → None (caller degrades gracefully).
        """
        with self._lock:
            # 1. cached & valid
            if self._token and self._is_valid():
                return self._token

            # 2. Key/Secret path (preferred, auto-refreshing)
            if settings.CNINFO_ACCESS_KEY and settings.CNINFO_ACCESS_SECRET:
                token = self._refresh_locked()
                if token:
                    return token
                # refresh failed; fall through to legacy token if any

            # 3. legacy static token
            legacy = settings.CNINFO_ACCESS_TOKEN
            if legacy:
                if not self._token:
                    logger.info(
                        "cninfo token: using legacy static CNINFO_ACCESS_TOKEN "
                        "(Key/Secret not configured or refresh failed); "
                        "token expiry is not managed and may cause intermittent failures"
                    )
                self._token = legacy
                # Unknown expiry: treat as never-valid-so-it-stays, but return it.
                self._expires_at = 0.0
                return legacy

            # 4. nothing configured
            return None

    def invalidate(self) -> None:
        """Force the next ``get_token()`` to re-fetch (e.g. on 401)."""
        with self._lock:
            self._token = None
            self._expires_at = 0.0
            self._clear_disk_cache()

    @property
    def last_refresh_error(self) -> Optional[str]:
        return self._last_refresh_error

    # ── internals (must hold self._lock) ────────────────────────────
    def _is_valid(self) -> bool:
        if not self._token or self._expires_at <= 0:
            return False
        return time.time() < (self._expires_at - settings.CNINFO_TOKEN_REFRESH_BUFFER_SECONDS)

    def _refresh_locked(self) -> Optional[str]:
        """Fetch a new token. Caller must hold ``self._lock``."""
        # Try disk cache first (survives process restart).
        cached = self._load_disk_cache()
        if cached and self._is_valid_for(cached.get("expires_at", 0)):
            self._token = cached.get("access_token")
            self._expires_at = cached.get("expires_at", 0)
            logger.debug("cninfo token: reused cached token from disk")
            return self._token

        token, expires_in = self._request_token()
        if not token:
            self._last_refresh_error = "OAuth2 token request failed (see prior warning log)"
            logger.warning("cninfo token: refresh failed; will fall back to legacy/static token if any")
            return None

        self._token = token
        # Be defensive: some responses omit expires_in; default to 1h.
        ttl = expires_in if expires_in and expires_in > 0 else 3600
        self._expires_at = time.time() + ttl
        self._last_refresh_error = None
        self._save_disk_cache(token, self._expires_at)
        logger.info("cninfo token: refreshed successfully (valid for %ss)", ttl)
        return token

    @staticmethod
    def _is_valid_for(expires_at: float) -> bool:
        if expires_at <= 0:
            return False
        return time.time() < (expires_at - settings.CNINFO_TOKEN_REFRESH_BUFFER_SECONDS)

    def _request_token(self) -> tuple[Optional[str], Optional[int]]:
        """Call the OAuth2 endpoint. Tries multiple auth styles for robustness.

        Returns ``(access_token, expires_in_seconds)`` or ``(None, None)``.
        Caller must hold ``self._lock``.
        """
        url = settings.CNINFO_TOKEN_REFRESH_URL
        key = settings.CNINFO_ACCESS_KEY
        secret = settings.CNINFO_ACCESS_SECRET
        attempts = [
            ("form+basic", self._payload_basic_form),
            ("json+basic", self._payload_basic_json),
            ("form-body", self._payload_form_body),
            ("json-body", self._payload_json_body),
        ]
        last_err = ""
        for label, builder in attempts:
            headers, data = builder(key, secret)
            try:
                with httpx.Client(timeout=15.0) as client:
                    resp = client.post(url, headers=headers, content=data)
            except Exception as exc:  # network / DNS / TLS
                last_err = f"{label}: {type(exc).__name__}: {exc}"
                logger.debug("cninfo token attempt %s failed: %s", label, exc)
                continue

            if resp.status_code != 200:
                last_err = f"{label}: HTTP {resp.status_code} {resp.text[:120]}"
                logger.debug("cninfo token attempt %s -> HTTP %s", label, resp.status_code)
                continue

            token, ttl = self._parse_token_response(resp)
            if token:
                logger.debug("cninfo token: obtained via %s", label)
                return token, ttl
            last_err = f"{label}: response missing access_token ({resp.text[:120]})"

        logger.warning("cninfo token: all %d auth styles failed; last=%s", len(attempts), last_err)
        return None, None

    @staticmethod
    def _payload_basic_form(key: str, secret: str) -> tuple[Dict[str, str], bytes]:
        import base64
        cred = base64.b64encode(f"{key}:{secret}".encode()).decode()
        headers = {
            "Authorization": f"Basic {cred}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = "grant_type=client_credentials".encode()
        return headers, data

    @staticmethod
    def _payload_basic_json(key: str, secret: str) -> tuple[Dict[str, str], bytes]:
        import base64
        cred = base64.b64encode(f"{key}:{secret}".encode()).decode()
        headers = {
            "Authorization": f"Basic {cred}",
            "Content-Type": "application/json",
        }
        data = json.dumps({"grant_type": "client_credentials"}).encode()
        return headers, data

    @staticmethod
    def _payload_form_body(key: str, secret: str) -> tuple[Dict[str, str], bytes]:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = f"grant_type=client_credentials&client_id={key}&client_secret={secret}".encode()
        return headers, data

    @staticmethod
    def _payload_json_body(key: str, secret: str) -> tuple[Dict[str, str], bytes]:
        headers = {"Content-Type": "application/json"}
        data = json.dumps({
            "grant_type": "client_credentials",
            "client_id": key,
            "client_secret": secret,
        }).encode()
        return headers, data

    @staticmethod
    def _parse_token_response(resp: httpx.Response) -> tuple[Optional[str], Optional[int]]:
        """Tolerate field-name variants in the OAuth2 response."""
        try:
            payload = resp.json()
        except Exception:
            return None, None

        # access_token may live at top level or nested under "data".
        token = _first_present(payload, ["access_token", "accessToken"])
        if not token and isinstance(payload.get("data"), dict):
            token = _first_present(payload["data"], ["access_token", "accessToken"])

        # expires_in may live at top level or nested under "data" (seconds).
        ttl_raw = _first_present(payload, ["expires_in", "expiresIn", "expire_in"])
        if ttl_raw is None and isinstance(payload.get("data"), dict):
            ttl_raw = _first_present(payload["data"], ["expires_in", "expiresIn"])
        try:
            ttl = int(float(ttl_raw)) if ttl_raw is not None else None
        except (TypeError, ValueError):
            ttl = None
        return token, ttl

    # ── optional disk cache ─────────────────────────────────────────
    def _disk_path(self) -> Optional[Path]:
        directory = settings.CNINFO_TOKEN_CACHE_DIR
        if not directory:
            return None
        return Path(directory) / _TOKEN_CACHE_FILE

    def _save_disk_cache(self, token: str, expires_at: float) -> None:
        path = self._disk_path()
        if not path:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"access_token": token, "expires_at": expires_at, "saved_at": _now_iso()}
            path.write_text(json.dumps(payload), encoding="utf-8")
            path.chmod(0o600)
        except Exception as exc:
            logger.debug("cninfo token: disk cache write failed: %s", exc)

    def _load_disk_cache(self) -> Optional[Dict[str, Any]]:
        path = self._disk_path()
        if not path or not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.debug("cninfo token: disk cache read failed: %s", exc)
            return None

    def _clear_disk_cache(self) -> None:
        path = self._disk_path()
        if path and path.exists():
            try:
                path.unlink()
            except Exception:
                pass


def _first_present(payload: Dict[str, Any], keys: list[str]) -> Optional[Any]:
    for key in keys:
        if payload.get(key) not in (None, ""):
            return payload.get(key)
    return None


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# Module-level singleton — import this, not the class.
token_manager = _TokenManager()


def get_cninfo_access_token() -> Optional[str]:
    """Public entry point used by cninfo_webapi_tool.

    Returns a valid access_token (refreshing if needed), the legacy static
    token, or ``None`` when nothing is configured.
    """
    return token_manager.get_token()


def invalidate_cninfo_token() -> None:
    """Force a re-fetch on the next call (call on auth failure, e.g. 401)."""
    token_manager.invalidate()
