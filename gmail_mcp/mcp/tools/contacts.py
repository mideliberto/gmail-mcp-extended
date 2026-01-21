"""
Contact Tools Module

Provides access to Google Contacts via the People API.
"""

from typing import Dict, Any, List, Optional

from mcp.server.fastmcp import FastMCP

from gmail_mcp.utils.logger import get_logger
from gmail_mcp.utils.services import get_people_service
from gmail_mcp.utils.config import get_config
from gmail_mcp.auth.oauth import get_credentials

logger = get_logger(__name__)


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
