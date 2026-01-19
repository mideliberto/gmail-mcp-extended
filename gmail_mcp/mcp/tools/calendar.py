"""
Calendar Tools Module

Handles Google Calendar operations: create, list, update, delete, suggest times, detect events.
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone

import dateutil.parser as parser

from mcp.server.fastmcp import FastMCP

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.utils.services import get_gmail_service, get_calendar_service
from gmail_mcp.auth.oauth import get_credentials
from gmail_mcp.gmail.processor import parse_email_message, extract_entities
from gmail_mcp.calendar.processor import (
    get_user_timezone,
    create_calendar_event_object,
    get_color_id_from_name
)

logger = get_logger(__name__)


def setup_calendar_tools(mcp: FastMCP) -> None:
    """Set up calendar tools on the FastMCP application."""

    @mcp.tool()
    def create_calendar_event(
        summary: str,
        start_time: str,
        end_time: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        color_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new event in the user's Google Calendar.

        This tool creates a new calendar event with the specified details.

        Prerequisites:
        - The user must be authenticated with Google Calendar access

        Args:
            summary (str): The title/summary of the event
            start_time (str): The start time of the event in ISO format (YYYY-MM-DDTHH:MM:SS) or simple date/time format ("5pm", "tomorrow 3pm")
            end_time (str, optional): The end time of the event. If not provided, you should ask the user for this information.
            description (str, optional): Description or notes for the event. If not provided, leave it blank.
            location (str, optional): Location of the event. If not provided, leave it blank.
            attendees (List[str], optional): List of email addresses of attendees. The current user will always be added automatically.
            color_name (str, optional): Color name for the event (e.g., "red", "blue", "green", "purple", "yellow", "orange")

        Returns:
            Dict[str, Any]: The result of the operation, including:
                - success: Whether the operation was successful
                - message: A message describing the result
                - event_id: The ID of the created event
                - event_link: Direct link to the event in Google Calendar
                - missing_info: List of missing information that should be asked from the user

        Example usage:
        1. Create a simple event:
           create_calendar_event(summary="Team Meeting", start_time="2023-12-01T14:00:00")

        2. Create a detailed event:
           create_calendar_event(
               summary="Project Kickoff",
               start_time="next monday at 10am",
               end_time="next monday at 11:30am",
               description="Initial meeting to discuss project scope",
               location="Conference Room A",
               attendees=["colleague@example.com", "manager@example.com"],
               color_name="blue"
           )
        """
        credentials = get_credentials()
        if not credentials:
            return {
                "success": False,
                "error": "Not authenticated. Please authenticate first.",
                "missing_info": []
            }

        try:
            service = get_calendar_service(credentials)

            if color_name:
                color_id = get_color_id_from_name(color_name)
            else:
                color_id = "1"

            event_body = create_calendar_event_object(
                summary=summary,
                start_time=start_time,
                end_time=end_time,
                description=description,
                location=location,
                attendees=attendees,
                color_id=color_id
            )

            if "error" in event_body:
                missing_info = []
                if not end_time:
                    missing_info.append("end_time")

                return {
                    "success": False,
                    "error": event_body["error"],
                    "parsed_start": event_body.get("parsed_start"),
                    "parsed_end": event_body.get("parsed_end"),
                    "current_datetime": event_body.get("current_datetime"),
                    "missing_info": missing_info
                }

            created_event = service.events().insert(calendarId="primary", body=event_body).execute()

            event_id = created_event.get("id", "")
            event_link = created_event.get("htmlLink", "")

            return {
                "success": True,
                "message": "Event created successfully.",
                "event_id": event_id,
                "event_link": event_link,
                "event_details": {
                    "summary": summary,
                    "start": event_body.get("start", {}),
                    "end": event_body.get("end", {}),
                    "timezone": event_body.get("_parsed", {}).get("timezone", "UTC"),
                    "all_day": event_body.get("_parsed", {}).get("all_day", False),
                    "current_datetime": event_body.get("_parsed", {}).get("current_datetime", "")
                },
                "missing_info": []
            }

        except Exception as e:
            logger.error(f"Failed to create calendar event: {e}")
            missing_info = []
            if not end_time:
                missing_info.append("end_time")

            return {
                "success": False,
                "error": f"Failed to create calendar event: {e}",
                "missing_info": missing_info
            }

    @mcp.tool()
    def detect_events_from_email(email_id: str) -> Dict[str, Any]:
        """
        Detect potential calendar events from an email.

        This tool analyzes an email to identify potential calendar events
        based on dates, times, and contextual clues.

        Prerequisites:
        - The user must be authenticated
        - You need an email ID from list_emails() or search_emails()

        Args:
            email_id (str): The ID of the email to analyze for events

        Returns:
            Dict[str, Any]: The detected events including:
                - success: Whether the operation was successful
                - events: List of potential events with details
                - email_link: Link to the original email

        Example usage:
        1. Get an email: email = get_email(email_id="...")
        2. Detect events: events = detect_events_from_email(email_id="...")
        3. Ask the user if they want to add the events to their calendar
        4. Ask the user for any missing information (end time, location, description, attendees)
        5. If confirmed, create the events using create_calendar_event()

        Important:
        - Always ask for user confirmation before creating calendar events
        - Always ask for missing information like end time, location, description, and attendees
        - Never use default values without user input
        - Always include the event_link when discussing events with the user
        """
        credentials = get_credentials()

        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_gmail_service(credentials)
            message = service.users().messages().get(userId="me", id=email_id, format="full").execute()
            metadata, content = parse_email_message(message)

            entities = extract_entities(content.plain_text)

            thread_id = message["threadId"]
            email_link = f"https://mail.google.com/mail/u/0/#inbox/{thread_id}/{email_id}"

            potential_events = []

            dates = entities.get("dates", [])
            times = entities.get("times", [])

            event_patterns = [
                r'(?i)(?:meeting|call|conference|appointment|event|webinar|seminar|workshop|session|interview)\s+(?:on|at|for)\s+([^.,:;!?]+)',
                r'(?i)(?:schedule|scheduled|plan|planning|organize|organizing|host|hosting)\s+(?:a|an)\s+([^.,:;!?]+)',
                r'(?i)(?:invite|invitation|inviting)\s+(?:you|everyone|all)\s+(?:to|for)\s+([^.,:;!?]+)'
            ]

            event_titles = []
            for pattern in event_patterns:
                matches = re.findall(pattern, content.plain_text)
                event_titles.extend(matches)

            parsed_datetimes = []

            datetime_patterns = [
                r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\s+(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?\b',
                r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{2,4}\s+(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?\b',
                r'\b(?:tomorrow|today|next\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))\s+(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?\b'
            ]

            for pattern in datetime_patterns:
                matches = re.findall(pattern, content.plain_text)
                for match in matches:
                    try:
                        dt = parser.parse(match)
                        parsed_datetimes.append(dt)
                    except (ValueError, TypeError):
                        pass

            if not parsed_datetimes and dates and times:
                for date_str in dates:
                    for time_str in times:
                        try:
                            dt = parser.parse(f"{date_str} {time_str}")
                            parsed_datetimes.append(dt)
                        except (ValueError, TypeError):
                            pass

            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            potential_attendees = list(set(re.findall(email_pattern, content.plain_text)))

            location_patterns = [
                r'(?i)(?:at|in|location|place|venue):\s*([^.,:;!?]+)',
                r'(?i)(?:at|in)\s+the\s+([^.,:;!?]+)',
                r'(?i)(?:meet|meeting)\s+(?:at|in)\s+([^.,:;!?]+)'
            ]

            potential_location = None
            for pattern in location_patterns:
                matches = re.findall(pattern, content.plain_text)
                if matches:
                    potential_location = matches[0].strip()
                    break

            for i, dt in enumerate(parsed_datetimes):
                end_dt = dt + timedelta(hours=1)

                title = f"Event from email"
                if i < len(event_titles):
                    title = event_titles[i]
                elif metadata.subject:
                    title = f"Re: {metadata.subject}"

                potential_events.append({
                    "summary": title,
                    "start_time": dt.isoformat(),
                    "end_time": end_dt.isoformat(),
                    "description": f"Detected from email: {metadata.subject}",
                    "location": potential_location,
                    "attendees": potential_attendees,
                    "confidence": "medium",
                    "source_text": content.plain_text[:200] + "..." if len(content.plain_text) > 200 else content.plain_text
                })

            return {
                "success": True,
                "events": potential_events,
                "email_id": email_id,
                "email_link": email_link,
                "subject": metadata.subject,
                "from": {
                    "email": metadata.from_email,
                    "name": metadata.from_name
                }
            }

        except Exception as e:
            logger.error(f"Failed to detect events from email: {e}")
            return {
                "success": False,
                "error": f"Failed to detect events from email: {e}"
            }

    @mcp.tool()
    def list_calendar_events(
        max_results: int = 10,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List events from the user's Google Calendar.

        This tool retrieves a list of upcoming events from the user's calendar.

        Prerequisites:
        - The user must be authenticated with Google Calendar access

        Args:
            max_results (int, optional): Maximum number of events to return. Defaults to 10.
            time_min (str, optional): Start time for the search in ISO format or natural language.
                                     Defaults to now.
            time_max (str, optional): End time for the search in ISO format or natural language.
                                     Defaults to unlimited.
            query (str, optional): Free text search terms to find events that match.

        Returns:
            Dict[str, Any]: The list of events including:
                - events: List of calendar events with details and links
                - next_page_token: Token for pagination (if applicable)

        Example usage:
        1. List upcoming events:
           list_calendar_events()

        2. List events for a specific time range:
           list_calendar_events(time_min="tomorrow", time_max="tomorrow at 11:59pm")

        3. Search for specific events:
           list_calendar_events(query="meeting")

        Important:
        - Always include the event_link when discussing specific events with the user
        - The event_link allows users to directly access their events in Google Calendar
        - When listing multiple events, include the event_link for each event
        """
        credentials = get_credentials()

        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_calendar_service(credentials)

            if not time_min:
                time_min_dt = datetime.now(timezone.utc)
            else:
                try:
                    time_min_dt = parser.parse(time_min, fuzzy=True)
                    if time_min_dt < datetime.now() and "year" not in time_min.lower():
                        if any(day in time_min.lower() for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
                            current_datetime = datetime.now()
                            days_ahead = (time_min_dt.weekday() - current_datetime.weekday()) % 7
                            if days_ahead == 0:
                                days_ahead = 7
                            time_min_dt = current_datetime + timedelta(days=days_ahead)
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Could not parse start time: {time_min}",
                        "message": "Please provide a clearer date and time format for the start time."
                    }

            time_min_formatted = time_min_dt.isoformat() + 'Z'

            time_max_formatted = None
            if time_max:
                try:
                    time_max_dt = parser.parse(time_max, fuzzy=True)
                    if time_max_dt < datetime.now() and "year" not in time_max.lower():
                        if any(day in time_max.lower() for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
                            current_datetime = datetime.now()
                            days_ahead = (time_max_dt.weekday() - current_datetime.weekday()) % 7
                            if days_ahead == 0:
                                days_ahead = 7
                            time_max_dt = current_datetime + timedelta(days=days_ahead)
                    time_max_formatted = time_max_dt.isoformat() + 'Z'
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Could not parse end time: {time_max}",
                        "message": "Please provide a clearer date and time format for the end time."
                    }

            user_timezone = get_user_timezone()

            params = {
                'calendarId': 'primary',
                'timeMin': time_min_formatted,
                'maxResults': max_results,
                'singleEvents': True,
                'orderBy': 'startTime',
                'timeZone': user_timezone
            }

            if time_max_formatted:
                params['timeMax'] = time_max_formatted

            if query:
                params['q'] = query

            events_result = service.events().list(**params).execute()
            events = events_result.get('items', [])

            processed_events = []
            for event in events:
                start = event.get('start', {})
                end = event.get('end', {})

                is_all_day = 'date' in start and 'date' in end

                if is_all_day:
                    start_display = start.get('date', '')
                    end_display = end.get('date', '')
                    time_display = "All day"
                else:
                    try:
                        start_dt = parser.parse(start.get('dateTime', ''))
                        end_dt = parser.parse(end.get('dateTime', ''))

                        start_display = start_dt.strftime("%Y-%m-%d %I:%M %p")
                        end_display = end_dt.strftime("%I:%M %p") if start_dt.date() == end_dt.date() else end_dt.strftime("%Y-%m-%d %I:%M %p")
                        time_display = f"{start_dt.strftime('%I:%M %p')} - {end_dt.strftime('%I:%M %p')}"
                    except Exception:
                        start_display = start.get('dateTime', '')
                        end_display = end.get('dateTime', '')
                        time_display = "Unknown time"

                event_id = event['id']
                event_link = f"https://calendar.google.com/calendar/event?eid={event_id}"

                processed_events.append({
                    "id": event_id,
                    "summary": event.get('summary', 'Untitled Event'),
                    "start": start,
                    "end": end,
                    "start_display": start_display,
                    "end_display": end_display,
                    "time_display": time_display,
                    "is_all_day": is_all_day,
                    "location": event.get('location', ''),
                    "description": event.get('description', ''),
                    "attendees": event.get('attendees', []),
                    "event_link": event_link
                })

            return {
                "success": True,
                "events": processed_events,
                "next_page_token": events_result.get('nextPageToken'),
                "timezone": user_timezone,
                "query_parameters": {
                    "time_min": time_min,
                    "time_max": time_max,
                    "query": query
                }
            }

        except Exception as e:
            logger.error(f"Failed to list calendar events: {e}")
            return {
                "success": False,
                "error": f"Failed to list calendar events: {e}"
            }

    @mcp.tool()
    def suggest_meeting_times(
        start_date: str,
        end_date: str,
        duration_minutes: int = 60,
        working_hours: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suggest available meeting times within a date range.

        This tool analyzes the user's calendar and suggests available time slots
        for scheduling meetings based on their existing calendar events.

        Prerequisites:
        - The user must be authenticated with Google Calendar access

        Args:
            start_date (str): The start date of the range to check (can be natural language like "tomorrow")
            end_date (str): The end date of the range to check (can be natural language like "next friday")
            duration_minutes (int, optional): The desired meeting duration in minutes. Defaults to 60.
            working_hours (str, optional): Working hours in format "9-17" (9am to 5pm). Defaults to 9am-5pm.

        Returns:
            Dict[str, Any]: The suggested meeting times including:
                - success: Whether the operation was successful
                - suggestions: List of suggested meeting times with formatted date/time
                - message: A message describing the result

        Example usage:
        1. Find meeting times for tomorrow:
           suggest_meeting_times(start_date="tomorrow", end_date="tomorrow")

        2. Find meeting times for next week with custom duration:
           suggest_meeting_times(
               start_date="next monday",
               end_date="next friday",
               duration_minutes=30
           )

        3. Find meeting times with custom working hours:
           suggest_meeting_times(
               start_date="tomorrow",
               end_date="friday",
               working_hours="10-16"
           )

        Important:
        - The tool respects the user's existing calendar events
        - Suggestions are limited to working hours (default 9am-5pm)
        - Weekends are excluded by default
        - The tool will return at most 10 suggestions
        """
        credentials = get_credentials()

        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}

        try:
            work_start_hour = 9
            work_end_hour = 17

            if working_hours:
                try:
                    hours_parts = working_hours.split("-")
                    if len(hours_parts) == 2:
                        work_start_hour = int(hours_parts[0])
                        work_end_hour = int(hours_parts[1])
                except Exception as e:
                    logger.warning(f"Failed to parse working hours: {e}")

            from gmail_mcp.calendar.processor import suggest_meeting_times as processor_suggest_times

            suggestions = processor_suggest_times(
                start_date=start_date,
                end_date=end_date,
                duration_minutes=duration_minutes,
                working_hours=(work_start_hour, work_end_hour)
            )

            if suggestions and "error" in suggestions[0]:
                return {
                    "success": False,
                    "error": suggestions[0]["error"],
                    "message": "Could not suggest meeting times. Please check your date range."
                }

            return {
                "success": True,
                "suggestions": suggestions,
                "message": f"Found {len(suggestions)} available time slots.",
                "parameters": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "duration_minutes": duration_minutes,
                    "working_hours": f"{work_start_hour}-{work_end_hour}"
                }
            }

        except Exception as e:
            logger.error(f"Failed to suggest meeting times: {e}")
            return {
                "success": False,
                "error": f"Failed to suggest meeting times: {e}"
            }

    @mcp.tool()
    def update_calendar_event(
        event_id: str,
        summary: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing calendar event.

        Args:
            event_id (str): The ID of the event to update
            summary (str, optional): New title for the event
            start_time (str, optional): New start time
            end_time (str, optional): New end time
            description (str, optional): New description
            location (str, optional): New location

        Returns:
            Dict[str, Any]: Updated event details
        """
        credentials = get_credentials()

        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_calendar_service(credentials)

            event = service.events().get(calendarId="primary", eventId=event_id).execute()

            if summary:
                event["summary"] = summary
            if description:
                event["description"] = description
            if location:
                event["location"] = location

            if start_time:
                try:
                    start_dt = parser.parse(start_time, fuzzy=True)
                    event["start"] = {"dateTime": start_dt.isoformat(), "timeZone": get_user_timezone()}
                except Exception:
                    return {"success": False, "error": f"Could not parse start time: {start_time}"}

            if end_time:
                try:
                    end_dt = parser.parse(end_time, fuzzy=True)
                    event["end"] = {"dateTime": end_dt.isoformat(), "timeZone": get_user_timezone()}
                except Exception:
                    return {"success": False, "error": f"Could not parse end time: {end_time}"}

            updated_event = service.events().update(
                calendarId="primary",
                eventId=event_id,
                body=event
            ).execute()

            return {
                "success": True,
                "message": "Event updated successfully.",
                "event_id": updated_event["id"],
                "event_link": updated_event.get("htmlLink", ""),
                "summary": updated_event.get("summary", "")
            }

        except Exception as e:
            logger.error(f"Failed to update calendar event: {e}")
            return {"success": False, "error": f"Failed to update calendar event: {e}"}

    @mcp.tool()
    def delete_calendar_event(event_id: str) -> Dict[str, Any]:
        """
        Delete a calendar event.

        Args:
            event_id (str): The ID of the event to delete

        Returns:
            Dict[str, Any]: Result of the operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_calendar_service(credentials)

            service.events().delete(calendarId="primary", eventId=event_id).execute()

            return {
                "success": True,
                "message": "Event deleted successfully.",
                "event_id": event_id
            }

        except Exception as e:
            logger.error(f"Failed to delete calendar event: {e}")
            return {"success": False, "error": f"Failed to delete calendar event: {e}"}

    @mcp.tool()
    def rsvp_event(event_id: str, response: str) -> Dict[str, Any]:
        """
        Respond to a calendar event invitation.

        Args:
            event_id (str): The ID of the event
            response (str): Response status - "accepted", "declined", or "tentative"

        Returns:
            Dict[str, Any]: Result of the operation
        """
        credentials = get_credentials()

        if not credentials:
            return {"error": "Not authenticated. Please use the authenticate tool first."}

        if response not in ["accepted", "declined", "tentative"]:
            return {"success": False, "error": "Response must be 'accepted', 'declined', or 'tentative'"}

        try:
            service = get_calendar_service(credentials)

            event = service.events().get(calendarId="primary", eventId=event_id).execute()

            gmail_service = get_gmail_service(credentials)
            profile = gmail_service.users().getProfile(userId="me").execute()
            user_email = profile.get("emailAddress", "")

            attendees = event.get("attendees", [])
            for attendee in attendees:
                if attendee.get("email", "").lower() == user_email.lower():
                    attendee["responseStatus"] = response
                    break

            event["attendees"] = attendees

            updated_event = service.events().update(
                calendarId="primary",
                eventId=event_id,
                body=event
            ).execute()

            return {
                "success": True,
                "message": f"RSVP updated to '{response}'.",
                "event_id": event_id,
                "summary": updated_event.get("summary", "")
            }

        except Exception as e:
            logger.error(f"Failed to RSVP: {e}")
            return {"success": False, "error": f"Failed to RSVP: {e}"}
