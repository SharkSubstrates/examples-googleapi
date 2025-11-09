"""
Example: Get User Information and Available Drives

This example demonstrates how to:
- Authenticate with Google Drive
- Get the current user's information
- List all drives (including shared drives) the user has access to
"""
import sys
import os
from pathlib import Path

# Add parent directory to path so we can import gdrivekit
sys.path.insert(0, str(Path(__file__).parent.parent))

from gdrivekit.clients import GDriveClient
from dotenv import load_dotenv


def test_get_user_info(client: GDriveClient):
    """Display information about the authenticated user."""
    print("\n=== USER INFORMATION ===")
    user_info = client.get_user_info()
    print(user_info)


def test_get_drives_info(client: GDriveClient):
    """List all available drives (including shared drives)."""
    print("\n=== AVAILABLE DRIVES ===")
    for drive in client.get_drives_info():
        print(drive.to_dict())


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
    test_get_user_info(client)
    test_get_drives_info(client)

