"""
Example: Download Files from Google Drive

This example demonstrates how to:
- Download a binary file from Google Drive
- Save the downloaded file to disk
"""
import os
from pathlib import Path
from dotenv import load_dotenv

from googleapi_oauth import OAuth2Client
from secretstore import KeyringStorage
from googleapi_drive import DriveClient


# Test file IDs - replace with your own
# See MY_TEST_IDS.txt for the original test IDs
TEST_RAW_FILE_ID = "YOUR_RAW_FILE_ID_HERE"


def test_download_file(drive: DriveClient):
    """Download a file and save it to disk."""
    print("\n=== DOWNLOAD FILE ===")
    
    # Get file metadata
    item = drive.get_item(TEST_RAW_FILE_ID)
    print(f"Downloading: {item.name}")
    print(f"Type: {item.type.value}")
    print(f"Size: {item.size if hasattr(item, 'size') else 'unknown'}")
    
    # Download the file
    binary_data = drive.download_file(item)
    
    # Display info
    print(f"\nDownloaded {len(binary_data)} bytes")
    print(f"First 100 bytes: {binary_data[:100]}")
    
    # Save to disk
    output_path = Path(__file__).parent / f"downloaded_{item.name}"
    with open(output_path, "wb") as f:
        f.write(binary_data)
    
    print(f"\n✓ File saved to: {output_path}")


def test_download_to_path(drive: DriveClient):
    """Download a file directly to a path (alternative method)."""
    print("\n=== DOWNLOAD FILE TO PATH ===")
    
    # Get file metadata
    item = drive.get_item(TEST_RAW_FILE_ID)
    print(f"Downloading: {item.name}")
    
    # Download directly to path
    output_path = Path(__file__).parent / f"downloaded_direct_{item.name}"
    drive.download_file(item, filesystem_path=str(output_path))
    
    print(f"✓ File saved to: {output_path}")


if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()
    
    # Step 1: Set up authentication - Set to ephemeral storage for testing
    auth = OAuth2Client(
        client_id=os.getenv('CLIENT_ID'),
        client_secret=os.getenv('CLIENT_SECRET'),
        scopes=os.getenv('CLIENT_SCOPES', '').split(',')
    )
    
    # Step 2: Create Drive client
    drive = DriveClient(auth)
    
    # Run tests
    test_download_file(drive)
    # test_download_to_path(drive)  # Alternative method
