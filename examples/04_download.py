"""
Example: Download Files from Google Drive

This example demonstrates how to:
- Download a binary file from Google Drive
- Save the downloaded file to disk
"""
import sys
import os
from pathlib import Path

# Add parent directory to path so we can import gdrivekit
sys.path.insert(0, str(Path(__file__).parent.parent))

from gdrivekit.clients import GDriveClient
from dotenv import load_dotenv


# Test file IDs - replace with your own
TEST_RAW_FILE_ID = "1iOtGFTreJR9fprYlTjZWaQthn364Ny4Q"


def test_download_file(client: GDriveClient):
    """Download a file and save it to disk."""
    print("\n=== DOWNLOAD FILE ===")
    test_document = client.get_item(TEST_RAW_FILE_ID)
    binary_data = client.download_file(test_document)
    
    # Display first 100 bytes
    print(f"Downloaded {len(binary_data)} bytes")
    print(f"First 100 bytes: {binary_data[:100]}")
    
    # Save to disk
    output_path = Path(__file__).parent / "test_download_file.zip"
    with open(output_path, "wb") as f:
        f.write(binary_data)
    
    print(f"File saved to: {output_path}")


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
    
    # Run test
    test_download_file(client)

