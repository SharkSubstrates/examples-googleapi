"""
Google Drive API export functions specifically for Google Slides.
Supports: HTML, PDF, and structured data via Slides API
"""
from __future__ import annotations
import requests
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from item import DriveItem

import logging
logger = logging.getLogger(__name__)

def export_slides_to_html(service, item: 'DriveItem') -> str:
    """
    Export Google Slides to HTML format using exportLinks.
    
    Args:
        service: Authenticated Google Drive service instance
        item: DriveItem with export_links populated
        
    Returns:
        Raw HTML string
    """
    try:
        if not item.export_links:
            raise ValueError(f"No export links available for item '{item.id}'. Item may not be a Google Workspace document.")
        
        mime_type = 'text/html'
        if mime_type not in item.export_links:
            raise ValueError(f"HTML export not available for item '{item.id}'. Available formats: {list(item.export_links.keys())}")
        
        export_url = item.export_links[mime_type]
        
        # Get access token from service credentials
        credentials = service._http.credentials
        if not credentials.valid:
            from google.auth.transport.requests import Request
            credentials.refresh(Request())
        access_token = credentials.token
        
        # Make HTTP request with authorization
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(export_url, headers=headers)
        response.raise_for_status()
        
        html_content = response.text
        
        logger.info(f"Successfully exported Slides {item.id} to HTML ({len(html_content)} bytes)")
        return html_content
        
    except Exception as e:
        raise ValueError(f"Failed to export Slides '{item.id}' to HTML: {str(e)}") from e


def export_slides_to_pdf(service, item: 'DriveItem') -> bytes:
    """
    Export Google Slides to PDF format using exportLinks.
    
    Args:
        service: Authenticated Google Drive service instance
        item: DriveItem with export_links populated
        
    Returns:
        Raw PDF bytes
    """
    try:
        if not item.export_links:
            raise ValueError(f"No export links available for item '{item.id}'. Item may not be a Google Workspace document.")
        
        mime_type = 'application/pdf'
        if mime_type not in item.export_links:
            raise ValueError(f"PDF export not available for item '{item.id}'. Available formats: {list(item.export_links.keys())}")
        
        export_url = item.export_links[mime_type]
        
        # Get access token from service credentials
        credentials = service._http.credentials
        if not credentials.valid:
            from google.auth.transport.requests import Request
            credentials.refresh(Request())
        access_token = credentials.token
        
        # Make HTTP request with authorization
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(export_url, headers=headers)
        response.raise_for_status()
        
        pdf_data = response.content
        
        logger.info(f"Successfully exported Slides {item.id} to PDF ({len(pdf_data)} bytes)")
        return pdf_data
        
    except Exception as e:
        raise ValueError(f"Failed to export Slides '{item.id}' to PDF: {str(e)}") from e


def export_slides_via_api(
    client_name: str,
    client_id: str,
    client_secret: str,
    scopes: list[str],
    presentation_id: str
) -> Dict[str, Any]:
    """
    Export Google Slides presentation data via Slides API v1.
    
    This provides structured access to slide content, speaker notes, and images,
    which is necessary for markdown conversion.
    
    Args:
        client_name: Name for the OAuth client
        client_id: OAuth client ID
        client_secret: OAuth client secret
        scopes: List of OAuth scopes
        presentation_id: The Google Slides presentation ID
        
    Returns:
        Dictionary with presentation data including slides, text, notes, and images
    """
    try:
        # Import here to avoid circular dependencies
        import sys
        import os
        # Add parent directory to path to import slides_api_client
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from ..clients.slides import GDriveSlidesClient
        
        logger.info(f"Creating Slides API client for presentation {presentation_id}")
        slides_client = GDriveSlidesClient(
            client_name=client_name,
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes
        )
        
        logger.info(f"Fetching presentation data via Slides API")
        presentation_data = slides_client.fetch_presentation_data(presentation_id)
        
        logger.info(f"Successfully exported Slides {presentation_id} via API")
        return presentation_data
        
    except Exception as e:
        raise ValueError(f"Failed to export Slides '{presentation_id}' via API: {str(e)}") from e


def export_slides(service, item: 'DriveItem', output_format: str) -> str | bytes:
    """
    Export Google Slides to the specified format using exportLinks.
    
    Args:
        service: Authenticated Google Drive service instance
        item: DriveItem with export_links populated
        output_format: Either "html" or "pdf" (markdown not supported via this function)
        
    Returns:
        HTML string or PDF bytes
        
    Note:
        For markdown export, use export_slides_via_api() instead, which provides
        structured data that can be converted to markdown.
    """
    if output_format == "html":
        return export_slides_to_html(service, item)
    elif output_format == "pdf":
        return export_slides_to_pdf(service, item)
    elif output_format == "markdown":
        raise ValueError("Markdown export requires Slides API. Use export_slides_via_api() instead.")
    else:
        raise ValueError(f"Unsupported output format for Slides: {output_format}. Must be 'html' or 'pdf'")

