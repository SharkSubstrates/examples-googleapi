"""
Example: Export Single Files (Documents, Sheets, Slides)

This example demonstrates how to:
- Export a Google Doc to markdown with images and comments
- Export a Google Slides to markdown with speaker notes
- Export a Google Sheet to markdown tables

Shows the new decoupled package architecture where you import
only what you need.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

from googleapi_oauth import OAuth2Client
from secretstore import KeyringStorage
from googleapi_drive import DriveClient, ItemType
from googleapi_docs import DocsClient
from googleapi_sheets import SheetsClient, convert_sheets_to_markdown
from googleapi_slides import SlidesClient, convert_slides_to_markdown


# Test file IDs - replace with your own
# See MY_TEST_IDS.txt for the original test IDs
TEST_DOCUMENT_ID = "YOUR_DOCS_ID_HERE"
TEST_SLIDES_ID = "YOUR_SLIDES_ID_HERE"
TEST_SHEET_ID = "YOUR_SHEET_ID_HERE"


def export_document(drive: DriveClient, docs: DocsClient, doc_id: str, output_dir: Path):
    """Export a Google Doc to markdown with images and comments."""
    print(f"\n=== EXPORTING DOCUMENT {doc_id} ===")
    
    # Get file metadata from Drive
    item = drive.get_item(doc_id)
    print(f"Title: {item.name}")
    print(f"Type: {item.type}")
    
    # Get comments (optional, requires Drive API)
    comments = drive.get_comments(doc_id)
    print(f"Comments: {len(comments)}")
    
    # Export to markdown via Docs API
    markdown, assets = docs.export(doc_id, comments=comments)
    
    # Save to disk
    doc_output_dir = output_dir / doc_id
    doc_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save markdown
    (doc_output_dir / 'content.md').write_text(markdown)
    print(f"Saved markdown: {doc_output_dir / 'content.md'}")
    
    # Save assets (images)
    if assets:
        assets_dir = doc_output_dir / 'assets'
        assets_dir.mkdir(exist_ok=True)
        for asset in assets:
            asset_path = assets_dir / asset.name
            asset_path.write_bytes(asset.content)
        print(f"Saved {len(assets)} assets to {assets_dir}")
    
    print(f"✓ Document exported to {doc_output_dir}")


def export_slides(drive: DriveClient, slides: SlidesClient, slides_id: str, output_dir: Path):
    """Export a Google Slides presentation to markdown with images."""
    print(f"\n=== EXPORTING SLIDES {slides_id} ===")
    
    # Get file metadata from Drive
    item = drive.get_item(slides_id)
    print(f"Title: {item.name}")
    
    # Get comments (optional)
    comments = drive.get_comments(slides_id)
    print(f"Comments: {len(comments)}")
    
    # Fetch presentation data
    presentation_data = slides.fetch_presentation_data(slides_id)
    print(f"Slides: {len(presentation_data['slides'])}")
    
    # Convert to markdown
    markdown, assets = convert_slides_to_markdown(presentation_data, comments=comments)
    
    # Save to disk
    slides_output_dir = output_dir / slides_id
    slides_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save markdown
    (slides_output_dir / 'content.md').write_text(markdown)
    print(f"Saved markdown: {slides_output_dir / 'content.md'}")
    
    # Save assets (images)
    if assets:
        assets_dir = slides_output_dir / 'assets'
        assets_dir.mkdir(exist_ok=True)
        for asset in assets:
            asset_path = assets_dir / asset.name
            asset_path.write_bytes(asset.content)
        print(f"Saved {len(assets)} assets to {assets_dir}")
    
    print(f"✓ Slides exported to {slides_output_dir}")


def export_sheet(drive: DriveClient, sheets: SheetsClient, sheet_id: str, output_dir: Path):
    """Export a Google Sheet to markdown tables."""
    print(f"\n=== EXPORTING SHEET {sheet_id} ===")
    
    # Get file metadata from Drive
    item = drive.get_item(sheet_id)
    print(f"Title: {item.name}")
    
    # Get comments (optional)
    comments = drive.get_comments(sheet_id)
    print(f"Comments: {len(comments)}")
    
    # Fetch spreadsheet data
    sheets_data = sheets.fetch_spreadsheet_data(sheet_id)
    print(f"Sheets/tabs: {len(sheets_data)}")
    
    # Convert to markdown
    markdown = convert_sheets_to_markdown(sheets_data, comments=comments)
    
    # Save to disk
    sheet_output_dir = output_dir / sheet_id
    sheet_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save markdown
    (sheet_output_dir / 'content.md').write_text(markdown)
    print(f"Saved markdown: {sheet_output_dir / 'content.md'}")
    
    print(f"✓ Sheet exported to {sheet_output_dir}")


def export_doc_without_drive(docs: DocsClient, doc_id: str, output_dir: Path):
    """
    Export a doc if you already know the ID - no Drive API needed!
    
    This demonstrates loose coupling - you can use Docs API alone
    if you don't need metadata or comments.
    """
    print(f"\n=== EXPORTING DOCUMENT (NO DRIVE) {doc_id} ===")
    
    # Export directly - no Drive API calls
    markdown, assets = docs.export(doc_id, comments=None)
    
    # Save to disk
    doc_output_dir = output_dir / f"{doc_id}_no_drive"
    doc_output_dir.mkdir(parents=True, exist_ok=True)
    
    (doc_output_dir / 'content.md').write_text(markdown)
    
    if assets:
        assets_dir = doc_output_dir / 'assets'
        assets_dir.mkdir(exist_ok=True)
        for asset in assets:
            (assets_dir / asset.name).write_bytes(asset.content)
    
    print(f"✓ Document exported to {doc_output_dir} (without Drive API)")


if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()
    
    # Step 1: Set up authentication - Set to ephemeral storage for testing
    auth_client = OAuth2Client(
        client_id=os.getenv('CLIENT_ID'),
        client_secret=os.getenv('CLIENT_SECRET'),
        scopes=os.getenv('CLIENT_SCOPES', '').split(',')
    )
    
    # Step 2: Create API clients
    # Only import what you need! Each client is independent.
    #drive = DriveClient(auth_client)
    docs = DocsClient(auth_client)
    #sheets = SheetsClient(auth_client)
    #slides = SlidesClient(auth_client)
    
    # Show user info
    #print("User:", drive.get_user_info())
    #print("Drives:", len(drive.drives))
    
    # Output directory
    output_dir = Path(__file__).parent / "exported_docs"
    output_dir.mkdir(exist_ok=True)
    
    # Export examples
    #export_document(drive, docs, TEST_DOCUMENT_ID, output_dir)
    # export_slides(drive, slides, TEST_SLIDES_ID, output_dir)
    # export_sheet(drive, sheets, TEST_SHEET_ID, output_dir)
    
    # Bonus: Export without Drive dependency
    export_doc_without_drive(docs, TEST_DOCUMENT_ID, output_dir)
    
    print("\n✓ All exports complete!")
    print(f"Output saved to: {output_dir}")
