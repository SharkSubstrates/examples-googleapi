from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from ..item import ItemType


@dataclass
class ExportedAsset:
    """
    Represents an asset (image, chart, etc.) extracted from an exported document.
    
    Attributes:
        name: Asset filename
        content: Raw binary data
        anchor: Reference identifier in document (e.g., "img_001", "cmnt1")
        mime_type: Asset content type (e.g., "image/png")
    """
    name: str
    content: bytes
    anchor: str
    mime_type: str


@dataclass
class ExportedItem:
    """
    Represents a fully exported Google Workspace document with all associated data.
    
    Attributes:
        item_id: Original Google Drive file ID
        item_type: Type of document (DOCS_DOCUMENT, DOCS_SHEETS, or DOCS_SLIDES)
        title: Document name
        created_time: Creation timestamp
        modified_time: Last modified timestamp
        content: Exported document content (str for markdown, bytes for pdf)
        content_format: Output format - "pdf" or "markdown"
        assets: List of extracted assets (images, charts, etc.)
        comments: List of document comments with metadata and replies
    """
    item_id: str
    item_type: ItemType
    title: str
    created_time: str
    modified_time: str
    content: str | bytes
    content_format: str  # "pdf" or "markdown"
    assets: List[ExportedAsset] = field(default_factory=list)
    comments: List[dict] = field(default_factory=list)
    
    def is_pdf(self) -> bool:
        """Check if content is PDF format."""
        return self.content_format == "pdf"
    
    def is_markdown(self) -> bool:
        """Check if content is markdown format."""
        return self.content_format == "markdown"


@dataclass
class BatchExportResult:
    """
    Results from a batch export operation.
    
    Attributes:
        total_processed: Total number of items processed
        successes: List of successfully exported items with metadata
        failures: List of failed items with error information
        skipped: List of skipped items with reason
    """
    total_processed: int
    successes: List[dict] = field(default_factory=list)  # {"item_id", "name", "type", "path"}
    failures: List[dict] = field(default_factory=list)   # {"item_id", "name", "error"}
    skipped: List[dict] = field(default_factory=list)    # {"item_id", "name", "reason"}

