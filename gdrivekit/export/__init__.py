"""
Google Drive document export functionality.

This module provides tools for exporting Google Workspace documents (Docs, Sheets, Slides)
to AI-friendly formats with proper asset extraction, comment preservation, and caching support.

Public API:
    - ExportedItem: Main data structure for exported documents
    - ExportedAsset: Data structure for extracted assets
    - save_to_disk: Save exported item to disk cache
    - load_from_disk: Load exported item from disk cache
    - delete_from_disk: Delete cached exported item
    - cache_exists: Check if cache exists for an item
    
Export modules (by document type):
    - docs: Google Docs export (exporters, converters)
    - sheets: Google Sheets export (exporters, converters)
    - slides: Google Slides export (exporters, converters)
"""

from .models import ExportedItem, ExportedAsset
from .cache import save_to_disk, load_from_disk, delete_from_disk, cache_exists

# Import type-specific modules
from . import docs
from . import sheets
from . import slides

__all__ = [
    'ExportedItem',
    'ExportedAsset',
    'save_to_disk',
    'load_from_disk',
    'delete_from_disk',
    'cache_exists',
    'docs',
    'sheets',
    'slides',
]

