"""
Email Retention Tools Module

Handles automated email retention policy enforcement.
"""

from typing import Dict, Any, List, Optional

from mcp.server.fastmcp import FastMCP

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.utils.services import get_gmail_service
from gmail_mcp.auth.oauth import get_credentials

logger = get_logger(__name__)


# Default retention policies - label name to days
# Use None for INDEF (never auto-delete)
DEFAULT_RETENTION_POLICIES = {
    "Retention/7-days": 7,
    "Retention/30-days": 30,
    "Retention/90-days": 90,
    "Retention/6-months": 180,
    "Retention/1-year": 365,
    "Retention/3-years": 1095,
    "Retention/7-years": 2555,
    "Retention/INDEF": None,  # Never auto-delete
}


def _find_label_by_name(service, label_name: str) -> Optional[Dict[str, Any]]:
    """
    Find a label by name (case-insensitive).

    Args:
        service: Gmail API service instance
        label_name: The label name to search for

    Returns:
        Label dict with 'id' and 'name', or None if not found
    """
    results = service.users().labels().list(userId="me").execute()
    labels = results.get("labels", [])

    label_name_lower = label_name.lower()
    for label in labels:
        if label["name"].lower() == label_name_lower:
            return {"id": label["id"], "name": label["name"]}

    return None


def _count_expired_emails(service, label_name: str, days: int) -> int:
    """
    Count emails that match a label and are older than the specified days.

    Args:
        service: Gmail API service instance
        label_name: The retention label name
        days: Number of days - emails older than this are expired

    Returns:
        Count of expired emails
    """
    query = f"label:{label_name.replace('/', '-')} older_than:{days}d"

    result = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=1  # We just need the count estimate
    ).execute()

    return result.get("resultSizeEstimate", 0)


def _fetch_messages_with_pagination(
    service,
    query: str,
    max_messages: int
) -> List[Dict[str, Any]]:
    """
    Fetch messages matching a query with pagination support.

    Args:
        service: Gmail API service instance
        query: Gmail search query
        max_messages: Maximum number of messages to fetch

    Returns:
        List of message dicts with 'id' keys
    """
    messages = []
    page_token: Optional[str] = None

    while len(messages) < max_messages:
        remaining = max_messages - len(messages)
        page_size = min(remaining, 100)

        request_params = {
            "userId": "me",
            "q": query,
            "maxResults": page_size
        }
        if page_token:
            request_params["pageToken"] = page_token

        result = service.users().messages().list(**request_params).execute()
        page_messages = result.get("messages", [])

        if not page_messages:
            break

        messages.extend(page_messages)
        page_token = result.get("nextPageToken")

        if not page_token:
            break

    return messages[:max_messages]


def _batch_trash_emails(service, message_ids: List[str]) -> tuple:
    """
    Batch trash emails using Gmail's native batchModify endpoint.

    Args:
        service: Gmail API service instance
        message_ids: List of message IDs to trash

    Returns:
        tuple: (success_count, failure_count)
    """
    if not message_ids:
        return 0, 0

    batch_size = 1000
    total_success = 0
    total_failed = 0

    for i in range(0, len(message_ids), batch_size):
        batch_ids = message_ids[i:i + batch_size]

        body = {
            "ids": batch_ids,
            "addLabelIds": ["TRASH"],
            "removeLabelIds": ["INBOX"]
        }

        try:
            service.users().messages().batchModify(userId="me", body=body).execute()
            total_success += len(batch_ids)
        except Exception as e:
            total_failed += len(batch_ids)
            logger.error(f"Batch trash failed: {e}")

    return total_success, total_failed


def setup_email_retention_tools(mcp: FastMCP) -> None:
    """Set up email retention management tools on the FastMCP application."""

    @mcp.tool()
    def setup_retention_labels() -> Dict[str, Any]:
        """
        Create standard retention labels if they don't exist.

        Creates the following labels:
        - Retention/7-days (for emails to delete after 7 days)
        - Retention/30-days (for emails to delete after 30 days)
        - Retention/90-days (for emails to delete after 90 days)
        - Retention/6-months (for emails to delete after 6 months)
        - Retention/1-year (for emails to delete after 1 year)
        - Retention/3-years (for emails to delete after 3 years)

        Returns:
            Dict[str, Any]: Result including created and existing labels
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)

            # First ensure parent "Retention" label exists
            parent_label = _find_label_by_name(service, "Retention")
            if not parent_label:
                result = service.users().labels().create(
                    userId="me",
                    body={"name": "Retention", "labelListVisibility": "labelShow", "messageListVisibility": "show"}
                ).execute()
                logger.info(f"Created parent label: Retention")

            created = []
            existing = []

            for label_name in DEFAULT_RETENTION_POLICIES.keys():
                label = _find_label_by_name(service, label_name)
                if label:
                    existing.append(label_name)
                else:
                    result = service.users().labels().create(
                        userId="me",
                        body={"name": label_name, "labelListVisibility": "labelShow", "messageListVisibility": "show"}
                    ).execute()
                    created.append(label_name)
                    logger.info(f"Created label: {label_name}")

            return {
                "success": True,
                "message": f"Setup complete. Created {len(created)} labels, {len(existing)} already existed.",
                "created": created,
                "existing": existing
            }

        except Exception as e:
            logger.error(f"Failed to setup retention labels: {e}")
            return {"success": False, "error": f"Failed to setup retention labels: {e}"}

    @mcp.tool()
    def enforce_retention_policies(
        dry_run: bool = True,
        max_emails_per_label: int = 100
    ) -> Dict[str, Any]:
        """
        Enforce email retention policies by deleting expired emails.

        Scans all retention labels and trashes emails that have exceeded their
        retention period. By default runs in dry_run mode to preview what would
        be deleted.

        Args:
            dry_run (bool): If True, only reports what would be deleted without
                           actually deleting. Set to False to perform deletion.
                           Default: True (safe mode)
            max_emails_per_label (int): Maximum emails to process per retention
                                       label (default: 100, max: 500)

        Returns:
            Dict[str, Any]: Results including:
                - dry_run: Whether this was a dry run
                - summary: Total emails processed/would be processed
                - by_label: Breakdown by retention label with counts and oldest dates
                - errors: Any errors encountered

        Example usage:
        1. Preview what would be deleted:
           enforce_retention_policies(dry_run=True)

        2. Actually delete expired emails:
           enforce_retention_policies(dry_run=False)

        3. Process more emails per label:
           enforce_retention_policies(dry_run=False, max_emails_per_label=500)
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)
            max_emails_per_label = min(max_emails_per_label, 500)

            results_by_label = {}
            total_processed = 0
            total_failed = 0
            errors = []

            for label_name, days in DEFAULT_RETENTION_POLICIES.items():
                # Skip INDEF labels - never auto-delete
                if days is None:
                    results_by_label[label_name] = {
                        "status": "skipped",
                        "reason": "INDEF - never auto-delete",
                        "retention_days": None
                    }
                    continue

                # Check if label exists
                label = _find_label_by_name(service, label_name)
                if not label:
                    results_by_label[label_name] = {
                        "status": "skipped",
                        "reason": "Label does not exist",
                        "retention_days": days
                    }
                    continue

                # Build query - use label ID for reliability
                # Gmail search uses hyphenated label names for nested labels
                query = f"label:{label_name.replace('/', '-')} older_than:{days}d"

                if dry_run:
                    # Just count, don't fetch full list
                    count = _count_expired_emails(service, label_name, days)
                    results_by_label[label_name] = {
                        "status": "would_delete",
                        "count": count,
                        "retention_days": days
                    }
                    total_processed += count
                else:
                    # Fetch and trash messages
                    messages = _fetch_messages_with_pagination(service, query, max_emails_per_label)

                    if not messages:
                        results_by_label[label_name] = {
                            "status": "no_expired",
                            "count": 0,
                            "retention_days": days
                        }
                        continue

                    message_ids = [m["id"] for m in messages]
                    trashed, failed = _batch_trash_emails(service, message_ids)

                    results_by_label[label_name] = {
                        "status": "processed",
                        "trashed": trashed,
                        "failed": failed,
                        "retention_days": days
                    }

                    total_processed += trashed
                    total_failed += failed

                    if failed > 0:
                        errors.append(f"{label_name}: {failed} emails failed to trash")

            return {
                "success": True,
                "dry_run": dry_run,
                "summary": {
                    "total_processed": total_processed,
                    "total_failed": total_failed,
                    "message": f"{'Would trash' if dry_run else 'Trashed'} {total_processed} emails across all retention labels."
                },
                "by_label": results_by_label,
                "errors": errors if errors else None
            }

        except Exception as e:
            logger.error(f"Failed to enforce retention policies: {e}")
            return {"success": False, "error": f"Failed to enforce retention policies: {e}"}

    @mcp.tool()
    def get_retention_status() -> Dict[str, Any]:
        """
        Get current status of all retention labels.

        Shows how many emails are in each retention label and how many
        are expired (past their retention period).

        Returns:
            Dict[str, Any]: Status of each retention label including:
                - total_count: Total emails with this label
                - expired_count: Emails past retention period
                - retention_days: The retention period for this label

        Example usage:
        1. Check retention status: get_retention_status()
        2. Review results, then: enforce_retention_policies(dry_run=False)
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)

            status_by_label = {}
            total_emails = 0
            total_expired = 0

            for label_name, days in DEFAULT_RETENTION_POLICIES.items():
                label = _find_label_by_name(service, label_name)
                if not label:
                    status_by_label[label_name] = {
                        "exists": False,
                        "retention_days": days
                    }
                    continue

                # Count total emails with this label
                total_query = f"label:{label_name.replace('/', '-')}"
                total_result = service.users().messages().list(
                    userId="me",
                    q=total_query,
                    maxResults=1
                ).execute()
                label_total = total_result.get("resultSizeEstimate", 0)

                # For INDEF labels, no emails are ever "expired"
                if days is None:
                    status_by_label[label_name] = {
                        "exists": True,
                        "total_count": label_total,
                        "expired_count": 0,
                        "retention_days": None,
                        "label_id": label["id"],
                        "note": "INDEF - never auto-delete"
                    }
                    total_emails += label_total
                    continue

                # Count expired emails
                expired_count = _count_expired_emails(service, label_name, days)

                status_by_label[label_name] = {
                    "exists": True,
                    "total_count": label_total,
                    "expired_count": expired_count,
                    "retention_days": days,
                    "label_id": label["id"]
                }

                total_emails += label_total
                total_expired += expired_count

            return {
                "success": True,
                "summary": {
                    "total_retention_emails": total_emails,
                    "total_expired": total_expired
                },
                "by_label": status_by_label
            }

        except Exception as e:
            logger.error(f"Failed to get retention status: {e}")
            return {"success": False, "error": f"Failed to get retention status: {e}"}
