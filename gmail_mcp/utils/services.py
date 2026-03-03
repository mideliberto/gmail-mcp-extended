"""
Service Caching Module

Provides cached instances of Gmail, Calendar, and People services.
Delegates to shared.service_health for lifecycle management.
"""

from googleapiclient.discovery import Resource
from google.oauth2.credentials import Credentials

from shared.service_health import get_service, invalidate


def get_gmail_service(credentials: Credentials) -> Resource:
    """
    Get a cached Gmail API service instance.

    The service is cached and reused across calls. If the credentials change
    (different token), a new service is created.

    Args:
        credentials: The Google OAuth credentials.

    Returns:
        Resource: The Gmail API service instance.
    """
    return get_service("gmail", "v1", credentials)


def get_calendar_service(credentials: Credentials) -> Resource:
    """
    Get a cached Calendar API service instance.

    The service is cached and reused across calls. If the credentials change
    (different token), a new service is created.

    Args:
        credentials: The Google OAuth credentials.

    Returns:
        Resource: The Calendar API service instance.
    """
    return get_service("calendar", "v3", credentials)


def get_people_service(credentials: Credentials) -> Resource:
    """
    Get a cached People API service instance.

    The service is cached and reused across calls. If the credentials change
    (different token), a new service is created.

    Args:
        credentials: The Google OAuth credentials.

    Returns:
        Resource: The People API service instance.
    """
    return get_service("people", "v1", credentials)


def clear_service_cache() -> None:
    """
    Clear all cached service instances.

    This should be called when logging out or when credentials are invalidated.
    """
    invalidate()
