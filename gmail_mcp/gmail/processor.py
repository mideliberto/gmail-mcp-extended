"""
Email Processing Module

This module provides tools for processing emails, including parsing, thread analysis,
sender history collection, and metadata extraction.
"""

import base64
import re
import email
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timezone
import logging

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.auth.oauth import get_credentials
from gmail_mcp.mcp.schemas import (
    EmailMetadata, 
    EmailContent, 
    ThreadInfo as Thread, 
    SenderInfo as Sender
)

# Get logger
logger = get_logger(__name__)


def parse_email_message(message: Dict[str, Any]) -> Tuple[EmailMetadata, EmailContent]:
    """
    Parse an email message from the Gmail API.
    
    Args:
        message (Dict[str, Any]): The Gmail API message object.
        
    Returns:
        Tuple[EmailMetadata, EmailContent]: The parsed email metadata and content.
    """
    # Extract headers
    headers = {}
    for header in message["payload"]["headers"]:
        headers[header["name"].lower()] = header["value"]
    
    # Extract basic metadata
    subject = headers.get("subject", "No Subject")
    
    # Parse from field
    from_field = headers.get("from", "")
    from_name, from_email = parseaddr(from_field)
    
    # Decode from_name if needed
    if from_name:
        try:
            decoded_parts = []
            for part, encoding in decode_header(from_name):
                if isinstance(part, bytes):
                    decoded_parts.append(part.decode(encoding or "utf-8", errors="replace"))
                else:
                    decoded_parts.append(part)
            from_name = "".join(decoded_parts)
        except Exception as e:
            logger.warning(f"Failed to decode from_name: {e}")
    
    # Parse to field
    to_field = headers.get("to", "")
    to_list = []
    if to_field:
        for addr in to_field.split(","):
            _, email_addr = parseaddr(addr.strip())
            if email_addr:
                to_list.append(email_addr)
    
    # Parse cc field
    cc_field = headers.get("cc", "")
    cc_list = []
    if cc_field:
        for addr in cc_field.split(","):
            _, email_addr = parseaddr(addr.strip())
            if email_addr:
                cc_list.append(email_addr)
    
    # Parse date
    date_str = headers.get("date", "")
    date = datetime.now(timezone.utc)  # Default to now if parsing fails
    if date_str:
        try:
            date = parsedate_to_datetime(date_str)
            # Ensure timezone-aware (some emails have naive datetimes)
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
        except Exception as e:
            logger.warning(f"Failed to parse date: {e}")
    
    # Check for attachments
    has_attachments = False
    if "parts" in message["payload"]:
        for part in message["payload"]["parts"]:
            if part.get("filename"):
                has_attachments = True
                break
    
    # Create metadata object
    metadata = EmailMetadata(
        id=message["id"],
        thread_id=message["threadId"],
        subject=subject,
        from_email=from_email,
        from_name=from_name if from_name else "",
        to=to_list,
        cc=cc_list if cc_list else [],
        date=date,
        labels=message.get("labelIds", []),
        has_attachments=has_attachments
    )
    
    # Extract content
    content = extract_content(message["payload"])
    
    return metadata, content


def extract_content(payload: Dict[str, Any]) -> EmailContent:
    """
    Extract content from an email payload.
    
    Args:
        payload (Dict[str, Any]): The email payload.
        
    Returns:
        EmailContent: The extracted email content.
    """
    plain_text = ""
    html = None
    attachments = []
    
    def extract_body(part):
        """
        Extract body from a message part.
        
        Args:
            part (Dict[str, Any]): The message part.
            
        Returns:
            Tuple[str, str]: The plain text and HTML content.
        """
        nonlocal plain_text, html, attachments
        
        # Check if this part has a filename (attachment)
        if part.get("filename"):
            attachments.append({
                "filename": part["filename"],
                "mimeType": part["mimeType"],
                "size": len(part.get("body", {}).get("data", "")),
                "part_id": part.get("partId")
            })
            return
        
        # Check if this part has subparts
        if "parts" in part:
            for subpart in part["parts"]:
                extract_body(subpart)
            return
        
        # Extract body data
        body_data = part.get("body", {}).get("data", "")
        if not body_data:
            return
        
        # Decode body data
        try:
            decoded_data = base64.urlsafe_b64decode(body_data).decode("utf-8")
        except Exception as e:
            logger.warning(f"Failed to decode body data: {e}")
            return
        
        # Store based on mime type
        mime_type = part.get("mimeType", "")
        if mime_type == "text/plain":
            plain_text = decoded_data
        elif mime_type == "text/html":
            html = decoded_data
            # If we have HTML but no plain text, extract text from HTML
            if not plain_text:
                plain_text = extract_text_from_html(decoded_data)
    
    # Start extraction
    extract_body(payload)
    
    # If we still don't have plain text but have a body, try to decode it
    if not plain_text and "body" in payload and "data" in payload["body"]:
        try:
            plain_text = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
        except Exception as e:
            logger.warning(f"Failed to decode body data: {e}")
    
    # Create content object
    content = EmailContent(
        plain_text=plain_text,
        html=html,
        attachments=attachments
    )
    
    return content


def extract_text_from_html(html_content: str) -> str:
    """
    Extract plain text from HTML content.
    
    Args:
        html_content (str): The HTML content.
        
    Returns:
        str: The extracted plain text.
    """
    # Simple regex-based extraction
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', html_content)
    
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    
    # Replace HTML entities
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'&#39;', "'", text)
    
    return text.strip()


def analyze_thread(thread_id: str) -> Optional[Thread]:
    """
    Analyze a thread to extract information.
    
    Args:
        thread_id (str): The ID of the thread to analyze.
        
    Returns:
        Optional[Thread]: The thread information, or None if the thread could not be analyzed.
    """
    credentials = get_credentials()
    
    if not credentials:
        logger.error("Not authenticated")
        return None
    
    try:
        # Build the Gmail API service
        service = build("gmail", "v1", credentials=credentials)
        
        # Get the thread
        thread = service.users().threads().get(userId="me", id=thread_id).execute()
        
        # Extract basic information
        messages = thread.get("messages", [])
        
        if not messages:
            logger.warning(f"Thread {thread_id} has no messages")
            return None
        
        # Extract subject from the first message
        subject = "No Subject"
        for header in messages[0]["payload"]["headers"]:
            if header["name"].lower() == "subject":
                subject = header["value"]
                break
        
        # Extract participants
        participants = set()
        message_ids = []
        last_message_date = None
        
        for message in messages:
            message_ids.append(message["id"])
            
            # Extract headers
            headers = {}
            for header in message["payload"]["headers"]:
                headers[header["name"].lower()] = header["value"]
            
            # Extract participants from from, to, and cc fields
            for field in ["from", "to", "cc"]:
                if field in headers:
                    for addr in headers[field].split(","):
                        name, email_addr = parseaddr(addr.strip())
                        if email_addr:
                            participants.add(email_addr)
            
            # Extract date
            date_str = headers.get("date", "")
            if date_str:
                try:
                    date = parsedate_to_datetime(date_str)
                    # Ensure timezone-aware (some emails have naive datetimes)
                    if date.tzinfo is None:
                        date = date.replace(tzinfo=timezone.utc)
                    if not last_message_date or date > last_message_date:
                        last_message_date = date
                except Exception as e:
                    logger.warning(f"Failed to parse date: {e}")
        
        # Create thread object
        thread_obj = Thread(
            id=thread_id,
            subject=subject,
            participants=[{"email": p} for p in participants],
            last_message_date=last_message_date or datetime.now(timezone.utc),
            message_count=len(messages)
        )
        
        return thread_obj
    
    except HttpError as error:
        logger.error(f"Failed to analyze thread: {error}")
        return None


def get_sender_history(sender_email: str) -> Optional[Sender]:
    """
    Get the history of a sender.
    
    Args:
        sender_email (str): The email address of the sender.
        
    Returns:
        Optional[Sender]: The sender information, or None if the sender could not be analyzed.
    """
    credentials = get_credentials()
    
    if not credentials:
        logger.error("Not authenticated")
        return None
    
    try:
        # Build the Gmail API service
        service = build("gmail", "v1", credentials=credentials)
        
        # Search for messages from the sender
        query = f"from:{sender_email}"
        result = service.users().messages().list(userId="me", q=query, maxResults=100).execute()
        
        messages = result.get("messages", [])
        
        if not messages:
            # No messages found
            return Sender(
                email=sender_email,
                name="",
                message_count=0
            )
        
        # Extract metadata from messages
        message_metadata = []
        sender_name = ""
        
        for message_info in messages:
            message = service.users().messages().get(userId="me", id=message_info["id"]).execute()
            metadata = extract_email_metadata(message)
            message_metadata.append(metadata)
            
            # Get sender name from the first message
            if not sender_name and metadata.from_name:
                sender_name = metadata.from_name
        
        # Sort by date
        message_metadata.sort(key=lambda x: x.date)
        
        # Get first and last message dates
        first_metadata = message_metadata[0]
        last_metadata = message_metadata[-1]
        
        # Extract common topics
        # This is a simple implementation that just counts words in subjects
        word_counts = {}
        for metadata in message_metadata:
            # Split subject into words
            words = re.findall(r'\b\w+\b', metadata.subject.lower())
            for word in words:
                # Skip common words
                if word in ["re", "fw", "fwd", "the", "and", "or", "to", "from", "for", "in", "on", "at", "with", "by"]:
                    continue
                word_counts[word] = word_counts.get(word, 0) + 1
        
        # Get top topics
        topics = []
        for word, count in sorted(word_counts.items(), key=lambda x: x[1], reverse=True):
            if count >= 2 and len(topics) < 5:  # At least 2 occurrences, max 5 topics
                topics.append(word)
        
        # Create sender object
        sender = Sender(
            email=sender_email,
            name=sender_name,
            message_count=len(messages),
            first_message_date=first_metadata.date,
            last_message_date=last_metadata.date,
            common_topics=topics
        )
        
        return sender
    
    except HttpError as error:
        logger.error(f"Failed to get sender history: {error}")
        return None


def extract_email_metadata(message: Dict[str, Any]) -> EmailMetadata:
    """
    Extract metadata from an email message.
    
    Args:
        message (Dict[str, Any]): The Gmail API message object.
        
    Returns:
        EmailMetadata: The extracted email metadata.
    """
    metadata, _ = parse_email_message(message)
    return metadata


def extract_entities(text: str) -> Dict[str, List[str]]:
    """
    Extract entities from text using simple pattern matching.
    
    This function identifies common entities like dates, times, phone numbers,
    email addresses, URLs, and potential action items in the text.
    
    Args:
        text (str): The text to extract entities from.
        
    Returns:
        Dict[str, List[str]]: A dictionary of entity types and their values.
    """
    entities = {
        "dates": [],
        "times": [],
        "phone_numbers": [],
        "email_addresses": [],
        "urls": [],
        "action_items": []
    }
    
    # Extract dates (simple patterns like MM/DD/YYYY, DD/MM/YYYY, Month DD, YYYY)
    date_patterns = [
        r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',  # MM/DD/YYYY or DD/MM/YYYY
        r'\b\d{1,2}-\d{1,2}-\d{2,4}\b',  # MM-DD-YYYY or DD-MM-YYYY
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}(?:st|nd|rd|th)?,? \d{2,4}\b',  # Month DD, YYYY
        r'\b\d{1,2}(?:st|nd|rd|th)? (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*,? \d{2,4}\b',  # DD Month, YYYY
        r'\b(?:tomorrow|today|yesterday|next (?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)|this (?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b'  # Relative dates
    ]
    
    for pattern in date_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        entities["dates"].extend(matches)
    
    # Extract times
    time_patterns = [
        r'\b\d{1,2}:\d{2}\s*(?:am|pm)?\b',  # HH:MM am/pm
        r'\b\d{1,2}\s*(?:am|pm)\b',  # HH am/pm
        r'\b\d{1,2}:\d{2}\s*(?:hrs|hours)\b',  # 24-hour format
        r'\b(?:noon|midnight)\b'  # Special times
    ]
    
    for pattern in time_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        entities["times"].extend(matches)
    
    # Extract phone numbers
    phone_patterns = [
        r'\b\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',  # International format
        r'\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',  # US format (123) 456-7890
        r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b'  # Simple format 123-456-7890
    ]
    
    for pattern in phone_patterns:
        matches = re.findall(pattern, text)
        entities["phone_numbers"].extend(matches)
    
    # Extract email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    entities["email_addresses"] = re.findall(email_pattern, text)
    
    # Extract URLs
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    entities["urls"] = re.findall(url_pattern, text)
    
    # Extract potential action items
    action_patterns = [
        r'(?:please|kindly|could you|can you|would you).*?(?:\?|\.)',  # Requests
        r'(?:need to|must|should|have to).*?(?:\.|$)',  # Obligations
        r'(?:let me know|confirm|update me|get back to me).*?(?:\.|$)',  # Follow-ups
        r'(?:deadline|due date|by the end of|no later than).*?(?:\.|$)'  # Deadlines
    ]
    
    for pattern in action_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        # Clean up the matches
        cleaned_matches = [match.strip() for match in matches if len(match.strip()) > 10]
        entities["action_items"].extend(cleaned_matches)
    
    # Remove duplicates
    for entity_type in entities:
        entities[entity_type] = list(set(entities[entity_type]))
    
    return entities


def analyze_communication_patterns(sender_email: str, recipient_email: str) -> Dict[str, Any]:
    """
    Analyze communication patterns between a sender and recipient.
    
    This function examines the history of emails between two email addresses
    to identify patterns in their communication style, frequency, and content.
    
    Args:
        sender_email (str): The email address of the sender.
        recipient_email (str): The email address of the recipient.
        
    Returns:
        Dict[str, Any]: Analysis of communication patterns.
    """
    credentials = get_credentials()
    
    if not credentials:
        logger.error("Not authenticated")
        return {"error": "Not authenticated"}
    
    try:
        # Build the Gmail API service
        service = build("gmail", "v1", credentials=credentials)
        
        # Search for messages between the sender and recipient
        query = f"from:{sender_email} to:{recipient_email} OR from:{recipient_email} to:{sender_email}"
        result = service.users().messages().list(userId="me", q=query, maxResults=50).execute()
        
        messages = result.get("messages", [])
        
        if not messages:
            return {
                "message_count": 0,
                "communication_exists": False,
                "analysis": "No communication history found between these email addresses."
            }
        
        # Extract metadata and content from messages
        conversation_data = []
        
        for message_info in messages:
            message = service.users().messages().get(userId="me", id=message_info["id"], format="full").execute()
            metadata, content = parse_email_message(message)
            
            # Determine direction (sent or received)
            direction = "sent" if metadata.from_email == recipient_email else "received"
            
            conversation_data.append({
                "id": metadata.id,
                "date": metadata.date,
                "subject": metadata.subject,
                "direction": direction,
                "content": content.plain_text,
                "length": len(content.plain_text)
            })
        
        # Sort by date
        conversation_data.sort(key=lambda x: x["date"])
        
        # Analyze communication frequency
        if len(conversation_data) >= 2:
            first_date = conversation_data[0]["date"]
            last_date = conversation_data[-1]["date"]
            date_diff = (last_date - first_date).days
            
            if date_diff > 0:
                frequency = len(conversation_data) / date_diff
                frequency_description = "daily" if frequency >= 1 else "weekly" if frequency >= 0.14 else "monthly" if frequency >= 0.03 else "infrequent"
            else:
                frequency_description = "same day"
        else:
            frequency_description = "one-time"
        
        # Analyze response times
        response_times = []
        for i in range(1, len(conversation_data)):
            if conversation_data[i]["direction"] != conversation_data[i-1]["direction"]:
                response_time = (conversation_data[i]["date"] - conversation_data[i-1]["date"]).total_seconds() / 3600  # hours
                response_times.append(response_time)
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else None
        
        # Analyze message lengths
        sent_lengths = [msg["length"] for msg in conversation_data if msg["direction"] == "sent"]
        received_lengths = [msg["length"] for msg in conversation_data if msg["direction"] == "received"]
        
        avg_sent_length = sum(sent_lengths) / len(sent_lengths) if sent_lengths else 0
        avg_received_length = sum(received_lengths) / len(received_lengths) if received_lengths else 0
        
        # Analyze formality (simple heuristic based on greetings and sign-offs)
        formality_markers = {
            "formal": ["dear", "sincerely", "regards", "respectfully", "thank you for your", "please find", "i am writing to"],
            "informal": ["hey", "hi", "hello", "thanks", "cheers", "talk soon", "take care", "best"]
        }
        
        formality_scores = {"formal": 0, "informal": 0}
        
        for msg in conversation_data:
            text = msg["content"].lower()
            for style, markers in formality_markers.items():
                for marker in markers:
                    if marker in text:
                        formality_scores[style] += 1
        
        formality = "formal" if formality_scores["formal"] > formality_scores["informal"] else "informal"
        
        # Extract common topics (simple keyword extraction)
        all_text = " ".join([msg["subject"] + " " + msg["content"] for msg in conversation_data])
        words = re.findall(r'\b\w+\b', all_text.lower())
        word_counts = {}
        
        for word in words:
            # Skip common words and short words
            if word in ["re", "fw", "fwd", "the", "and", "or", "to", "from", "for", "in", "on", "at", "with", "by", "a", "an", "is", "are", "was", "were"] or len(word) < 3:
                continue
            word_counts[word] = word_counts.get(word, 0) + 1
        
        # Get top topics
        topics = []
        for word, count in sorted(word_counts.items(), key=lambda x: x[1], reverse=True):
            if count >= 3 and len(topics) < 5:  # At least 3 occurrences, max 5 topics
                topics.append(word)
        
        return {
            "message_count": len(conversation_data),
            "communication_exists": True,
            "first_contact": conversation_data[0]["date"].isoformat(),
            "last_contact": conversation_data[-1]["date"].isoformat(),
            "frequency": frequency_description,
            "avg_response_time_hours": avg_response_time,
            "communication_style": {
                "formality": formality,
                "avg_message_length": {
                    "sent": avg_sent_length,
                    "received": avg_received_length
                }
            },
            "common_topics": topics
        }
    
    except Exception as e:
        logger.error(f"Failed to analyze communication patterns: {e}")
        return {"error": f"Failed to analyze communication patterns: {e}"}


def find_related_emails(email_id: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Find emails related to the given email based on subject, sender, and content.
    
    This function searches for emails that are related to the specified email
    by matching subject keywords, the same sender, or similar content.
    
    Args:
        email_id (str): The ID of the email to find related emails for.
        max_results (int, optional): Maximum number of related emails to return. Defaults to 10.
        
    Returns:
        List[Dict[str, Any]]: List of related emails with metadata.
    """
    credentials = get_credentials()
    
    if not credentials:
        logger.error("Not authenticated")
        return []
    
    try:
        # Build the Gmail API service
        service = build("gmail", "v1", credentials=credentials)
        
        # Get the original email
        message = service.users().messages().get(userId="me", id=email_id, format="full").execute()
        metadata, content = parse_email_message(message)
        
        # Extract keywords from subject (remove common words)
        subject_words = re.findall(r'\b\w+\b', metadata.subject.lower())
        subject_keywords = [word for word in subject_words if len(word) > 3 and word not in ["re", "fw", "fwd", "the", "and", "or", "to", "from", "for", "in", "on", "at", "with", "by", "a", "an", "is", "are", "was", "were"]]
        
        # Build search query
        search_queries = []
        
        # Add subject keywords to query
        if subject_keywords:
            subject_query = " OR ".join([f"subject:{keyword}" for keyword in subject_keywords[:3]])  # Limit to top 3 keywords
            search_queries.append(f"({subject_query})")
        
        # Add sender to query
        search_queries.append(f"from:{metadata.from_email}")
        
        # Combine queries
        query = " OR ".join(search_queries)
        
        # Exclude the original email
        query = f"({query}) -rfc822msgid:{email_id}"
        
        # Search for related emails
        result = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
        
        messages = result.get("messages", [])
        
        if not messages:
            return []
        
        # Extract metadata from related emails
        related_emails = []
        
        for message_info in messages:
            related_message = service.users().messages().get(userId="me", id=message_info["id"]).execute()
            related_metadata = extract_email_metadata(related_message)
            
            # Calculate simple relevance score
            relevance_score = 0
            
            # Score based on sender match
            if related_metadata.from_email == metadata.from_email:
                relevance_score += 3
            
            # Score based on subject keyword matches
            for keyword in subject_keywords:
                if keyword in related_metadata.subject.lower():
                    relevance_score += 1
            
            # Score based on recency (newer = higher score)
            days_old = (datetime.now(timezone.utc) - related_metadata.date).days
            recency_score = max(0, 5 - (days_old / 7))  # 5 points for current, decreasing by 1 per week
            relevance_score += recency_score
            
            related_emails.append({
                "id": related_metadata.id,
                "thread_id": related_metadata.thread_id,
                "subject": related_metadata.subject,
                "from": {
                    "email": related_metadata.from_email,
                    "name": related_metadata.from_name
                },
                "date": related_metadata.date.isoformat(),
                "relevance_score": round(relevance_score, 2)
            })
        
        # Sort by relevance score
        related_emails.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return related_emails
    
    except Exception as e:
        logger.error(f"Failed to find related emails: {e}")
        return [] 