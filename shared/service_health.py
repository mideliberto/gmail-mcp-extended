"""
Shared service health management for google-mcp monorepo.

Caches googleapiclient Resource instances per service name, with:
- Credential hash comparison (rebuild on token change)
- Age-based rotation (rebuild after MAX_AGE_SECONDS)
- Explicit httplib2 transport cleanup on eviction

Usage (one-liner for any module):
    service = get_service("gmail", "v1", credentials)
"""

import logging
import threading
import time
from typing import Optional

from googleapiclient.discovery import build, Resource
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

MAX_AGE_SECONDS = 4 * 60 * 60  # 4 hours

_cache_lock = threading.Lock()
_cache: dict[str, Resource] = {}  # key → service
_cache_cred_hashes: dict[str, int] = {}  # key → credential hash
_cache_timestamps: dict[str, float] = {}  # key → creation time


def _credentials_hash(credentials: Credentials) -> int:
    return hash((credentials.token, credentials.refresh_token))


def _close_service(service: Resource) -> None:
    """Close the httplib2 transport held by a googleapiclient Resource."""
    try:
        http = getattr(service, "_http", None)
        if http is not None and hasattr(http, "close"):
            http.close()
            logger.debug("Closed httplib2 transport for evicted service")
    except Exception as e:
        logger.debug(f"Could not close httplib2 transport: {e}")


def get_service(
    service_name: str,
    version: str,
    credentials: Credentials,
    force_rebuild: bool = False,
) -> Resource:
    """
    Get a cached Google API service, rebuilding if stale or credentials changed.

    Args:
        service_name: Google API name (e.g. "gmail", "drive", "calendar").
        version: API version (e.g. "v1", "v3").
        credentials: Google OAuth credentials.
        force_rebuild: Force a fresh service even if cache is valid.

    Returns:
        Resource: A googleapiclient Resource instance.
    """
    key = f"{service_name}:{version}"
    cred_hash = _credentials_hash(credentials)
    now = time.monotonic()

    with _cache_lock:
        cached = _cache.get(key)
        if (
            cached is not None
            and not force_rebuild
            and _cache_cred_hashes.get(key) == cred_hash
            and (now - _cache_timestamps.get(key, 0)) < MAX_AGE_SECONDS
        ):
            return cached

        # Evict old service if present
        if cached is not None:
            age = now - _cache_timestamps.get(key, 0)
            reason = (
                "forced" if force_rebuild
                else "credentials changed" if _cache_cred_hashes.get(key) != cred_hash
                else f"age {age:.0f}s > {MAX_AGE_SECONDS}s"
            )
            logger.debug(f"Rebuilding {key} service ({reason})")
            _close_service(cached)

        service = build(service_name, version, credentials=credentials)
        _cache[key] = service
        _cache_cred_hashes[key] = cred_hash
        _cache_timestamps[key] = now
        logger.debug(f"Created {key} service")
        return service


def invalidate(service_name: Optional[str] = None) -> None:
    """
    Invalidate cached services, closing their transports.

    Args:
        service_name: If provided, only invalidate services matching this name
                      (e.g. "gmail" invalidates "gmail:v1"). If None, invalidate all.
    """
    with _cache_lock:
        keys_to_remove = [
            k for k in _cache
            if service_name is None or k.startswith(f"{service_name}:")
        ]
        for key in keys_to_remove:
            _close_service(_cache[key])
            del _cache[key]
            del _cache_cred_hashes[key]
            del _cache_timestamps[key]
            logger.debug(f"Invalidated {key} service")
