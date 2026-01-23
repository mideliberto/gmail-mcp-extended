"""
Subscription Management Tools Module

Provides tools for managing email subscriptions and newsletters.
"""

import re
from collections import defaultdict
from typing import Dict, Any, List, Optional

from mcp.server.fastmcp import FastMCP

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.utils.services import get_gmail_service
from gmail_mcp.auth.oauth import get_credentials

logger = get_logger(__name__)


def setup_subscription_tools(mcp: FastMCP) -> None:
    """Set up subscription management tools on the FastMCP application."""

    def _extract_unsubscribe_link(message: Dict[str, Any]) -> Optional[str]:
        """Extract unsubscribe link from email headers or body."""
        headers = {h["name"].lower(): h["value"] for h in message.get("payload", {}).get("headers", [])}

        # Check List-Unsubscribe header first
        list_unsub = headers.get("list-unsubscribe", "")
        if list_unsub:
            # Extract URL from header (format: <url> or <mailto:...>, <url>)
            urls = re.findall(r'<(https?://[^>]+)>', list_unsub)
            if urls:
                return urls[0]

        # Search body for unsubscribe link
        body = ""
        payload = message.get("payload", {})
        if "body" in payload and payload["body"].get("data"):
            import base64
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
        else:
            for part in payload.get("parts", []):
                if part.get("mimeType") in ["text/plain", "text/html"]:
                    if "body" in part and part["body"].get("data"):
                        import base64
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                        break

        # Look for unsubscribe links in body
        patterns = [
            r'href=["\']?(https?://[^"\'>\s]*unsubscribe[^"\'>\s]*)["\']?',
            r'(https?://[^\s<>"]+unsubscribe[^\s<>"]*)',
            r'href=["\']?(https?://[^"\'>\s]*opt-out[^"\'>\s]*)["\']?',
        ]
        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    @mcp.tool()
    def setup_subscription_labels() -> Dict[str, Any]:
        """
        Create labels for managing subscriptions.

        Creates:
        - Subscription/Review - Newly discovered subscriptions
        - Subscription/Retained - Subscriptions you want to keep
        - Subscription/Unsubscribed - Processed subscriptions

        Returns:
            Dict[str, Any]: Result with created labels
        """
        credentials = get_credentials()
        if not credentials:
            return {"success": False, "error": "Not authenticated"}

        try:
            service = get_gmail_service(credentials)

            labels_to_create = [
                {"name": "Subscription/Review", "color": {"backgroundColor": "#ffad47", "textColor": "#000000"}},
                {"name": "Subscription/Retained", "color": {"backgroundColor": "#16a765", "textColor": "#ffffff"}},
                {"name": "Subscription/Unsubscribed", "color": {"backgroundColor": "#cccccc", "textColor": "#000000"}},
            ]

            # Get existing labels
            existing = service.users().labels().list(userId="me").execute()
            existing_names = {l["name"]: l for l in existing.get("labels", [])}

            created = []
            already_exists = []

            for label_def in labels_to_create:
                if label_def["name"] in existing_names:
                    already_exists.append(label_def["name"])
                else:
                    body = {
                        "name": label_def["name"],
                        "labelListVisibility": "labelShow",
                        "messageListVisibility": "show"
                    }
                    if "color" in label_def:
                        body["color"] = label_def["color"]

                    result = service.users().labels().create(userId="me", body=body).execute()
                    created.append(result["name"])

            return {
                "success": True,
                "created": created,
                "already_existed": already_exists,
                "message": f"Created {len(created)} labels, {len(already_exists)} already existed"
            }

        except Exception as e:
            logger.error(f"Failed to setup subscription labels: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def find_subscription_emails(max_results: int = 100, unlabeled_only: bool = True) -> Dict[str, Any]:
        """
        Find emails that appear to be subscriptions/newsletters.

        Args:
            max_results (int): Maximum subscriptions to find (default: 100)
            unlabeled_only (bool): Only find subscriptions not yet labeled (default: True)

        Returns:
            Dict[str, Any]: List of senders with subscription characteristics
        """
        credentials = get_credentials()
        if not credentials:
            return {"success": False, "error": "Not authenticated"}

        try:
            service = get_gmail_service(credentials)

            # Search for emails with unsubscribe indicators
            query = "has:unsubscribe"
            if unlabeled_only:
                query += " -label:Subscription/Review -label:Subscription/Retained -label:Subscription/Unsubscribed"

            # Fetch messages
            all_messages = []
            page_token = None

            while len(all_messages) < max_results * 3:  # Fetch more to group by sender
                request_params = {
                    "userId": "me",
                    "q": query,
                    "maxResults": min(100, max_results * 3 - len(all_messages))
                }
                if page_token:
                    request_params["pageToken"] = page_token

                result = service.users().messages().list(**request_params).execute()
                all_messages.extend(result.get("messages", []))

                page_token = result.get("nextPageToken")
                if not page_token:
                    break

            # Group by sender
            sender_info = defaultdict(lambda: {"count": 0, "subjects": [], "message_ids": []})

            for msg_ref in all_messages[:max_results * 3]:
                msg = service.users().messages().get(
                    userId="me",
                    id=msg_ref["id"],
                    format="metadata",
                    metadataHeaders=["From", "Subject", "List-Unsubscribe"]
                ).execute()

                headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
                from_header = headers.get("from", "")
                subject = headers.get("subject", "")

                # Extract email from "Name <email>" format
                email_match = re.search(r'<([^>]+)>', from_header)
                sender_email = email_match.group(1).lower() if email_match else from_header.lower()

                if sender_email:
                    sender_info[sender_email]["count"] += 1
                    if len(sender_info[sender_email]["subjects"]) < 3:
                        sender_info[sender_email]["subjects"].append(subject)
                    if len(sender_info[sender_email]["message_ids"]) < 5:
                        sender_info[sender_email]["message_ids"].append(msg_ref["id"])
                    sender_info[sender_email]["from_name"] = from_header.split('<')[0].strip().strip('"')
                    if headers.get("list-unsubscribe"):
                        sender_info[sender_email]["has_list_unsubscribe"] = True

            # Convert to list and sort by count
            subscriptions = []
            for email, info in sender_info.items():
                # Estimate frequency
                if info["count"] >= 20:
                    frequency = "daily"
                elif info["count"] >= 4:
                    frequency = "weekly"
                else:
                    frequency = "occasional"

                subscriptions.append({
                    "email": email,
                    "name": info.get("from_name", email),
                    "count": info["count"],
                    "frequency": frequency,
                    "sample_subjects": info["subjects"],
                    "has_list_unsubscribe": info.get("has_list_unsubscribe", False),
                    "sample_message_id": info["message_ids"][0] if info["message_ids"] else None
                })

            subscriptions.sort(key=lambda x: x["count"], reverse=True)
            subscriptions = subscriptions[:max_results]

            return {
                "success": True,
                "subscriptions": subscriptions,
                "total_found": len(subscriptions),
                "message": f"Found {len(subscriptions)} subscription senders"
            }

        except Exception as e:
            logger.error(f"Failed to find subscriptions: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def get_unsubscribe_link(email_id: str) -> Dict[str, Any]:
        """
        Get the unsubscribe link from a specific email.

        Args:
            email_id (str): ID of the email

        Returns:
            Dict[str, Any]: Unsubscribe link if found
        """
        credentials = get_credentials()
        if not credentials:
            return {"success": False, "error": "Not authenticated"}

        try:
            service = get_gmail_service(credentials)

            message = service.users().messages().get(
                userId="me",
                id=email_id,
                format="full"
            ).execute()

            unsub_link = _extract_unsubscribe_link(message)

            if unsub_link:
                return {
                    "success": True,
                    "unsubscribe_link": unsub_link,
                    "message": "Click the link to unsubscribe. Do not share this link."
                }
            else:
                return {
                    "success": False,
                    "error": "No unsubscribe link found in this email"
                }

        except Exception as e:
            logger.error(f"Failed to get unsubscribe link: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def unsubscribe_and_cleanup(
        from_address: str,
        archive_existing: bool = True,
        create_filter: bool = True
    ) -> Dict[str, Any]:
        """
        Get unsubscribe link for a sender and optionally clean up existing emails.

        Args:
            from_address (str): Email address of the sender to unsubscribe from
            archive_existing (bool): Archive all existing emails from this sender (default: True)
            create_filter (bool): Create filter to auto-trash future emails (default: True)

        Returns:
            Dict[str, Any]: Unsubscribe link and cleanup results

        Note: You must manually click the unsubscribe link - automatic unsubscription
        is not supported as it could be used maliciously.
        """
        credentials = get_credentials()
        if not credentials:
            return {"success": False, "error": "Not authenticated"}

        try:
            service = get_gmail_service(credentials)

            # Find a recent email from this sender to get unsubscribe link
            search_result = service.users().messages().list(
                userId="me",
                q=f"from:{from_address}",
                maxResults=1
            ).execute()

            unsubscribe_link = None
            if search_result.get("messages"):
                msg = service.users().messages().get(
                    userId="me",
                    id=search_result["messages"][0]["id"],
                    format="full"
                ).execute()
                unsubscribe_link = _extract_unsubscribe_link(msg)

            result = {
                "success": True,
                "from_address": from_address,
                "unsubscribe_link": unsubscribe_link
            }

            # Archive existing emails
            if archive_existing:
                # Get all messages from this sender
                all_ids = []
                page_token = None
                while True:
                    search = service.users().messages().list(
                        userId="me",
                        q=f"from:{from_address} in:inbox",
                        maxResults=100,
                        pageToken=page_token
                    ).execute()
                    all_ids.extend([m["id"] for m in search.get("messages", [])])
                    page_token = search.get("nextPageToken")
                    if not page_token or len(all_ids) >= 500:
                        break

                if all_ids:
                    # Archive (remove INBOX label)
                    service.users().messages().batchModify(
                        userId="me",
                        body={"ids": all_ids, "removeLabelIds": ["INBOX"]}
                    ).execute()
                    result["emails_archived"] = len(all_ids)

            # Create filter to trash future emails
            if create_filter:
                filter_body = {
                    "criteria": {"from": from_address},
                    "action": {"removeLabelIds": ["INBOX"], "addLabelIds": ["TRASH"]}
                }
                try:
                    service.users().settings().filters().create(
                        userId="me",
                        body=filter_body
                    ).execute()
                    result["filter_created"] = True
                except Exception as filter_err:
                    result["filter_error"] = str(filter_err)

            # Add label
            try:
                labels = service.users().labels().list(userId="me").execute()
                unsub_label = next(
                    (l for l in labels.get("labels", []) if l["name"] == "Subscription/Unsubscribed"),
                    None
                )
                if unsub_label and search_result.get("messages"):
                    service.users().messages().modify(
                        userId="me",
                        id=search_result["messages"][0]["id"],
                        body={"addLabelIds": [unsub_label["id"]]}
                    ).execute()
            except Exception:
                pass  # Label is optional

            if unsubscribe_link:
                result["message"] = "Click the unsubscribe link to complete. Future emails will be auto-trashed."
            else:
                result["message"] = "No unsubscribe link found, but filter created to trash future emails."

            return result

        except Exception as e:
            logger.error(f"Failed to process unsubscribe: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def create_subscription_filter(
        from_address: str,
        action: str = "retain",
        skip_inbox: bool = True,
        retention_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a filter for a subscription sender.

        Args:
            from_address (str): Email address of the sender
            action (str): "retain" (keep with label) or "junk" (trash)
            skip_inbox (bool): Skip inbox for retained subscriptions (default: True)
            retention_days (int, optional): Apply retention label (7, 30, 90, 180, 365)

        Returns:
            Dict[str, Any]: Filter creation result
        """
        credentials = get_credentials()
        if not credentials:
            return {"success": False, "error": "Not authenticated"}

        if action not in ["retain", "junk"]:
            return {"success": False, "error": "Action must be 'retain' or 'junk'"}

        try:
            service = get_gmail_service(credentials)

            # Get labels
            labels = service.users().labels().list(userId="me").execute()
            label_map = {l["name"]: l["id"] for l in labels.get("labels", [])}

            filter_body = {
                "criteria": {"from": from_address},
                "action": {}
            }

            if action == "junk":
                filter_body["action"]["addLabelIds"] = ["TRASH"]
                filter_body["action"]["removeLabelIds"] = ["INBOX"]
                label_name = "Subscription/Unsubscribed"
            else:
                # Retain
                add_labels = []
                remove_labels = []

                if "Subscription/Retained" in label_map:
                    add_labels.append(label_map["Subscription/Retained"])

                if retention_days:
                    retention_label_map = {
                        7: "Retention/7-days",
                        30: "Retention/30-days",
                        90: "Retention/90-days",
                        180: "Retention/6-months",
                        365: "Retention/1-year"
                    }
                    retention_label = retention_label_map.get(retention_days)
                    if retention_label and retention_label in label_map:
                        add_labels.append(label_map[retention_label])

                if skip_inbox:
                    remove_labels.append("INBOX")

                if add_labels:
                    filter_body["action"]["addLabelIds"] = add_labels
                if remove_labels:
                    filter_body["action"]["removeLabelIds"] = remove_labels

                label_name = "Subscription/Retained"

            # Create the filter
            result = service.users().settings().filters().create(
                userId="me",
                body=filter_body
            ).execute()

            return {
                "success": True,
                "filter_id": result.get("id"),
                "from_address": from_address,
                "action": action,
                "skip_inbox": skip_inbox,
                "retention_days": retention_days,
                "message": f"Filter created to {action} emails from {from_address}"
            }

        except Exception as e:
            logger.error(f"Failed to create subscription filter: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def mark_sender_as_junk(from_address: str, report_spam: bool = False) -> Dict[str, Any]:
        """
        Mark a sender as junk - creates filter to trash and optionally reports as spam.

        Args:
            from_address (str): Email address of the junk sender
            report_spam (bool): Also report existing emails as spam (default: False)

        Returns:
            Dict[str, Any]: Result of the operation
        """
        credentials = get_credentials()
        if not credentials:
            return {"success": False, "error": "Not authenticated"}

        try:
            service = get_gmail_service(credentials)

            result = {
                "success": True,
                "from_address": from_address
            }

            # Create filter to trash future emails
            filter_body = {
                "criteria": {"from": from_address},
                "action": {"addLabelIds": ["TRASH"], "removeLabelIds": ["INBOX"]}
            }
            try:
                service.users().settings().filters().create(
                    userId="me",
                    body=filter_body
                ).execute()
                result["filter_created"] = True
            except Exception as e:
                result["filter_error"] = str(e)

            # Find and trash/spam existing emails
            all_ids = []
            page_token = None
            while True:
                search = service.users().messages().list(
                    userId="me",
                    q=f"from:{from_address}",
                    maxResults=100,
                    pageToken=page_token
                ).execute()
                all_ids.extend([m["id"] for m in search.get("messages", [])])
                page_token = search.get("nextPageToken")
                if not page_token or len(all_ids) >= 500:
                    break

            if all_ids:
                if report_spam:
                    # Move to spam
                    service.users().messages().batchModify(
                        userId="me",
                        body={"ids": all_ids, "addLabelIds": ["SPAM"], "removeLabelIds": ["INBOX"]}
                    ).execute()
                    result["emails_marked_spam"] = len(all_ids)
                else:
                    # Move to trash
                    service.users().messages().batchModify(
                        userId="me",
                        body={"ids": all_ids, "addLabelIds": ["TRASH"], "removeLabelIds": ["INBOX"]}
                    ).execute()
                    result["emails_trashed"] = len(all_ids)

            result["message"] = f"Sender marked as junk. {len(all_ids)} emails processed."
            return result

        except Exception as e:
            logger.error(f"Failed to mark sender as junk: {e}")
            return {"success": False, "error": str(e)}

    logger.info("Subscription tools registered successfully")
