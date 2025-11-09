"""
Example: Working with File Comments

This example demonstrates how to:
- Get all comments on a file
- Reply to a comment
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


def test_get_comments(client: GDriveClient):
    """Get all comments on a file."""
    print("\n=== FILE COMMENTS ===")
    comments = client.get_comments(TEST_DOCUMENT_ID)
    print(comments)
    return comments


def test_reply_to_comment(client: GDriveClient):
    """Reply to the first comment on a file."""
    print("\n=== REPLY TO COMMENT ===")
    comments = client.get_comments(TEST_DOCUMENT_ID)
    
    if not comments:
        print("No comments found on this file.")
        return
    
    TEST_COMMENT_ID = comments[0]['id']
    response = client.reply_to_comment(
        TEST_DOCUMENT_ID,
        TEST_COMMENT_ID,
        "This is a test reply from the API!"
    )
    print(response)


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
    comments = test_get_comments(client)
    if comments:
        test_reply_to_comment(client)

