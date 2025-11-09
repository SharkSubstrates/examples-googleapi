"""
Google Drive API export functions specifically for Google Sheets.
Supports: HTML, PDF (no markdown)
"""
from __future__ import annotations
import requests
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from item import DriveItem

import logging
logger = logging.getLogger(__name__)


def export_sheets_to_html(service, item: 'DriveItem') -> str:
    """
    Export Google Sheets to HTML format using exportLinks.
    
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
        
        logger.info(f"Successfully exported Sheets {item.id} to HTML ({len(html_content)} bytes)")
        return html_content
        
    except Exception as e:
        raise ValueError(f"Failed to export Sheets '{item.id}' to HTML: {str(e)}") from e


def export_sheets_to_pdf(service, item: 'DriveItem') -> bytes:
    """
    Export Google Sheets to PDF format using exportLinks.
    
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
        
        logger.info(f"Successfully exported Sheets {item.id} to PDF ({len(pdf_data)} bytes)")
        return pdf_data
        
    except Exception as e:
        raise ValueError(f"Failed to export Sheets '{item.id}' to PDF: {str(e)}") from e


def export_sheets(service, item: 'DriveItem', output_format: str) -> str | bytes:
    """
    Export Google Sheets to the specified format using exportLinks.
    
    Args:
        service: Authenticated Google Drive service instance
        item: DriveItem with export_links populated
        output_format: Either "html" or "pdf" (markdown not supported)
        
    Returns:
        HTML string or PDF bytes
    """
    if output_format == "html":
        return export_sheets_to_html(service, item)
    elif output_format == "pdf":
        return export_sheets_to_pdf(service, item)
    elif output_format == "markdown":
        raise ValueError("Markdown export is not supported for Google Sheets. Use 'html' or 'pdf' instead.")
    else:
        raise ValueError(f"Unsupported output format for Sheets: {output_format}. Must be 'html' or 'pdf'")

