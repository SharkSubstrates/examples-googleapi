"""
HTML to Markdown conversion specifically for Google Docs.
"""
from __future__ import annotations
import re
import base64
from typing import List, Tuple
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


def extract_assets_from_markdown(markdown_content: str) -> Tuple[str, List[ExportedAsset]]:
    """
    Extract base64 images from markdown (both inline and reference-style).
    
    Google Docs markdown export uses reference-style images like:
    ![image1]
    [image1]: <data:image/png;base64,...>
    """
    assets = []
    asset_counter = 1
    
    # Pattern for reference-style image definitions
    ref_pattern = r'\[([^\]]+)\]:\s*<data:([^;]+);base64,([^>]+)>'
    
    def replace_reference(match):
        nonlocal asset_counter
        ref_name = match.group(1)
        mime_type = match.group(2)
        base64_data = match.group(3)
        
        try:
            binary_data = base64.b64decode(base64_data)
            extension = _guess_extension_from_mime(mime_type)
            asset_name = f"{ref_name}{extension}"
            anchor = ref_name
            
            asset = ExportedAsset(
                name=asset_name,
                content=binary_data,
                anchor=anchor,
                mime_type=mime_type
            )
            assets.append(asset)
            
            logger.debug(f"Extracted markdown reference asset: {asset_name} ({len(binary_data)} bytes)")
            asset_counter += 1
            
            return f"[{ref_name}]: assets/{asset_name}"
            
        except Exception as e:
            logger.warning(f"Failed to extract markdown reference image {ref_name}: {e}")
            return match.group(0)
    
    markdown_content = re.sub(ref_pattern, replace_reference, markdown_content, flags=re.MULTILINE)
    
    # Convert reference-style image usage to inline
    for asset in assets:
        ref_name = asset.anchor
        markdown_content = re.sub(
            rf'!\[\]\[{re.escape(ref_name)}\]',
            f'![{ref_name}](assets/{asset.name})',
            markdown_content
        )
        markdown_content = re.sub(
            rf'^\[{re.escape(ref_name)}\]:\s*assets/{re.escape(asset.name)}$',
            '',
            markdown_content,
            flags=re.MULTILINE
        )
    
    # Handle inline images (legacy/fallback)
    inline_pattern = r'!\[(.*?)\]\(data:([^;]+);base64,([^\)]+)\)'
    
    def replace_inline(match):
        nonlocal asset_counter
        alt_text = match.group(1)
        mime_type = match.group(2)
        base64_data = match.group(3)
        
        try:
            binary_data = base64.b64decode(base64_data)
            extension = _guess_extension_from_mime(mime_type)
            asset_name = f"asset_{asset_counter:03d}{extension}"
            anchor = f"asset_{asset_counter:03d}"
            
            asset = ExportedAsset(
                name=asset_name,
                content=binary_data,
                anchor=anchor,
                mime_type=mime_type
            )
            assets.append(asset)
            
            logger.debug(f"Extracted inline markdown asset: {asset_name} ({len(binary_data)} bytes)")
            asset_counter += 1
            
            return f"![{alt_text}](assets/{asset_name})"
            
        except Exception as e:
            logger.warning(f"Failed to extract inline image: {e}")
            return match.group(0)
    
    markdown_content = re.sub(inline_pattern, replace_inline, markdown_content)
    
    logger.info(f"Extracted {len(assets)} assets from Markdown")
    return markdown_content, assets


def add_comment_markers_to_markdown(
    markdown_content: str,
    html_content: str,
    comments: List[dict]
) -> str:
    """
    Use HTML to find comment positions and add markers to markdown.
    
    Strategy:
    1. Extract comment snippets from HTML anchors
    2. Find those snippets in markdown
    3. Add [1], [2] markers after the snippets
    4. Add numbered comment section at end
    """
    if not comments:
        return markdown_content
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find all inline comment reference anchors
    comment_ref_anchors = soup.find_all('a', id=re.compile(r'^cmnt_ref\d+$'))
    
    # Sort by numeric ID - first N are top-level
    sorted_anchors = sorted(comment_ref_anchors, key=lambda a: int(re.search(r'\d+', a.get('id')).group()))
    
    # Get top N anchors (for top-level comments)
    num_top_level = len(comments)
    top_level_anchors = sorted_anchors[:num_top_level]
    
    # For each top-level comment, find the text it's attached to
    for idx, anchor in enumerate(top_level_anchors):
        comment_num = idx + 1
        snippet = comments[idx].get('snippet', '')
        
        if snippet:
            pattern = re.escape(snippet)
            markdown_content = re.sub(
                f'({pattern})',
                f'\\1[{comment_num}]',
                markdown_content,
                count=1
            )
    
    logger.info(f"Added {num_top_level} comment markers to markdown")
    return markdown_content


def add_comment_section(markdown_content: str, comments: List[dict] = None) -> str:
    """Add formatted comment section at end of markdown."""
    if not comments or len(comments) == 0:
        return markdown_content
    
    lines = [
        "",
        "---",
        "",
        "Comments:",
        ""
    ]
    
    for idx, comment in enumerate(comments):
        comment_num = idx + 1
        lines.append(f"### [{comment_num}]")
        lines.append("")
        timestamp = comment.get('createdTime', '')
        author = comment.get('author', 'Unknown')
        content = comment.get('content', '')
        lines.append(f"[{timestamp}] {author}: {content}")
        lines.append("")
        
        for reply in comment.get('replies', []):
            reply_time = reply.get('createdTime', '')
            reply_author = reply.get('author', 'Unknown')
            reply_content = reply.get('content', '')
            lines.append(f"  - [{reply_time}] {reply_author}: {reply_content}")
        
        if comment.get('replies'):
            lines.append("")
    
    return markdown_content + '\n'.join(lines)


def process_docs_markdown_export(
    markdown_content: str,
    html_content: str,
    comments: List[dict] = None
) -> Tuple[str, List[ExportedAsset]]:
    """
    Process native markdown export for Google Docs with HTML for comment positioning.
    
    Args:
        markdown_content: Raw markdown from Google Drive export
        html_content: HTML export (for comment positioning only)
        comments: List of comment dictionaries from API
        
    Returns:
        Tuple of (processed_markdown, list_of_assets)
    """
    logger.info("Processing Google Docs markdown export")
    
    # Step 1: Extract base64 assets from markdown
    markdown_content, assets = extract_assets_from_markdown(markdown_content)
    
    # Step 2: Add comment markers using HTML for positioning
    if comments:
        markdown_content = add_comment_markers_to_markdown(markdown_content, html_content, comments)
    
    # Step 3: Add comment section at end
    markdown_content = add_comment_section(markdown_content, comments)
    
    logger.info(f"Processing complete: {len(markdown_content)} chars, {len(assets)} assets")
    return markdown_content, assets

