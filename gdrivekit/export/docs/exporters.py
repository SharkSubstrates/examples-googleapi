"""
Google Drive API export functions specifically for Google Docs.
Supports: markdown, HTML, PDF
"""
from __future__ import annotations
import requests
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from item import DriveItem

import logging
logger = logging.getLogger(__name__)


def export_docs_to_html(service, item: 'DriveItem') -> str:
    """
    Export a Google Doc to HTML format using exportLinks.
    
    Args:
        service: Authenticated Google Drive service instance
        item: DriveItem with export_links populated
        
    Returns:
        Raw HTML string with comment anchors preserved
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
        
        logger.info(f"Successfully exported {item.id} to HTML ({len(html_content)} bytes)")
        return html_content
        
    except Exception as e:
        raise ValueError(f"Failed to export Doc '{item.id}' to HTML: {str(e)}") from e


def export_docs_to_pdf(service, item: 'DriveItem') -> bytes:
    """
    Export a Google Doc to PDF format using exportLinks.
    
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
        
        logger.info(f"Successfully exported {item.id} to PDF ({len(pdf_data)} bytes)")
        return pdf_data
        
    except Exception as e:
        raise ValueError(f"Failed to export Doc '{item.id}' to PDF: {str(e)}") from e


def export_docs_to_markdown(service, item: 'DriveItem') -> str:
    """
    Export a Google Doc to native Markdown format using exportLinks.
    
    Args:
        service: Authenticated Google Drive service instance
        item: DriveItem with export_links populated
        
    Returns:
        Raw Markdown string with embedded base64 assets
    """
    try:
        if not item.export_links:
            raise ValueError(f"No export links available for item '{item.id}'. Item may not be a Google Workspace document.")
        
        mime_type = 'text/markdown'
        if mime_type not in item.export_links:
            raise ValueError(f"Markdown export not available for item '{item.id}'. Available formats: {list(item.export_links.keys())}")
        
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
        
        markdown_content = response.text
        
        logger.info(f"Successfully exported {item.id} to Markdown ({len(markdown_content)} bytes)")
        return markdown_content
        
    except Exception as e:
        raise ValueError(f"Failed to export Doc '{item.id}' to Markdown: {str(e)}") from e


def export_docs(service, item: 'DriveItem', output_format: str) -> str | bytes:
    """
    Export a Google Doc to the specified format using exportLinks.
    
    Args:
        service: Authenticated Google Drive service instance
        item: DriveItem with export_links populated
        output_format: Either "markdown", "html" or "pdf"
        
    Returns:
        Markdown/HTML string or PDF bytes
    """
    if output_format == "markdown":
        return export_docs_to_markdown(service, item)
    elif output_format == "html":
        return export_docs_to_html(service, item)
    elif output_format == "pdf":
        return export_docs_to_pdf(service, item)
    else:
        raise ValueError(f"Unsupported output format for Docs: {output_format}. Must be 'markdown', 'html' or 'pdf'")

