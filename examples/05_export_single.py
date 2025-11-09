"""
Example: Export Single Files (Documents, Sheets, Slides)

This example demonstrates how to:
- Export a Google Doc to markdown
- Export a Google Slides to markdown
- Export a Google Sheet to CSV/JSON
"""
import sys
import os
from pathlib import Path

# Add parent directory to path so we can import gdrivekit
sys.path.insert(0, str(Path(__file__).parent.parent))

from gdrivekit.clients import GDriveClient
from dotenv import load_dotenv


# Test file IDs - replace with your own
TEST_DOCUMENT_ID = "1_Aa4YkzEASDP5Kcgj6VG7dMmB891azneTMZP41ntOYQ"
TEST_SLIDES_ID = "16vqnCLrQWeLqCjuFFyaaDC9mfX0sJPfYoeWKmfw7FNQ"
TEST_SHEET_ID = "1TABUvAt2w7LmWjdFPHVxnOAuzeb5u5KJZ34V9FUcfio"


def test_export_document(client: GDriveClient, item_id: str):
    """Export a Google Doc to markdown and save to disk."""
    print("\n=== EXPORT DOCUMENT ===")
    exported = client.export_document(item_id, save_to_disk=True)
    print(f"Document exported: {exported}")


def test_export_slides(client: GDriveClient, slides_id: str):
    """Export a Google Slides presentation to markdown and save to disk."""
    print("\n=== EXPORT SLIDES ===")
    exported = client.export_document(slides_id, output_type="markdown", save_to_disk=True)
    print(f"Slides exported: {exported}")


def test_export_sheets(client: GDriveClient, sheet_id: str):
    """Export a Google Sheet and save to disk."""
    print("\n=== EXPORT SHEET ===")
    exported = client.export_document(sheet_id, save_to_disk=True)
    print(f"Sheet exported: {exported}")


if __name__ == "__main__":
    # Load environment variables
    env_path = Path(__file__).parent.parent / "gdfs.env"
    load_dotenv(env_path)
    
    # Initialize client
    client = GDriveClient(
        "example-app",
        os.getenv('CLIENT_ID'),
        os.getenv('CLIENT_SECRET'),
        os.getenv('CLIENT_SCOPES').split(',')
    )
    
    # Run tests
    test_export_document(client, TEST_DOCUMENT_ID)
    test_export_slides(client, TEST_SLIDES_ID)
    test_export_sheets(client, TEST_SHEET_ID)

