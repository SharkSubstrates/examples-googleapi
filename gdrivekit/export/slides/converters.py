"""
Markdown conversion for Google Slides via Slides API.
Converts structured presentation data to markdown format.
"""
from __future__ import annotations
import re
import base64
import urllib.request
import requests
from typing import List, Tuple, Dict, Any
from ..models import ExportedAsset

import logging
logger = logging.getLogger(__name__)


def _guess_extension_from_mime(mime_type: str) -> str:
    """Guess file extension from MIME type."""
    mime_to_ext = {
        'image/png': '.png',
        'image/jpeg': '.jpg',
        'image/jpg': '.jpg',
        'image/gif': '.gif',
        'image/svg+xml': '.svg',
        'image/webp': '.webp',
    }
    return mime_to_ext.get(mime_type, '.png')


def _download_image_from_url(url: str, counter: int) -> ExportedAsset:
    """
    Download an image from a URL and create an ExportedAsset.
    
    Args:
        url: Image URL from Slides API
        counter: Asset counter for naming
    
    Returns:
        ExportedAsset with downloaded image data
    """
    try:
        logger.debug(f"Downloading image from {url[:100]}...")
        
        # Try with requests first (handles auth better)
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        binary_data = response.content
        content_type = response.headers.get('Content-Type', 'image/png')
        mime_type = content_type.split(';')[0].strip()
        
        extension = _guess_extension_from_mime(mime_type)
        asset_name = f"slide_image_{counter:03d}{extension}"
        anchor = f"slide_image_{counter:03d}"
        
        asset = ExportedAsset(
            name=asset_name,
            content=binary_data,
            anchor=anchor,
            mime_type=mime_type
        )
        
        logger.debug(f"Downloaded slide asset: {asset_name} ({len(binary_data)} bytes)")
        return asset
        
    except Exception as e:
        logger.warning(f"Failed to download image from {url[:100]}: {e}")
        # Return a placeholder asset
        return ExportedAsset(
            name=f"slide_image_{counter:03d}.png",
            content=b'',
            anchor=f"slide_image_{counter:03d}",
            mime_type='image/png'
        )


def _extract_text_from_slide(slide_data: Dict[str, Any]) -> str:
    """
    Extract all text content from a slide.
    
    Args:
        slide_data: Slide data from Slides API
        
    Returns:
        Combined text content
    """
    return slide_data.get('text_content', '')


def _format_speaker_notes(notes_text: str) -> str:
    """
    Format speaker notes for markdown output.
    
    Args:
        notes_text: Raw speaker notes text
        
    Returns:
        Formatted speaker notes section
    """
    if not notes_text or not notes_text.strip():
        return ""
    
    return f"\n\n### Speaker Notes\n\n{notes_text.strip()}\n"


def _map_comments_to_slides(
    comments: List[dict],
    slides_data: List[Dict[str, Any]]
) -> Dict[int, List[Tuple[str, int]]]:
    """
    Map comments to slide content using text snippet matching.
    
    Args:
        comments: List of comment dictionaries from Drive API
        slides_data: List of processed slide data
        
    Returns:
        Dictionary mapping comment index to (snippet, slide_index) tuples
    """
    comment_positions = {}
    
    for comment_idx, comment in enumerate(comments):
        snippet = comment.get('snippet', '').strip()
        if not snippet:
            logger.warning(f"Comment {comment_idx} has no snippet, skipping mapping")
            continue
        
        # Search for snippet in all slides
        found = False
        for slide_idx, slide_data in enumerate(slides_data):
            text_content = slide_data.get('text_content', '')
            
            if snippet in text_content:
                comment_positions[comment_idx] = (snippet, slide_idx)
                found = True
                logger.debug(f"Mapped comment {comment_idx} to slide {slide_idx + 1}")
                break
        
        if not found:
            logger.warning(f"Could not find snippet for comment {comment_idx}: {snippet[:50]}...")
            # Still track it but with no slide mapping
            comment_positions[comment_idx] = (snippet, -1)
    
    return comment_positions


def _add_comment_markers_to_markdown(
    markdown_content: str,
    comments: List[dict],
    comment_positions: Dict[int, List[Tuple[str, int]]]
) -> str:
    """
    Add comment markers [1], [2], etc. to markdown content.
    
    Args:
        markdown_content: Markdown content without markers
        comments: List of comments
        comment_positions: Mapping from comment index to snippet and slide index
        
    Returns:
        Markdown content with comment markers inserted
    """
    if not comments:
        return markdown_content
    
    # Add markers for each comment
    for comment_idx, (snippet, slide_idx) in comment_positions.items():
        if slide_idx == -1:
            continue  # Skip comments without position
        
        comment_num = comment_idx + 1
        
        # Escape special regex characters in snippet
        pattern = re.escape(snippet)
        
        # Try to add marker after the snippet
        # Use a callback to only replace the first occurrence
        replaced = False
        def replace_once(match):
            nonlocal replaced
            if not replaced:
                replaced = True
                return f"{match.group(0)}[{comment_num}]"
            return match.group(0)
        
        markdown_content = re.sub(
            f'({pattern})',
            replace_once,
            markdown_content,
            count=1
        )
        
        if replaced:
            logger.debug(f"Added marker [{comment_num}] for comment {comment_idx}")
        else:
            logger.warning(f"Could not add marker for comment {comment_idx}")
    
    return markdown_content


def _add_comment_section(markdown_content: str, comments: List[dict] = None) -> str:
    """
    Add formatted comment section at end of markdown.
    
    Args:
        markdown_content: Existing markdown content
        comments: List of comment dictionaries
        
    Returns:
        Markdown with comments section appended
    """
    if not comments or len(comments) == 0:
        return markdown_content
    
    lines = [
        "",
        "---",
        "",
        "## Comments",
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


def convert_slides_to_markdown(
    presentation_data: Dict[str, Any],
    comments: List[dict] = None
) -> Tuple[str, List[ExportedAsset]]:
    """
    Convert Slides API presentation data to markdown format.
    
    This creates a structured markdown document with:
    - Title section
    - Individual slide sections with "# --- Slide N ---" headers
    - Text content from each slide
    - Speaker notes below each slide (if present)
    - Images downloaded and referenced as local assets
    - Comment markers [1], [2] inline in text
    - Comments section at the end
    
    Args:
        presentation_data: Structured data from Slides API (via slides_api_client)
        comments: List of comment dictionaries from Drive API
        
    Returns:
        Tuple of (markdown_string, list_of_assets)
    """
    logger.info("Converting Slides presentation to markdown")
    
    title = presentation_data.get('title', 'Untitled Presentation')
    slides = presentation_data.get('slides', [])
    
    if not slides:
        logger.warning("No slides found in presentation")
        return "# Empty Presentation\n", []
    
    markdown_parts = []
    assets = []
    image_counter = 1
    
    # Process each slide
    for slide in slides:
        slide_num = slide['slide_index'] + 1
        text_content = slide.get('text_content', '')
        speaker_notes = slide.get('speaker_notes', '')
        images = slide.get('images', [])
        
        # Add slide header
        markdown_parts.append(f"# --- Slide {slide_num} ---\n")
        
        # Add text content
        if text_content:
            markdown_parts.append(text_content)
            markdown_parts.append("\n")
        else:
            markdown_parts.append("*(No text content)*\n")
        
        # Download and add images
        for image in images:
            image_url = image.get('url')
            if image_url:
                asset = _download_image_from_url(image_url, image_counter)
                if asset.content:  # Only add if download succeeded
                    assets.append(asset)
                    # Add image reference to markdown
                    markdown_parts.append(f"\n![{asset.anchor}](assets/{asset.name})\n")
                    image_counter += 1
        
        # Add speaker notes if present
        if speaker_notes:
            notes_section = _format_speaker_notes(speaker_notes)
            markdown_parts.append(notes_section)
        
        markdown_parts.append("\n")
    
    # Combine all markdown parts
    markdown_content = ''.join(markdown_parts)
    
    # Map comments to slides
    if comments:
        logger.info(f"Mapping {len(comments)} comments to slides")
        comment_positions = _map_comments_to_slides(comments, slides)
        
        # Add comment markers inline
        markdown_content = _add_comment_markers_to_markdown(
            markdown_content,
            comments,
            comment_positions
        )
        
        # Add comments section at end
        markdown_content = _add_comment_section(markdown_content, comments)
    
    logger.info(f"Conversion complete: {len(markdown_content)} chars, {len(assets)} assets")
    return markdown_content, assets
