"""
Contact Tools Module

Provides access to Google Contacts via the People API.
Includes contact hygiene, CRUD operations, and bulk management.
"""

import csv
import re
import os
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Dict, Any, List, Optional, Tuple

from mcp.server.fastmcp import FastMCP

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.utils.services import get_people_service, get_gmail_service
from gmail_mcp.utils.config import get_config
from gmail_mcp.auth.oauth import get_credentials

logger = get_logger(__name__)


def _normalize_phone(phone: str) -> str:
    """Normalize phone number for comparison by removing non-digits."""
    return re.sub(r'\D', '', phone)


def _similarity_ratio(s1: str, s2: str) -> float:
    """Calculate similarity ratio between two strings."""
    if not s1 or not s2:
        return 0.0
    return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()


def _extract_domain(email: str) -> str:
    """Extract domain from email address."""
    if '@' in email:
        return email.split('@')[1].lower()
    return ""


def _parse_signature(text: str) -> Dict[str, Any]:
    """Extract contact info from email signature text."""
    result = {}

    # Phone patterns
    phone_patterns = [
        r'(?:phone|tel|mobile|cell|fax)?[:\s]*(\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})',
        r'(?:phone|tel|mobile|cell|fax)?[:\s]*(\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,4})',
    ]
    for pattern in phone_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result['phone'] = match.group(1).strip()
            break

    # Title patterns - "Title at Company" or "Title | Company" or "Title, Company"
    title_patterns = [
        r'^([^|\n]+?)\s+at\s+([^|\n]+?)$',
        r'^([^|\n]+?)\s*\|\s*([^|\n]+?)$',
        r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*,\s*([^,\n]+?)$',
    ]
    for pattern in title_patterns:
        for line in text.split('\n'):
            match = re.match(pattern, line.strip())
            if match:
                result['title'] = match.group(1).strip()
                result['company'] = match.group(2).strip()
                break

    # LinkedIn URL
    linkedin_match = re.search(r'linkedin\.com/in/([a-zA-Z0-9-]+)', text, re.IGNORECASE)
    if linkedin_match:
        result['linkedin'] = f"https://linkedin.com/in/{linkedin_match.group(1)}"

    return result


def setup_contact_tools(mcp: FastMCP) -> None:
    """Set up contact lookup tools on the FastMCP application."""

    def _check_contacts_enabled() -> Optional[Dict[str, Any]]:
        """Check if contacts API is enabled."""
        config = get_config()
        if not config.get("contacts_api_enabled", False):
            return {
                "success": False,
                "error": "Contacts API not enabled. Set contacts_api_enabled=true in config and re-authenticate."
            }
        return None

    def _parse_person(person: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a Person resource into a simplified contact dict."""
        result = {
            "resource_name": person.get("resourceName", ""),
            "etag": person.get("etag", ""),
        }

        # Names
        names = person.get("names", [])
        if names:
            name = names[0]
            result["name"] = name.get("displayName", "")
            result["given_name"] = name.get("givenName", "")
            result["family_name"] = name.get("familyName", "")

        # Email addresses
        emails = person.get("emailAddresses", [])
        result["emails"] = [
            {
                "address": e.get("value", ""),
                "type": e.get("type", "other"),
                "primary": e.get("metadata", {}).get("primary", False)
            }
            for e in emails
        ]
        if emails:
            # Set primary email as top-level field
            primary_emails = [e for e in emails if e.get("metadata", {}).get("primary")]
            result["email"] = primary_emails[0]["value"] if primary_emails else emails[0].get("value", "")

        # Phone numbers
        phones = person.get("phoneNumbers", [])
        result["phones"] = [
            {
                "number": p.get("value", ""),
                "type": p.get("type", "other"),
                "primary": p.get("metadata", {}).get("primary", False)
            }
            for p in phones
        ]
        if phones:
            primary_phones = [p for p in phones if p.get("metadata", {}).get("primary")]
            result["phone"] = primary_phones[0]["value"] if primary_phones else phones[0].get("value", "")

        # Organizations
        orgs = person.get("organizations", [])
        if orgs:
            org = orgs[0]
            result["organization"] = org.get("name", "")
            result["title"] = org.get("title", "")
            result["department"] = org.get("department", "")

        # Addresses
        addresses = person.get("addresses", [])
        result["addresses"] = [
            {
                "formatted": a.get("formattedValue", ""),
                "type": a.get("type", "other"),
                "city": a.get("city", ""),
                "region": a.get("region", ""),
                "country": a.get("country", ""),
            }
            for a in addresses
        ]

        # Biographies/Notes
        bios = person.get("biographies", [])
        if bios:
            result["notes"] = bios[0].get("value", "")

        # Photo
        photos = person.get("photos", [])
        if photos:
            result["photo_url"] = photos[0].get("url", "")

        return result

    @mcp.tool()
    def list_contacts(max_results: int = 50, page_token: Optional[str] = None) -> Dict[str, Any]:
        """
        List contacts from Google Contacts.

        Args:
            max_results (int): Maximum number of contacts to return (default: 50, max: 100)
            page_token (str, optional): Token for pagination

        Returns:
            Dict[str, Any]: List of contacts with basic information

        Example usage:
        1. List first 50 contacts: list_contacts()
        2. List with pagination: list_contacts(page_token="...")
        """
        error = _check_contacts_enabled()
        if error:
            return error

        credentials = get_credentials()
        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_people_service(credentials)

            max_results = min(max_results, 100)

            request_params = {
                "resourceName": "people/me",
                "pageSize": max_results,
                "personFields": "names,emailAddresses,phoneNumbers,organizations,addresses,biographies,photos"
            }
            if page_token:
                request_params["pageToken"] = page_token

            result = service.people().connections().list(**request_params).execute()

            contacts = []
            for person in result.get("connections", []):
                contacts.append(_parse_person(person))

            return {
                "success": True,
                "count": len(contacts),
                "total_people": result.get("totalPeople", 0),
                "contacts": contacts,
                "next_page_token": result.get("nextPageToken")
            }

        except Exception as e:
            logger.error(f"Failed to list contacts: {e}")
            return {"success": False, "error": f"Failed to list contacts: {e}"}

    @mcp.tool()
    def search_contacts(query: str, max_results: int = 10) -> Dict[str, Any]:
        """
        Search for contacts by name, email, or phone number.

        Args:
            query (str): Search query (name, email, phone, etc.)
            max_results (int): Maximum number of contacts to return (default: 10, max: 30)

        Returns:
            Dict[str, Any]: List of matching contacts

        Example usage:
        1. Search by name: search_contacts(query="John Smith")
        2. Search by email: search_contacts(query="john@example.com")
        3. Search by company: search_contacts(query="Acme Corp")
        """
        error = _check_contacts_enabled()
        if error:
            return error

        credentials = get_credentials()
        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_people_service(credentials)

            max_results = min(max_results, 30)

            result = service.people().searchContacts(
                query=query,
                pageSize=max_results,
                readMask="names,emailAddresses,phoneNumbers,organizations,addresses,biographies,photos"
            ).execute()

            contacts = []
            for item in result.get("results", []):
                person = item.get("person", {})
                contacts.append(_parse_person(person))

            return {
                "success": True,
                "query": query,
                "count": len(contacts),
                "contacts": contacts
            }

        except Exception as e:
            logger.error(f"Failed to search contacts: {e}")
            return {"success": False, "error": f"Failed to search contacts: {e}"}

    @mcp.tool()
    def get_contact(email: Optional[str] = None, resource_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed information about a specific contact.

        Args:
            email (str, optional): Email address to look up
            resource_name (str, optional): People API resource name (e.g., "people/c123456789")

        Note: Either email or resource_name must be provided. If both are provided,
        resource_name takes precedence.

        Returns:
            Dict[str, Any]: Contact details including:
                - name, email, phone
                - organization, title, department
                - addresses, notes
                - photo_url

        Example usage:
        1. By email: get_contact(email="bob@company.com")
        2. By resource name: get_contact(resource_name="people/c123456789")
        """
        error = _check_contacts_enabled()
        if error:
            return error

        if not email and not resource_name:
            return {"success": False, "error": "Either email or resource_name must be provided"}

        credentials = get_credentials()
        if not credentials:
            return {"success": False, "error": "Not authenticated. Please use the authenticate tool first."}

        try:
            service = get_people_service(credentials)

            # If resource_name provided, fetch directly
            if resource_name:
                result = service.people().get(
                    resourceName=resource_name,
                    personFields="names,emailAddresses,phoneNumbers,organizations,addresses,biographies,photos"
                ).execute()

                return {
                    "success": True,
                    "contact": _parse_person(result)
                }

            # If email provided, search for it
            search_result = service.people().searchContacts(
                query=email,
                pageSize=5,
                readMask="names,emailAddresses,phoneNumbers,organizations,addresses,biographies,photos"
            ).execute()

            # Find exact email match
            for item in search_result.get("results", []):
                person = item.get("person", {})
                emails = person.get("emailAddresses", [])
                for e in emails:
                    if e.get("value", "").lower() == email.lower():
                        return {
                            "success": True,
                            "contact": _parse_person(person)
                        }

            # No exact match found
            return {
                "success": False,
                "error": f"No contact found with email: {email}"
            }

        except Exception as e:
            logger.error(f"Failed to get contact: {e}")
            return {"success": False, "error": f"Failed to get contact: {e}"}

    # =========================================================================
    # Contact Hygiene Tools
    # =========================================================================

    @mcp.tool()
    def find_duplicate_contacts(threshold: float = 0.8, max_results: int = 50) -> Dict[str, Any]:
        """
        Find potential duplicate contacts based on email, phone, or name similarity.

        Args:
            threshold (float): Similarity threshold for name matching (0.0-1.0, default: 0.8)
            max_results (int): Maximum duplicate groups to return (default: 50)

        Returns:
            Dict[str, Any]: Groups of potential duplicates with match reasons

        Matching criteria (in order of confidence):
        1. Exact email match (confidence: 1.0)
        2. Exact phone match (confidence: 1.0)
        3. Similar name + same email domain (confidence: 0.9)
        4. Similar name (confidence: based on similarity ratio)
        """
        error = _check_contacts_enabled()
        if error:
            return error

        credentials = get_credentials()
        if not credentials:
            return {"success": False, "error": "Not authenticated"}

        try:
            service = get_people_service(credentials)

            # Fetch all contacts
            all_contacts = []
            page_token = None
            while True:
                request_params = {
                    "resourceName": "people/me",
                    "pageSize": 100,
                    "personFields": "names,emailAddresses,phoneNumbers,organizations"
                }
                if page_token:
                    request_params["pageToken"] = page_token

                result = service.people().connections().list(**request_params).execute()
                all_contacts.extend(result.get("connections", []))

                page_token = result.get("nextPageToken")
                if not page_token or len(all_contacts) >= 1000:
                    break

            # Build indices for matching
            email_index: Dict[str, List[Dict]] = {}
            phone_index: Dict[str, List[Dict]] = {}
            contacts_parsed = []

            for person in all_contacts:
                parsed = _parse_person(person)
                contacts_parsed.append(parsed)

                # Index by email
                for email_obj in parsed.get("emails", []):
                    email = email_obj.get("address", "").lower()
                    if email:
                        if email not in email_index:
                            email_index[email] = []
                        email_index[email].append(parsed)

                # Index by normalized phone
                for phone_obj in parsed.get("phones", []):
                    phone = _normalize_phone(phone_obj.get("number", ""))
                    if phone and len(phone) >= 10:
                        if phone not in phone_index:
                            phone_index[phone] = []
                        phone_index[phone].append(parsed)

            # Find duplicates
            duplicate_groups = []
            seen_resources = set()

            # Check exact email matches
            for email, contacts in email_index.items():
                if len(contacts) > 1:
                    resources = [c["resource_name"] for c in contacts]
                    key = tuple(sorted(resources))
                    if key not in seen_resources:
                        seen_resources.add(key)
                        duplicate_groups.append({
                            "contacts": contacts,
                            "match_reason": f"Same email: {email}",
                            "confidence": 1.0
                        })

            # Check exact phone matches
            for phone, contacts in phone_index.items():
                if len(contacts) > 1:
                    resources = [c["resource_name"] for c in contacts]
                    key = tuple(sorted(resources))
                    if key not in seen_resources:
                        seen_resources.add(key)
                        duplicate_groups.append({
                            "contacts": contacts,
                            "match_reason": f"Same phone: {phone}",
                            "confidence": 1.0
                        })

            # Check similar names
            for i, c1 in enumerate(contacts_parsed):
                name1 = c1.get("name", "")
                if not name1:
                    continue

                for c2 in contacts_parsed[i+1:]:
                    name2 = c2.get("name", "")
                    if not name2:
                        continue

                    # Skip if already found as duplicate
                    key = tuple(sorted([c1["resource_name"], c2["resource_name"]]))
                    if key in seen_resources:
                        continue

                    similarity = _similarity_ratio(name1, name2)
                    if similarity >= threshold:
                        # Check if same domain for higher confidence
                        domain1 = _extract_domain(c1.get("email", ""))
                        domain2 = _extract_domain(c2.get("email", ""))
                        same_domain = domain1 and domain1 == domain2

                        confidence = 0.9 if same_domain else similarity
                        seen_resources.add(key)
                        duplicate_groups.append({
                            "contacts": [c1, c2],
                            "match_reason": f"Similar name ({similarity:.0%})" + (" + same domain" if same_domain else ""),
                            "confidence": round(confidence, 2)
                        })

            # Sort by confidence and limit
            duplicate_groups.sort(key=lambda x: x["confidence"], reverse=True)
            duplicate_groups = duplicate_groups[:max_results]

            return {
                "success": True,
                "total_contacts_scanned": len(contacts_parsed),
                "duplicate_groups": duplicate_groups,
                "total_groups": len(duplicate_groups)
            }

        except Exception as e:
            logger.error(f"Failed to find duplicates: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def find_stale_contacts(months: int = 12, max_results: int = 100) -> Dict[str, Any]:
        """
        Find contacts with no email activity (sent or received) in the specified period.

        Args:
            months (int): Number of months of inactivity (default: 12)
            max_results (int): Maximum contacts to return (default: 100)

        Returns:
            Dict[str, Any]: List of stale contacts with last activity date
        """
        error = _check_contacts_enabled()
        if error:
            return error

        credentials = get_credentials()
        if not credentials:
            return {"success": False, "error": "Not authenticated"}

        try:
            people_service = get_people_service(credentials)
            gmail_service = get_gmail_service(credentials)

            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=months * 30)
            cutoff_str = cutoff_date.strftime("%Y/%m/%d")

            # Fetch contacts with email addresses
            contacts_with_email = []
            page_token = None
            while True:
                request_params = {
                    "resourceName": "people/me",
                    "pageSize": 100,
                    "personFields": "names,emailAddresses"
                }
                if page_token:
                    request_params["pageToken"] = page_token

                result = people_service.people().connections().list(**request_params).execute()

                for person in result.get("connections", []):
                    parsed = _parse_person(person)
                    if parsed.get("email"):
                        contacts_with_email.append(parsed)

                page_token = result.get("nextPageToken")
                if not page_token or len(contacts_with_email) >= 500:
                    break

            # Check email activity for each contact
            stale_contacts = []
            for contact in contacts_with_email:
                email = contact.get("email", "")
                if not email:
                    continue

                # Search for recent emails from/to this contact
                query = f"(from:{email} OR to:{email}) after:{cutoff_str}"
                try:
                    search_result = gmail_service.users().messages().list(
                        userId="me",
                        q=query,
                        maxResults=1
                    ).execute()

                    if not search_result.get("messages"):
                        # No recent activity - this contact is stale
                        stale_contacts.append({
                            "resource_name": contact["resource_name"],
                            "name": contact.get("name", "Unknown"),
                            "email": email,
                            "months_inactive": months,
                            "last_checked": datetime.now().isoformat()
                        })

                        if len(stale_contacts) >= max_results:
                            break
                except Exception:
                    # Skip contacts that cause search errors
                    continue

            return {
                "success": True,
                "cutoff_months": months,
                "contacts_checked": len(contacts_with_email),
                "stale_contacts": stale_contacts,
                "total_stale": len(stale_contacts)
            }

        except Exception as e:
            logger.error(f"Failed to find stale contacts: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def find_incomplete_contacts(
        require_email: bool = True,
        require_phone: bool = False,
        require_organization: bool = False,
        max_results: int = 100
    ) -> Dict[str, Any]:
        """
        Find contacts missing key information.

        Args:
            require_email (bool): Flag contacts without email (default: True)
            require_phone (bool): Flag contacts without phone (default: False)
            require_organization (bool): Flag contacts without organization (default: False)
            max_results (int): Maximum contacts to return (default: 100)

        Returns:
            Dict[str, Any]: List of incomplete contacts with missing fields
        """
        error = _check_contacts_enabled()
        if error:
            return error

        credentials = get_credentials()
        if not credentials:
            return {"success": False, "error": "Not authenticated"}

        try:
            service = get_people_service(credentials)

            incomplete_contacts = []
            page_token = None

            while len(incomplete_contacts) < max_results:
                request_params = {
                    "resourceName": "people/me",
                    "pageSize": 100,
                    "personFields": "names,emailAddresses,phoneNumbers,organizations"
                }
                if page_token:
                    request_params["pageToken"] = page_token

                result = service.people().connections().list(**request_params).execute()

                for person in result.get("connections", []):
                    parsed = _parse_person(person)
                    missing_fields = []

                    has_email = bool(parsed.get("emails"))
                    has_phone = bool(parsed.get("phones"))
                    has_org = bool(parsed.get("organization"))

                    if require_email and not has_email:
                        missing_fields.append("email")
                    if require_phone and not has_phone:
                        missing_fields.append("phone")
                    if require_organization and not has_org:
                        missing_fields.append("organization")

                    if missing_fields:
                        incomplete_contacts.append({
                            "resource_name": parsed["resource_name"],
                            "name": parsed.get("name", "Unknown"),
                            "missing_fields": missing_fields,
                            "has_email": has_email,
                            "has_phone": has_phone,
                            "has_organization": has_org
                        })

                        if len(incomplete_contacts) >= max_results:
                            break

                page_token = result.get("nextPageToken")
                if not page_token:
                    break

            return {
                "success": True,
                "criteria": {
                    "require_email": require_email,
                    "require_phone": require_phone,
                    "require_organization": require_organization
                },
                "incomplete_contacts": incomplete_contacts,
                "total_incomplete": len(incomplete_contacts)
            }

        except Exception as e:
            logger.error(f"Failed to find incomplete contacts: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def export_contacts(
        file_path: str,
        format: str = "csv",
        max_results: int = 1000
    ) -> Dict[str, Any]:
        """
        Export contacts to a CSV file for backup.

        Args:
            file_path (str): Path where to save the export file
            format (str): Export format - currently only "csv" supported
            max_results (int): Maximum contacts to export (default: 1000)

        Returns:
            Dict[str, Any]: Export results including file path and count
        """
        error = _check_contacts_enabled()
        if error:
            return error

        if format != "csv":
            return {"success": False, "error": "Only CSV format is currently supported"}

        credentials = get_credentials()
        if not credentials:
            return {"success": False, "error": "Not authenticated"}

        try:
            service = get_people_service(credentials)

            # Fetch all contacts
            all_contacts = []
            page_token = None

            while len(all_contacts) < max_results:
                request_params = {
                    "resourceName": "people/me",
                    "pageSize": min(100, max_results - len(all_contacts)),
                    "personFields": "names,emailAddresses,phoneNumbers,organizations,addresses,biographies"
                }
                if page_token:
                    request_params["pageToken"] = page_token

                result = service.people().connections().list(**request_params).execute()

                for person in result.get("connections", []):
                    all_contacts.append(_parse_person(person))

                page_token = result.get("nextPageToken")
                if not page_token:
                    break

            # Write to CSV
            fieldnames = ["name", "email", "phone", "organization", "title", "notes"]

            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else ".", exist_ok=True)

            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()

                for contact in all_contacts:
                    row = {
                        "name": contact.get("name", ""),
                        "email": contact.get("email", ""),
                        "phone": contact.get("phone", ""),
                        "organization": contact.get("organization", ""),
                        "title": contact.get("title", ""),
                        "notes": contact.get("notes", "")
                    }
                    writer.writerow(row)

            return {
                "success": True,
                "file_path": file_path,
                "format": format,
                "exported": len(all_contacts)
            }

        except Exception as e:
            logger.error(f"Failed to export contacts: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Contact CRUD Tools (requires contacts write scope)
    # =========================================================================

    @mcp.tool()
    def create_contact(
        name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        organization: Optional[str] = None,
        title: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new contact.

        Args:
            name (str): Contact's full name (required)
            email (str, optional): Email address
            phone (str, optional): Phone number
            organization (str, optional): Company/organization name
            title (str, optional): Job title
            notes (str, optional): Additional notes

        Returns:
            Dict[str, Any]: Created contact details

        Note: Requires contacts write scope. User may need to re-authenticate.
        """
        error = _check_contacts_enabled()
        if error:
            return error

        credentials = get_credentials()
        if not credentials:
            return {"success": False, "error": "Not authenticated"}

        try:
            service = get_people_service(credentials)

            # Build person object
            person = {
                "names": [{"givenName": name.split()[0] if ' ' in name else name,
                          "familyName": ' '.join(name.split()[1:]) if ' ' in name else ""}]
            }

            if email:
                person["emailAddresses"] = [{"value": email}]
            if phone:
                person["phoneNumbers"] = [{"value": phone}]
            if organization or title:
                person["organizations"] = [{}]
                if organization:
                    person["organizations"][0]["name"] = organization
                if title:
                    person["organizations"][0]["title"] = title
            if notes:
                person["biographies"] = [{"value": notes, "contentType": "TEXT_PLAIN"}]

            result = service.people().createContact(body=person).execute()

            return {
                "success": True,
                "message": "Contact created successfully",
                "contact": _parse_person(result)
            }

        except Exception as e:
            error_str = str(e)
            if "403" in error_str or "scope" in error_str.lower():
                return {
                    "success": False,
                    "error": "Permission denied. You need to re-authenticate with contacts write scope."
                }
            logger.error(f"Failed to create contact: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def update_contact(
        resource_name: Optional[str] = None,
        email_lookup: Optional[str] = None,
        name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        organization: Optional[str] = None,
        title: Optional[str] = None,
        notes: Optional[str] = None,
        append_notes: bool = False
    ) -> Dict[str, Any]:
        """
        Update an existing contact.

        Args:
            resource_name (str, optional): Contact resource name (e.g., "people/c123")
            email_lookup (str, optional): Find contact by email instead of resource_name
            name (str, optional): New name
            email (str, optional): New email
            phone (str, optional): New phone
            organization (str, optional): New organization
            title (str, optional): New title
            notes (str, optional): New notes
            append_notes (bool): Append to existing notes instead of replacing (default: False)

        Returns:
            Dict[str, Any]: Updated contact details

        Note: Either resource_name or email_lookup must be provided.
        """
        error = _check_contacts_enabled()
        if error:
            return error

        if not resource_name and not email_lookup:
            return {"success": False, "error": "Either resource_name or email_lookup must be provided"}

        credentials = get_credentials()
        if not credentials:
            return {"success": False, "error": "Not authenticated"}

        try:
            service = get_people_service(credentials)

            # Look up contact if needed
            if email_lookup and not resource_name:
                search_result = service.people().searchContacts(
                    query=email_lookup,
                    pageSize=5,
                    readMask="names,emailAddresses"
                ).execute()

                for item in search_result.get("results", []):
                    person = item.get("person", {})
                    for e in person.get("emailAddresses", []):
                        if e.get("value", "").lower() == email_lookup.lower():
                            resource_name = person.get("resourceName")
                            break
                    if resource_name:
                        break

                if not resource_name:
                    return {"success": False, "error": f"No contact found with email: {email_lookup}"}

            # Get current contact
            current = service.people().get(
                resourceName=resource_name,
                personFields="names,emailAddresses,phoneNumbers,organizations,biographies"
            ).execute()

            # Build update
            update_person = {}
            update_fields = []

            if name:
                update_person["names"] = [{
                    "givenName": name.split()[0] if ' ' in name else name,
                    "familyName": ' '.join(name.split()[1:]) if ' ' in name else ""
                }]
                update_fields.append("names")

            if email:
                update_person["emailAddresses"] = [{"value": email}]
                update_fields.append("emailAddresses")

            if phone:
                update_person["phoneNumbers"] = [{"value": phone}]
                update_fields.append("phoneNumbers")

            if organization or title:
                update_person["organizations"] = [{}]
                if organization:
                    update_person["organizations"][0]["name"] = organization
                if title:
                    update_person["organizations"][0]["title"] = title
                update_fields.append("organizations")

            if notes:
                if append_notes:
                    existing_notes = ""
                    for bio in current.get("biographies", []):
                        existing_notes = bio.get("value", "")
                        break
                    notes = f"{existing_notes}\n\n{notes}" if existing_notes else notes
                update_person["biographies"] = [{"value": notes, "contentType": "TEXT_PLAIN"}]
                update_fields.append("biographies")

            if not update_fields:
                return {"success": False, "error": "No fields to update"}

            # Include etag for optimistic locking
            update_person["etag"] = current.get("etag")

            result = service.people().updateContact(
                resourceName=resource_name,
                updatePersonFields=",".join(update_fields),
                body=update_person
            ).execute()

            return {
                "success": True,
                "message": "Contact updated successfully",
                "contact": _parse_person(result)
            }

        except Exception as e:
            error_str = str(e)
            if "403" in error_str or "scope" in error_str.lower():
                return {
                    "success": False,
                    "error": "Permission denied. You need to re-authenticate with contacts write scope."
                }
            logger.error(f"Failed to update contact: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def delete_contact(
        resource_name: Optional[str] = None,
        email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delete a contact.

        Args:
            resource_name (str, optional): Contact resource name (e.g., "people/c123")
            email (str, optional): Find and delete contact by email

        Returns:
            Dict[str, Any]: Deletion result

        Note: Either resource_name or email must be provided.
        """
        error = _check_contacts_enabled()
        if error:
            return error

        if not resource_name and not email:
            return {"success": False, "error": "Either resource_name or email must be provided"}

        credentials = get_credentials()
        if not credentials:
            return {"success": False, "error": "Not authenticated"}

        try:
            service = get_people_service(credentials)

            # Look up contact if needed
            if email and not resource_name:
                search_result = service.people().searchContacts(
                    query=email,
                    pageSize=5,
                    readMask="names,emailAddresses"
                ).execute()

                for item in search_result.get("results", []):
                    person = item.get("person", {})
                    for e in person.get("emailAddresses", []):
                        if e.get("value", "").lower() == email.lower():
                            resource_name = person.get("resourceName")
                            break
                    if resource_name:
                        break

                if not resource_name:
                    return {"success": False, "error": f"No contact found with email: {email}"}

            service.people().deleteContact(resourceName=resource_name).execute()

            return {
                "success": True,
                "message": f"Contact {resource_name} deleted successfully"
            }

        except Exception as e:
            error_str = str(e)
            if "403" in error_str or "scope" in error_str.lower():
                return {
                    "success": False,
                    "error": "Permission denied. You need to re-authenticate with contacts write scope."
                }
            logger.error(f"Failed to delete contact: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def merge_contacts(
        resource_names: List[str],
        primary: Optional[str] = None,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Merge multiple contacts into one, combining all unique information.

        Args:
            resource_names (List[str]): List of contact resource names to merge
            primary (str, optional): Resource name of contact to keep (default: first in list)
            dry_run (bool): Preview merge without executing (default: True)

        Returns:
            Dict[str, Any]: Merged contact preview or result

        Note: Requires contacts write scope for actual merge.
        """
        error = _check_contacts_enabled()
        if error:
            return error

        if len(resource_names) < 2:
            return {"success": False, "error": "At least 2 contacts required to merge"}

        credentials = get_credentials()
        if not credentials:
            return {"success": False, "error": "Not authenticated"}

        try:
            service = get_people_service(credentials)

            # Fetch all contacts to merge
            contacts_to_merge = []
            for rn in resource_names:
                person = service.people().get(
                    resourceName=rn,
                    personFields="names,emailAddresses,phoneNumbers,organizations,addresses,biographies,photos"
                ).execute()
                contacts_to_merge.append(person)

            # Determine primary contact
            primary_rn = primary if primary else resource_names[0]
            primary_idx = resource_names.index(primary_rn) if primary_rn in resource_names else 0

            # Combine all unique information
            merged_emails = []
            merged_phones = []
            merged_addresses = []
            seen_emails = set()
            seen_phones = set()

            for person in contacts_to_merge:
                for email in person.get("emailAddresses", []):
                    val = email.get("value", "").lower()
                    if val and val not in seen_emails:
                        seen_emails.add(val)
                        merged_emails.append(email)

                for phone in person.get("phoneNumbers", []):
                    val = _normalize_phone(phone.get("value", ""))
                    if val and val not in seen_phones:
                        seen_phones.add(val)
                        merged_phones.append(phone)

                for addr in person.get("addresses", []):
                    merged_addresses.append(addr)

            # Build merged contact preview
            primary_contact = contacts_to_merge[primary_idx]
            merged_preview = {
                "names": primary_contact.get("names", []),
                "emailAddresses": merged_emails,
                "phoneNumbers": merged_phones,
                "addresses": merged_addresses[:3],  # Limit addresses
                "organizations": primary_contact.get("organizations", []),
                "biographies": primary_contact.get("biographies", [])
            }

            result = {
                "success": True,
                "dry_run": dry_run,
                "primary_contact": primary_rn,
                "contacts_to_remove": [rn for rn in resource_names if rn != primary_rn],
                "merged_preview": _parse_person(merged_preview)
            }

            if not dry_run:
                # Actually perform the merge
                # Update primary with merged info
                update_fields = []
                update_body = {"etag": primary_contact.get("etag")}

                if merged_emails:
                    update_body["emailAddresses"] = merged_emails
                    update_fields.append("emailAddresses")
                if merged_phones:
                    update_body["phoneNumbers"] = merged_phones
                    update_fields.append("phoneNumbers")

                if update_fields:
                    service.people().updateContact(
                        resourceName=primary_rn,
                        updatePersonFields=",".join(update_fields),
                        body=update_body
                    ).execute()

                # Delete other contacts
                deleted = []
                for rn in resource_names:
                    if rn != primary_rn:
                        try:
                            service.people().deleteContact(resourceName=rn).execute()
                            deleted.append(rn)
                        except Exception as del_err:
                            logger.warning(f"Failed to delete {rn}: {del_err}")

                result["contacts_deleted"] = deleted
                result["message"] = f"Merged {len(resource_names)} contacts into {primary_rn}"

            return result

        except Exception as e:
            error_str = str(e)
            if "403" in error_str or "scope" in error_str.lower():
                return {
                    "success": False,
                    "error": "Permission denied. You need to re-authenticate with contacts write scope."
                }
            logger.error(f"Failed to merge contacts: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def enrich_contact_from_email(
        email_id: str,
        contact_email: Optional[str] = None,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Extract contact information from an email signature and optionally update the contact.

        Args:
            email_id (str): ID of the email to extract signature from
            contact_email (str, optional): Email of contact to update (default: sender)
            dry_run (bool): Preview extraction without updating (default: True)

        Returns:
            Dict[str, Any]: Extracted information and update preview

        Extracts:
        - Phone numbers
        - Job title and company
        - LinkedIn URL
        """
        error = _check_contacts_enabled()
        if error:
            return error

        credentials = get_credentials()
        if not credentials:
            return {"success": False, "error": "Not authenticated"}

        try:
            gmail_service = get_gmail_service(credentials)
            people_service = get_people_service(credentials)

            # Get email content
            message = gmail_service.users().messages().get(
                userId="me",
                id=email_id,
                format="full"
            ).execute()

            # Extract sender email if not specified
            headers = {h["name"].lower(): h["value"] for h in message.get("payload", {}).get("headers", [])}
            from_header = headers.get("from", "")

            # Parse email from "Name <email@example.com>" format
            email_match = re.search(r'<([^>]+)>', from_header)
            sender_email = email_match.group(1) if email_match else from_header
            target_email = contact_email or sender_email

            # Get email body
            body = ""
            payload = message.get("payload", {})
            if "body" in payload and payload["body"].get("data"):
                import base64
                body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
            else:
                # Check parts for text/plain
                for part in payload.get("parts", []):
                    if part.get("mimeType") == "text/plain":
                        if "body" in part and part["body"].get("data"):
                            body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                            break

            # Extract signature info (usually in last ~20 lines)
            lines = body.split('\n')
            signature_text = '\n'.join(lines[-30:]) if len(lines) > 30 else body

            extracted = _parse_signature(signature_text)

            result = {
                "success": True,
                "dry_run": dry_run,
                "target_email": target_email,
                "extracted_info": extracted
            }

            if not extracted:
                result["message"] = "No contact information found in email signature"
                return result

            # Find existing contact
            search_result = people_service.people().searchContacts(
                query=target_email,
                pageSize=5,
                readMask="names,emailAddresses,phoneNumbers,organizations"
            ).execute()

            existing_contact = None
            for item in search_result.get("results", []):
                person = item.get("person", {})
                for e in person.get("emailAddresses", []):
                    if e.get("value", "").lower() == target_email.lower():
                        existing_contact = person
                        break

            if existing_contact:
                result["existing_contact"] = _parse_person(existing_contact)
            else:
                result["message"] = f"No existing contact found for {target_email}"

            if not dry_run and existing_contact and extracted:
                # Update the contact
                resource_name = existing_contact.get("resourceName")
                update_body = {"etag": existing_contact.get("etag")}
                update_fields = []

                if extracted.get("phone") and not existing_contact.get("phoneNumbers"):
                    update_body["phoneNumbers"] = [{"value": extracted["phone"]}]
                    update_fields.append("phoneNumbers")

                if (extracted.get("title") or extracted.get("company")) and not existing_contact.get("organizations"):
                    update_body["organizations"] = [{}]
                    if extracted.get("title"):
                        update_body["organizations"][0]["title"] = extracted["title"]
                    if extracted.get("company"):
                        update_body["organizations"][0]["name"] = extracted["company"]
                    update_fields.append("organizations")

                if update_fields:
                    updated = people_service.people().updateContact(
                        resourceName=resource_name,
                        updatePersonFields=",".join(update_fields),
                        body=update_body
                    ).execute()
                    result["updated_contact"] = _parse_person(updated)
                    result["fields_updated"] = update_fields
                else:
                    result["message"] = "Contact already has this information"

            return result

        except Exception as e:
            error_str = str(e)
            if "403" in error_str or "scope" in error_str.lower():
                return {
                    "success": False,
                    "error": "Permission denied for update. Set dry_run=True to preview."
                }
            logger.error(f"Failed to enrich contact: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Contact Groups Tools
    # =========================================================================

    @mcp.tool()
    def list_contact_groups() -> Dict[str, Any]:
        """
        List all contact groups (labels) in the user's account.

        Returns:
            Dict[str, Any]: List of contact groups with member counts
        """
        error = _check_contacts_enabled()
        if error:
            return error

        credentials = get_credentials()
        if not credentials:
            return {"success": False, "error": "Not authenticated"}

        try:
            service = get_people_service(credentials)

            result = service.contactGroups().list(
                pageSize=100,
                groupFields="name,memberCount,groupType"
            ).execute()

            groups = []
            for group in result.get("contactGroups", []):
                groups.append({
                    "resource_name": group.get("resourceName", ""),
                    "name": group.get("name", ""),
                    "member_count": group.get("memberCount", 0),
                    "group_type": group.get("groupType", "")
                })

            return {
                "success": True,
                "groups": groups,
                "total": len(groups)
            }

        except Exception as e:
            logger.error(f"Failed to list contact groups: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def create_contact_group(name: str) -> Dict[str, Any]:
        """
        Create a new contact group.

        Args:
            name (str): Name for the new group

        Returns:
            Dict[str, Any]: Created group details
        """
        error = _check_contacts_enabled()
        if error:
            return error

        credentials = get_credentials()
        if not credentials:
            return {"success": False, "error": "Not authenticated"}

        try:
            service = get_people_service(credentials)

            result = service.contactGroups().create(
                body={"contactGroup": {"name": name}}
            ).execute()

            return {
                "success": True,
                "message": f"Contact group '{name}' created",
                "group": {
                    "resource_name": result.get("resourceName", ""),
                    "name": result.get("name", ""),
                    "member_count": 0
                }
            }

        except Exception as e:
            error_str = str(e)
            if "403" in error_str or "scope" in error_str.lower():
                return {"success": False, "error": "Permission denied. Re-authenticate with write scope."}
            logger.error(f"Failed to create contact group: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def add_contacts_to_group(
        group_resource_name: str,
        contact_resource_names: List[str]
    ) -> Dict[str, Any]:
        """
        Add contacts to a group.

        Args:
            group_resource_name (str): Resource name of the group
            contact_resource_names (List[str]): List of contact resource names to add

        Returns:
            Dict[str, Any]: Result of the operation
        """
        error = _check_contacts_enabled()
        if error:
            return error

        credentials = get_credentials()
        if not credentials:
            return {"success": False, "error": "Not authenticated"}

        try:
            service = get_people_service(credentials)

            service.contactGroups().members().modify(
                resourceName=group_resource_name,
                body={"resourceNamesToAdd": contact_resource_names}
            ).execute()

            return {
                "success": True,
                "message": f"Added {len(contact_resource_names)} contacts to group",
                "group": group_resource_name,
                "contacts_added": contact_resource_names
            }

        except Exception as e:
            error_str = str(e)
            if "403" in error_str or "scope" in error_str.lower():
                return {"success": False, "error": "Permission denied. Re-authenticate with write scope."}
            logger.error(f"Failed to add contacts to group: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def remove_contacts_from_group(
        group_resource_name: str,
        contact_resource_names: List[str]
    ) -> Dict[str, Any]:
        """
        Remove contacts from a group.

        Args:
            group_resource_name (str): Resource name of the group
            contact_resource_names (List[str]): List of contact resource names to remove

        Returns:
            Dict[str, Any]: Result of the operation
        """
        error = _check_contacts_enabled()
        if error:
            return error

        credentials = get_credentials()
        if not credentials:
            return {"success": False, "error": "Not authenticated"}

        try:
            service = get_people_service(credentials)

            service.contactGroups().members().modify(
                resourceName=group_resource_name,
                body={"resourceNamesToRemove": contact_resource_names}
            ).execute()

            return {
                "success": True,
                "message": f"Removed {len(contact_resource_names)} contacts from group",
                "group": group_resource_name,
                "contacts_removed": contact_resource_names
            }

        except Exception as e:
            error_str = str(e)
            if "403" in error_str or "scope" in error_str.lower():
                return {"success": False, "error": "Permission denied. Re-authenticate with write scope."}
            logger.error(f"Failed to remove contacts from group: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    def delete_contact_group(group_resource_name: str, delete_contacts: bool = False) -> Dict[str, Any]:
        """
        Delete a contact group.

        Args:
            group_resource_name (str): Resource name of the group to delete
            delete_contacts (bool): Also delete contacts in the group (default: False)

        Returns:
            Dict[str, Any]: Result of the operation
        """
        error = _check_contacts_enabled()
        if error:
            return error

        credentials = get_credentials()
        if not credentials:
            return {"success": False, "error": "Not authenticated"}

        try:
            service = get_people_service(credentials)

            service.contactGroups().delete(
                resourceName=group_resource_name,
                deleteContacts=delete_contacts
            ).execute()

            return {
                "success": True,
                "message": f"Contact group deleted" + (" (with contacts)" if delete_contacts else ""),
                "group": group_resource_name
            }

        except Exception as e:
            error_str = str(e)
            if "403" in error_str or "scope" in error_str.lower():
                return {"success": False, "error": "Permission denied. Re-authenticate with write scope."}
            logger.error(f"Failed to delete contact group: {e}")
            return {"success": False, "error": str(e)}

    logger.info("Contact tools registered successfully")
