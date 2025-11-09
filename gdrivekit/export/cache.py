"""
Disk caching for exported documents with structured storage format.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Optional
from .models import ExportedItem, ExportedAsset
from ..item import ItemType

import logging
logger = logging.getLogger(__name__)


def save_to_disk(exported_item: ExportedItem, base_path: str = "./exported_docs") -> str:
    """
    Save an ExportedItem to disk in a structured format.
    
    Directory structure:
        base_path/
            {item_id}/
                metadata.json       # Document metadata
                comments.json       # Comments list
                content.md          # or content.pdf
                assets/
                    asset_001.png
                    asset_002.jpg
    
    Args:
        exported_item: The ExportedItem to save
        base_path: Base directory for cached exports
        
    Returns:
        Path to the created directory
        
    Raises:
        IOError: If writing to disk fails
    """
    try:
        # Create directory structure
        item_dir = Path(base_path) / exported_item.item_id
        item_dir.mkdir(parents=True, exist_ok=True)
        
        assets_dir = item_dir / "assets"
        if exported_item.assets:
            assets_dir.mkdir(exist_ok=True)
        
        # Save metadata
        metadata = {
            "item_id": exported_item.item_id,
            "item_type": exported_item.item_type.value,
            "title": exported_item.title,
            "created_time": exported_item.created_time,
            "modified_time": exported_item.modified_time,
            "content_format": exported_item.content_format,
            "asset_count": len(exported_item.assets)
        }
        
        metadata_path = item_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        # Save comments
        comments_path = item_dir / "comments.json"
        with open(comments_path, 'w', encoding='utf-8') as f:
            json.dump(exported_item.comments, f, indent=2)
        
        # Save content
        content_extension = ".pdf" if exported_item.is_pdf() else ".md"
        content_path = item_dir / f"content{content_extension}"
        
        if exported_item.is_pdf():
            with open(content_path, 'wb') as f:
                f.write(exported_item.content)
        else:
            with open(content_path, 'w', encoding='utf-8') as f:
                f.write(exported_item.content)
        
        # Save assets
        for asset in exported_item.assets:
            asset_path = assets_dir / asset.name
            with open(asset_path, 'wb') as f:
                f.write(asset.content)
        
        logger.info(f"Saved exported item to {item_dir}")
        return str(item_dir)
        
    except Exception as e:
        raise IOError(f"Failed to save exported item to disk: {str(e)}") from e


def load_from_disk(item_id: str, base_path: str = "./exported_docs") -> ExportedItem:
    """
    Load an ExportedItem from disk.
    
    Args:
        item_id: The Google Drive file ID
        base_path: Base directory for cached exports
        
    Returns:
        ExportedItem object reconstructed from disk
        
    Raises:
        FileNotFoundError: If the cached item doesn't exist
        IOError: If reading from disk fails
    """
    try:
        item_dir = Path(base_path) / item_id
        
        if not item_dir.exists():
            raise FileNotFoundError(f"Cached item not found: {item_id}")
        
        # Load metadata
        metadata_path = item_dir / "metadata.json"
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Load comments
        comments_path = item_dir / "comments.json"
        with open(comments_path, 'r', encoding='utf-8') as f:
            comments = json.load(f)
        
        # Load content
        content_format = metadata['content_format']
        content_extension = ".pdf" if content_format == "pdf" else ".md"
        content_path = item_dir / f"content{content_extension}"
        
        if content_format == "pdf":
            with open(content_path, 'rb') as f:
                content = f.read()
        else:
            with open(content_path, 'r', encoding='utf-8') as f:
                content = f.read()
        
        # Load assets
        assets = []
        assets_dir = item_dir / "assets"
        if assets_dir.exists():
            for asset_file in sorted(assets_dir.iterdir()):
                if asset_file.is_file():
                    with open(asset_file, 'rb') as f:
                        asset_content = f.read()
                    
                    # Reconstruct asset metadata
                    # The anchor is derived from the filename
                    name = asset_file.name
                    anchor = asset_file.stem  # filename without extension
                    
                    # Try to determine MIME type from extension
                    ext_to_mime = {
                        '.png': 'image/png',
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.gif': 'image/gif',
                        '.svg': 'image/svg+xml',
                        '.webp': 'image/webp',
                        '.pdf': 'application/pdf',
                    }
                    mime_type = ext_to_mime.get(asset_file.suffix.lower(), 'application/octet-stream')
                    
                    asset = ExportedAsset(
                        name=name,
                        content=asset_content,
                        anchor=anchor,
                        mime_type=mime_type
                    )
                    assets.append(asset)
        
        # Reconstruct ExportedItem
        exported_item = ExportedItem(
            item_id=metadata['item_id'],
            item_type=ItemType(metadata['item_type']),
            title=metadata['title'],
            created_time=metadata['created_time'],
            modified_time=metadata['modified_time'],
            content=content,
            content_format=content_format,
            assets=assets,
            comments=comments
        )
        
        logger.info(f"Loaded exported item from {item_dir}")
        return exported_item
        
    except FileNotFoundError:
        raise
    except Exception as e:
        raise IOError(f"Failed to load exported item from disk: {str(e)}") from e


def delete_from_disk(item_id: str, base_path: str = "./exported_docs") -> bool:
    """
    Delete a cached ExportedItem from disk.
    
    Args:
        item_id: The Google Drive file ID
        base_path: Base directory for cached exports
        
    Returns:
        True if deleted, False if not found
    """
    try:
        import shutil
        item_dir = Path(base_path) / item_id
        
        if not item_dir.exists():
            logger.warning(f"Cached item not found for deletion: {item_id}")
            return False
        
        shutil.rmtree(item_dir)
        logger.info(f"Deleted cached item: {item_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete cached item: {e}")
        return False


def cache_exists(item_id: str, base_path: str = "./exported_docs") -> bool:
    """
    Check if a cached export exists for the given item ID.
    
    Args:
        item_id: The Google Drive file ID
        base_path: Base directory for cached exports
        
    Returns:
        True if cache exists, False otherwise
    """
    item_dir = Path(base_path) / item_id
    metadata_path = item_dir / "metadata.json"
    return metadata_path.exists()


def get_cached_metadata(item_id: str, base_path: str = "./exported_docs") -> Optional[dict]:
    """
    Get cached metadata for an item without loading the full export.
    
    Args:
        item_id: The Google Drive file ID
        base_path: Base directory for cached exports
        
    Returns:
        Metadata dictionary if cache exists, None otherwise
    """
    try:
        item_dir = Path(base_path) / item_id
        metadata_path = item_dir / "metadata.json"
        
        if not metadata_path.exists():
            return None
        
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to read cached metadata for {item_id}: {e}")
        return None


def should_skip_export(item_id: str, modified_time: str, base_path: str = "./exported_docs") -> bool:
    """
    Check if an export should be skipped based on cached metadata.
    
    For exported items (docs/slides/sheets), compares the Drive API modified_time
    with the cached modified_time. Skips if cached version is up-to-date.
    
    Args:
        item_id: The Google Drive file ID
        modified_time: Current modified time from Drive API (ISO format)
        base_path: Base directory for cached exports
        
    Returns:
        True if export should be skipped (cache is up-to-date), False otherwise
    """
    cached_metadata = get_cached_metadata(item_id, base_path)
    
    if not cached_metadata:
        return False
    
    cached_modified = cached_metadata.get('modified_time')
    if not cached_modified:
        return False
    
    # Compare timestamps
    # If cached is same or newer, skip the export
    return cached_modified >= modified_time


def raw_file_exists(item_id: str, filename: str, base_path: str = "./exported_docs") -> bool:
    """
    Check if a raw file has already been downloaded.
    
    Args:
        item_id: The Google Drive file ID
        filename: The original filename
        base_path: Base directory for cached exports
        
    Returns:
        True if file exists on disk, False otherwise
    """
    item_dir = Path(base_path) / item_id
    file_path = item_dir / filename
    return file_path.exists()

