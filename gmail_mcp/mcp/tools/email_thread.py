"""
Email Thread Tools Module

Handles thread/conversation view functionality for Gmail emails.
"""

import base64
from typing import Dict, Any, List, Optional

from mcp.server.fastmcp import FastMCP
from googleapiclient.errors import HttpError

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.utils.services import get_gmail_service
from gmail_mcp.auth.oauth import get_credentials

logger = get_logger(__name__)


def _extract_message_from_thread(msg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract message info from a thread message.

    Args:
        msg: Gmail API message object from threads().get()

    Returns:
        Dict with message details
    """
    headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}

    # Extract body
    body = ""
    payload = msg.get("payload", {})

    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                break
        # If no text/plain, try to find text in nested parts
        if not body:
            for part in payload["parts"]:
                if "parts" in part:
                    for subpart in part["parts"]:
                        if subpart.get("mimeType") == "text/plain" and "data" in subpart.get("body", {}):
                            body = base64.urlsafe_b64decode(subpart["body"]["data"]).decode("utf-8")
                            break
                    if body:
                        break
    elif "body" in payload and "data" in payload["body"]:
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

    return {
        "id": msg["id"],
        "from": headers.get("from", "Unknown"),
        "to": headers.get("to", "Unknown"),
        "cc": headers.get("cc", ""),
        "date": headers.get("date", "Unknown"),
        "subject": headers.get("subject", "No Subject"),
        "snippet": msg.get("snippet", ""),
        "body": body,
        "labels": msg.get("labelIds", [])
    }


def setup_email_thread_tools(mcp: FastMCP) -> None:
    """Set up email thread tools on the FastMCP application."""

    @mcp.tool()
    def get_thread(thread_id: str) -> Dict[str, Any]:
        """
        Get a full email thread/conversation.

        This tool retrieves all messages in a thread, providing full
        conversation context for understanding email chains.

        Prerequisites:
        - The user must be authenticated. Check auth://status resource first.
        - You need a thread_id, which can be obtained from get_email() or list_emails()

        Args:
            thread_id (str): The ID of the thread to retrieve.

        Returns:
            Dict[str, Any]: The thread details including:
                - thread_id: Thread ID
                - subject: Thread subject (from first message)
                - message_count: Number of messages in thread
                - participants: List of unique email addresses in the thread
                - messages: List of message objects in chronological order, each with:
                    - id: Message ID
                    - from: Sender
                    - to: Recipients
                    - cc: CC recipients
                    - date: Message date
                    - subject: Message subject
                    - snippet: Short snippet
                    - body: Full message body
                    - labels: Message labels
                - thread_link: Direct link to the thread in Gmail web interface

        Example usage:
        1. Get an email: email = get_email(email_id="...")
        2. Get the thread: thread = get_thread(thread_id=email["thread_id"])
        3. Review full conversation context before replying
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)

            # Get the full thread with all messages
            thread = service.users().threads().get(
                userId="me",
                id=thread_id,
                format="full"
            ).execute()

            messages = thread.get("messages", [])

            if not messages:
                return {
                    "success": False,
                    "error": "Thread contains no messages."
                }

            # Extract all messages in chronological order (API returns them in order)
            extracted_messages = [_extract_message_from_thread(msg) for msg in messages]

            # Get unique participants
            participants = set()
            for msg in extracted_messages:
                # Parse email addresses from from/to/cc fields
                for field in ["from", "to", "cc"]:
                    value = msg.get(field, "")
                    if value:
                        # Split on comma for multiple recipients
                        for addr in value.split(","):
                            addr = addr.strip()
                            # Extract just the email if it's in "Name <email>" format
                            if "<" in addr and ">" in addr:
                                addr = addr[addr.index("<") + 1:addr.index(">")]
                            if addr and "@" in addr:
                                participants.add(addr.lower())

            # Get subject from first message
            subject = extracted_messages[0].get("subject", "No Subject") if extracted_messages else "No Subject"

            thread_link = f"https://mail.google.com/mail/u/0/#inbox/{thread_id}"

            return {
                "thread_id": thread_id,
                "subject": subject,
                "message_count": len(extracted_messages),
                "participants": sorted(list(participants)),
                "messages": extracted_messages,
                "thread_link": thread_link
            }

        except HttpError as error:
            logger.error(f"Failed to get thread: {error}")
            return {"success": False, "error": f"Failed to get thread: {error}"}

    @mcp.tool()
    def get_thread_summary(thread_id: str) -> Dict[str, Any]:
        """
        Get a condensed summary of an email thread.

        This tool provides a summarized view of long threads, showing:
        - The original message
        - Timeline of replies
        - The last 2-3 messages in full
        - Key participants

        Useful for quickly understanding long email chains without
        reading every message.

        Prerequisites:
        - The user must be authenticated.
        - You need a thread_id from get_email() or list_emails()

        Args:
            thread_id (str): The ID of the thread to summarize.

        Returns:
            Dict[str, Any]: The thread summary including:
                - thread_id: Thread ID
                - subject: Thread subject
                - message_count: Total messages in thread
                - participants: List of participants
                - original_message: The first message that started the thread
                - timeline: Brief timeline of intermediate messages (date, from, snippet)
                - recent_messages: The last 2-3 messages in full
                - thread_link: Direct link to the thread

        Example usage:
        1. Get a thread summary: summary = get_thread_summary(thread_id="...")
        2. Review original context and recent messages
        3. Use get_thread() if you need full details
        """
        credentials = get_credentials()

        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)

            # Get the full thread
            thread = service.users().threads().get(
                userId="me",
                id=thread_id,
                format="full"
            ).execute()

            messages = thread.get("messages", [])

            if not messages:
                return {
                    "success": False,
                    "error": "Thread contains no messages."
                }

            # Extract all messages
            extracted_messages = [_extract_message_from_thread(msg) for msg in messages]

            # Get unique participants
            participants = set()
            for msg in extracted_messages:
                for field in ["from", "to", "cc"]:
                    value = msg.get(field, "")
                    if value:
                        for addr in value.split(","):
                            addr = addr.strip()
                            if "<" in addr and ">" in addr:
                                addr = addr[addr.index("<") + 1:addr.index(">")]
                            if addr and "@" in addr:
                                participants.add(addr.lower())

            subject = extracted_messages[0].get("subject", "No Subject")
            thread_link = f"https://mail.google.com/mail/u/0/#inbox/{thread_id}"

            # Build the summary
            original_message = extracted_messages[0]

            # Timeline for middle messages (excluding first and last 2-3)
            timeline = []
            recent_count = min(3, len(extracted_messages) - 1)  # Last 2-3 messages, but not first
            middle_start = 1
            middle_end = len(extracted_messages) - recent_count

            for msg in extracted_messages[middle_start:middle_end]:
                timeline.append({
                    "date": msg["date"],
                    "from": msg["from"],
                    "snippet": msg["snippet"][:100] + "..." if len(msg.get("snippet", "")) > 100 else msg.get("snippet", "")
                })

            # Recent messages (last 2-3, full content)
            recent_messages = extracted_messages[-recent_count:] if recent_count > 0 else []

            return {
                "thread_id": thread_id,
                "subject": subject,
                "message_count": len(extracted_messages),
                "participants": sorted(list(participants)),
                "original_message": original_message,
                "timeline": timeline,
                "recent_messages": recent_messages,
                "thread_link": thread_link
            }

        except HttpError as error:
            logger.error(f"Failed to get thread summary: {error}")
            return {"success": False, "error": f"Failed to get thread summary: {error}"}
