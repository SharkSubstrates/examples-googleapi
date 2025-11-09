"""
Example: Get User Information and Available Drives

This example demonstrates how to:
- Authenticate with Google Drive
- Get the current user's information
- List all drives (including shared drives) the user has access to
"""
import os
from pathlib import Path
from dotenv import load_dotenv

from googleapi_oauth import OAuth2Client
from secretstore import KeyringStorage
from googleapi_drive import DriveClient


def test_get_user_info(drive):
    """Display information about the authenticated user."""
    print("\n=== USER INFORMATION ===")
    user_info = drive.get_user_info()
    print(user_info)


def test_get_drives_info(drive):
    """List all available drives (including shared drives)."""
    print("\n=== AVAILABLE DRIVES ===")
    for drive_item in drive.get_drives_info():
        print(f"Drive: {drive_item.name} (ID: {drive_item.id})")


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
    test_get_user_info(drive)
    test_get_drives_info(drive)
