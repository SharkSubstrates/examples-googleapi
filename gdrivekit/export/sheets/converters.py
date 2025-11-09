"""
HTML/PDF/Markdown converters specifically for Google Sheets.
"""
from __future__ import annotations
import re
import base64
import urllib.request
from typing import List, Tuple, Dict, Any
from bs4 import BeautifulSoup
from ..models import ExportedAsset

import logging
logger = logging.getLogger(__name__)


def _extract_mime_type_from_data_uri(data_uri: str) -> str:
    """Extract MIME type from a data URI."""
    match = re.match(r'data:([^;]+);', data_uri)
    if match:
        return match.group(1)
    return "application/octet-stream"


def _guess_extension_from_mime(mime_type: str) -> str:
    """Guess file extension from MIME type."""
    mime_to_ext = {
        'image/png': '.png',
        'image/jpeg': '.jpg',
        'image/jpg': '.jpg',
        'image/gif': '.gif',
        'image/svg+xml': '.svg',
        'image/webp': '.webp',
        'application/pdf': '.pdf',
    }
    return mime_to_ext.get(mime_type, '.bin')


def extract_assets_from_sheets_html(html_content: str) -> Tuple[str, List[ExportedAsset]]:
    """
    Extract inline assets from Google Sheets HTML export.
    Handles embedded charts and images.
    
    Returns:
        Tuple of (modified_html, list_of_assets)
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    assets = []
    asset_counter = 1
    
    for img in soup.find_all('img'):
        src = img.get('src', '')
        
        # Handle data URIs
        if src.startswith('data:'):
            try:
                mime_type = _extract_mime_type_from_data_uri(src)
                
                if ';base64,' in src:
                    base64_data = src.split(';base64,')[1]
                    binary_data = base64.b64decode(base64_data)
                    
                    extension = _guess_extension_from_mime(mime_type)
                    asset_name = f"sheet_asset_{asset_counter:03d}{extension}"
                    anchor = f"sheet_asset_{asset_counter:03d}"
                    
                    asset = ExportedAsset(
                        name=asset_name,
                        content=binary_data,
                        anchor=anchor,
                        mime_type=mime_type
                    )
                    assets.append(asset)
                    
                    img['src'] = f"assets/{asset_name}"
                    
                    logger.debug(f"Extracted sheet asset: {asset_name} ({len(binary_data)} bytes)")
                    asset_counter += 1
                    
            except Exception as e:
                logger.warning(f"Failed to extract inline image: {e}")
                continue
        
        # Handle remote URLs
        elif src.startswith('http://') or src.startswith('https://'):
            try:
                logger.debug(f"Downloading remote image: {src}")
                req = urllib.request.Request(src, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    binary_data = response.read()
                    content_type = response.headers.get('Content-Type', 'application/octet-stream')
                    
                    mime_type = content_type.split(';')[0].strip()
                    
                    extension = _guess_extension_from_mime(mime_type)
                    asset_name = f"sheet_asset_{asset_counter:03d}{extension}"
                    anchor = f"sheet_asset_{asset_counter:03d}"
                    
                    asset = ExportedAsset(
                        name=asset_name,
                        content=binary_data,
                        anchor=anchor,
                        mime_type=mime_type
                    )
                    assets.append(asset)
                    
                    img['src'] = f"assets/{asset_name}"
                    
                    logger.debug(f"Downloaded sheet asset: {asset_name} ({len(binary_data)} bytes)")
                    asset_counter += 1
                    
            except Exception as e:
                logger.warning(f"Failed to download remote image {src}: {e}")
                continue
    
    logger.info(f"Extracted {len(assets)} assets from Sheets HTML")
    return str(soup), assets


def process_sheets_html_export(html_content: str) -> Tuple[str, List[ExportedAsset]]:
    """
    Process HTML export for Google Sheets.
    
    Args:
        html_content: Raw HTML from Google Drive export
        
    Returns:
        Tuple of (processed_html, list_of_assets)
    """
    logger.info("Processing Google Sheets HTML export")
    
    # Extract and process assets
    html_content, assets = extract_assets_from_sheets_html(html_content)
    
    logger.info(f"Processing complete: {len(html_content)} chars, {len(assets)} assets")
    return html_content, assets


def _format_markdown_table(data_rows: List[List[Any]]) -> str:
    """
    Convert 2D array of data into a markdown table.
    
    Args:
        data_rows: 2D array where first row is headers, remaining rows are data
        
    Returns:
        Markdown table string
    """
    if not data_rows or len(data_rows) == 0:
        return ""
    
    # Ensure all rows have same length by padding with empty strings
    max_cols = max(len(row) for row in data_rows) if data_rows else 0
    if max_cols == 0:
        return ""
    
    normalized_rows = []
    for row in data_rows:
        # Pad row to max_cols length and escape pipe characters
        normalized_row = []
        for i in range(max_cols):
            if i < len(row):
                cell_value = str(row[i]) if row[i] is not None else ""
                # Escape pipe characters in cell content
                cell_value = cell_value.replace('|', '\\|')
            else:
                cell_value = ""
            normalized_row.append(cell_value)
        normalized_rows.append(normalized_row)
    
    # Build markdown table
    lines = []
    
    # Header row
    header = normalized_rows[0] if normalized_rows else []
    lines.append("| " + " | ".join(header) + " |")
    
    # Separator row
    lines.append("|" + "|".join(["-" * (len(cell) + 2) if cell else "---" for cell in header]) + "|")
    
    # Data rows
    for row in normalized_rows[1:]:
        lines.append("| " + " | ".join(row) + " |")
    
    return "\n".join(lines)


def _map_comments_to_cells(comments: List[dict], sheets_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Map comments to specific cells in sheets using snippet matching.
    
    Google Sheets comments include a 'snippet' field containing the cell text
    and an 'anchor' with format: {"type":"workbook-range","uid":SHEET_ID,"range":"RANGE_ID"}
    
    Args:
        comments: List of comment dictionaries from API
        sheets_data: List of sheet data dictionaries
        
    Returns:
        Dictionary mapping "sheet_name:row:col" to list of comment indices
        e.g., {"Sheet1:0:1": [0, 2], ...} means comments 0 and 2 are at Sheet1, row 0, col 1
    """
    import json
    cell_to_comments = {}
    
    # Build sheet_id to sheet_name mapping and index
    sheet_id_to_data = {}
    for sheet in sheets_data:
        sheet_id_to_data[sheet['sheet_id']] = sheet
    
    for comment_idx, comment in enumerate(comments):
        try:
            snippet = comment.get('snippet', '').strip()
            anchor = comment.get('anchor')
            
            if not anchor or not snippet:
                logger.warning(f"Comment {comment_idx} missing anchor or snippet, skipping")
                continue
            
            # Parse anchor to get sheet ID
            try:
                anchor_data = json.loads(anchor) if isinstance(anchor, str) else anchor
                
                if isinstance(anchor_data, dict):
                    # Format: {"type":"workbook-range","uid":0,"range":"303498729"}
                    sheet_id = anchor_data.get('uid')
                    
                    if sheet_id is None:
                        logger.warning(f"Comment {comment_idx} anchor missing uid: {anchor}")
                        continue
                    
                    # Get the sheet data
                    if sheet_id not in sheet_id_to_data:
                        logger.warning(f"Comment {comment_idx} references unknown sheet ID {sheet_id}")
                        continue
                    
                    sheet = sheet_id_to_data[sheet_id]
                    sheet_name = sheet['sheet_name']
                    data_rows = sheet['data_rows']
                    
                    # Search for snippet in the sheet data
                    found = False
                    for row_idx, row in enumerate(data_rows):
                        for col_idx, cell_value in enumerate(row):
                            cell_str = str(cell_value) if cell_value is not None else ""
                            
                            # Check if snippet matches this cell
                            if cell_str.strip() == snippet:
                                key = f"{sheet_name}:{row_idx}:{col_idx}"
                                
                                if key not in cell_to_comments:
                                    cell_to_comments[key] = []
                                cell_to_comments[key].append(comment_idx)
                                
                                logger.debug(f"Mapped comment {comment_idx} to {key} via snippet '{snippet}'")
                                found = True
                                break
                        
                        if found:
                            break
                    
                    if not found:
                        logger.warning(f"Comment {comment_idx} snippet '{snippet}' not found in sheet {sheet_name}")
                        
            except (json.JSONDecodeError, ValueError, AttributeError, TypeError) as e:
                logger.warning(f"Failed to parse anchor for comment {comment_idx}: {e}")
                continue
                    
        except Exception as e:
            logger.warning(f"Failed to map comment {comment_idx}: {e}")
            continue
    
    logger.info(f"Mapped {len(comments)} comments to {len(cell_to_comments)} cells")
    return cell_to_comments


def _a1_to_indices(a1_notation: str) -> Tuple[int, int]:
    """
    Convert A1 notation (e.g., 'A1', 'B2', 'AA10') to 0-indexed row, col.
    
    Args:
        a1_notation: Cell reference in A1 notation
        
    Returns:
        Tuple of (row_index, col_index) as 0-indexed integers
    """
    match = re.match(r'^([A-Z]+)(\d+)$', a1_notation)
    if not match:
        raise ValueError(f"Invalid A1 notation: {a1_notation}")
    
    col_letters = match.group(1)
    row_num = int(match.group(2))
    
    # Convert column letters to index (A=0, B=1, ..., Z=25, AA=26, etc.)
    col_index = 0
    for char in col_letters:
        col_index = col_index * 26 + (ord(char) - ord('A') + 1)
    col_index -= 1  # Make 0-indexed
    
    row_index = row_num - 1  # Make 0-indexed
    
    return row_index, col_index


def convert_sheets_to_markdown(
    sheets_data: List[Dict[str, Any]],
    comments: List[dict]
) -> str:
    """
    Convert Google Sheets data to markdown with inline comment annotations.
    
    Args:
        sheets_data: List of sheet dictionaries from fetch_spreadsheet_data
        comments: List of comment dictionaries from API
        
    Returns:
        Complete markdown string with all sheets and comments
    """
    logger.info(f"Converting {len(sheets_data)} sheets to markdown with {len(comments)} comments")
    
    # Map comments to cells
    cell_to_comments = _map_comments_to_cells(comments, sheets_data)
    
    # Build markdown sections for each sheet
    markdown_sections = []
    
    for sheet in sheets_data:
        sheet_name = sheet['sheet_name']
        data_rows = sheet['data_rows']
        
        if not data_rows or len(data_rows) == 0:
            logger.debug(f"Skipping empty sheet: {sheet_name}")
            continue
        
        # Create sheet section
        section_lines = [f"# {sheet_name}", ""]
        
        # Build markdown table with comment markers
        # We need to inject [1], [2] markers into cells that have comments
        modified_rows = []
        for row_idx, row in enumerate(data_rows):
            modified_row = []
            for col_idx, cell_value in enumerate(row):
                cell_str = str(cell_value) if cell_value is not None else ""
                
                # Check if this cell has comments
                key = f"{sheet_name}:{row_idx}:{col_idx}"
                if key in cell_to_comments:
                    # Add comment markers
                    for comment_idx in cell_to_comments[key]:
                        cell_str += f"[{comment_idx + 1}]"
                
                modified_row.append(cell_str)
            modified_rows.append(modified_row)
        
        # Generate markdown table
        table_md = _format_markdown_table(modified_rows)
        section_lines.append(table_md)
        section_lines.append("")
        
        # Add comments section for this sheet if there are any comments
        sheet_comments = []
        for row_idx in range(len(data_rows)):
            for col_idx in range(max(len(row) for row in data_rows)):
                key = f"{sheet_name}:{row_idx}:{col_idx}"
                if key in cell_to_comments:
                    sheet_comments.extend(cell_to_comments[key])
        
        if sheet_comments:
            section_lines.append("## Comments")
            section_lines.append("")
            
            # Deduplicate and sort comment indices
            sheet_comments = sorted(set(sheet_comments))
            
            for comment_idx in sheet_comments:
                if comment_idx < len(comments):
                    comment = comments[comment_idx]
                    comment_num = comment_idx + 1
                    
                    section_lines.append(f"### [{comment_num}]")
                    section_lines.append("")
                    
                    timestamp = comment.get('createdTime', '')
                    author = comment.get('author', {})
                    # Handle both string and dict author formats
                    if isinstance(author, dict):
                        author_name = author.get('displayName', 'Unknown')
                    elif isinstance(author, str):
                        author_name = author
                    else:
                        author_name = 'Unknown'
                    content = comment.get('content', '')
                    
                    section_lines.append(f"[{timestamp}] {author_name}: {content}")
                    section_lines.append("")
                    
                    # Add replies
                    for reply in comment.get('replies', []):
                        reply_time = reply.get('createdTime', '')
                        reply_author = reply.get('author', {})
                        # Handle both string and dict author formats
                        if isinstance(reply_author, dict):
                            reply_author_name = reply_author.get('displayName', 'Unknown')
                        elif isinstance(reply_author, str):
                            reply_author_name = reply_author
                        else:
                            reply_author_name = 'Unknown'
                        reply_content = reply.get('content', '')
                        section_lines.append(f"  - [{reply_time}] {reply_author_name}: {reply_content}")
                    
                    if comment.get('replies'):
                        section_lines.append("")
        
        markdown_sections.append("\n".join(section_lines))
    
    # Combine all sections
    final_markdown = "\n".join(markdown_sections)
    
    logger.info(f"Generated {len(final_markdown)} characters of markdown")
    return final_markdown

