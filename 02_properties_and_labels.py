"""
Example: Working with File Properties and Labels

This example demonstrates how to:
- Get custom properties from a file
- Update custom properties on a file
- Clear properties by setting them to None
- Get labels applied to a file
- List all available labels in the organization
"""
import os
from pathlib import Path
from dotenv import load_dotenv

from googleapi_oauth import OAuth2Client
from secretstore import KeyringStorage
from googleapi_drive import DriveClient
from googleapi_labels import LabelsClient


# Test file IDs - replace with your own
# See MY_TEST_IDS.txt for the original test IDs
TEST_DOCUMENT_ID = "YOUR_DOCUMENT_ID_HERE"


def test_item_properties(drive: DriveClient):
    """Get and update custom properties on a file."""
    print("\n=== FILE PROPERTIES ===")
    test_document = drive.get_item(TEST_DOCUMENT_ID)
    
    # Get current properties
    print("Current properties:")
    print(test_document.properties)
    print(test_document.app_properties)
    
    # Update a property
    print("\nUpdating properties...")
    updated_item = drive.update_properties(test_document, {'test_key': 'test_value'})
    print("Updated properties:")
    print(updated_item.properties)
    
    # Clear a property by setting it to None
    print("\nClearing test_key property...")
    updated_item = drive.update_properties(test_document, {'test_key': None})
    print("Properties after clearing:")
    print(updated_item.properties)


def test_get_labels(drive: DriveClient):
    """Get labels applied to a specific file."""
    print("\n=== FILE LABELS ===")
    labels = drive.get_labels(TEST_DOCUMENT_ID)
    print(f"Found {len(labels)} labels on file:")
    for label in labels:
        print(f"  - {label}")


def test_list_all_labels(labels: LabelsClient):
    """List all labels available in the organization."""
    print("\n=== ALL AVAILABLE LABELS ===")
    all_labels = labels.list_all_labels()
    print(f"Found {len(all_labels)} labels in organization:")
    for label in all_labels[:5]:  # Show first 5
        print(f"  - {label.get('name', 'Unnamed')}")
    if len(all_labels) > 5:
        print(f"  ... and {len(all_labels) - 5} more")


if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()
    
    # Step 1: Set up authentication - Set to ephemeral storage for testing
    auth = OAuth2Client(
        client_id=os.getenv('CLIENT_ID'),
        client_secret=os.getenv('CLIENT_SECRET'),
        scopes=os.getenv('CLIENT_SCOPES', '').split(',')
    )
    
    # Step 2: Create clients
    drive = DriveClient(auth)
    labels = LabelsClient(auth)
    
    # Run tests
    test_item_properties(drive)
    test_get_labels(drive)
    test_list_all_labels(labels)
