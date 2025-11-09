"""
Example: Working with File Properties and Labels

This example demonstrates how to:
- Get custom properties from a file
- Update custom properties on a file
- Clear properties by setting them to None
- Get labels applied to a file
- List all available labels in the organization
"""
import sys
import os
from pathlib import Path

# Add parent directory to path so we can import gdrivekit
sys.path.insert(0, str(Path(__file__).parent.parent))

from gdrivekit.clients import GDriveClient, GDriveLabelsClient
from dotenv import load_dotenv


# Test file IDs - replace with your own
TEST_DOCUMENT_ID = "1_Aa4YkzEASDP5Kcgj6VG7dMmB891azneTMZP41ntOYQ"


def test_item_properties(client: GDriveClient):
    """Get and update custom properties on a file."""
    print("\n=== FILE PROPERTIES ===")
    test_document = client.get_item(TEST_DOCUMENT_ID)
    
    # Get current properties
    print("Current properties:")
    print(test_document.get_properties())
    
    # Clear a property by setting it to None
    test_properties = {'SDLC_PHASE': None}
    client.update_properties(test_document, test_properties)
    
    print("\nProperties after clearing SDLC_PHASE:")
    print(test_document.get_properties())


def test_get_labels(client: GDriveClient):
    """Get labels applied to a specific file."""
    print("\n=== FILE LABELS ===")
    labels = client.get_labels(TEST_DOCUMENT_ID)
    print(labels)


def test_list_all_labels(labels_client: GDriveLabelsClient):
    """List all labels available in the organization."""
    print("\n=== ALL AVAILABLE LABELS ===")
    labels = labels_client.list_all_labels()
    print(labels)


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
    
    # Initialize labels client (if needed)
    labels_client = GDriveLabelsClient(
        "example-app",
        os.getenv('CLIENT_ID'),
        os.getenv('CLIENT_SECRET'),
        os.getenv('CLIENT_SCOPES').split(',')
    )
    
    # Run tests
    test_item_properties(client)
    test_get_labels(client)
    test_list_all_labels(labels_client)

