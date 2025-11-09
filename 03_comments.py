"""
Example: Working with File Comments

This example demonstrates how to:
- Get all comments on a file
- Reply to a comment
"""
import os
from pathlib import Path
from dotenv import load_dotenv

from googleapi_oauth import OAuth2Client
from secretstore import KeyringStorage
from googleapi_drive import DriveClient


# Test file IDs - replace with your own
# See MY_TEST_IDS.txt for the original test IDs
TEST_DOCUMENT_ID = "YOUR_DOCUMENT_ID_HERE"


def test_get_comments(drive: DriveClient):
    """Get all comments on a file."""
    print("\n=== FILE COMMENTS ===")
    comments = drive.get_comments(TEST_DOCUMENT_ID)
    print(f"Found {len(comments)} comments:")
    
    for idx, comment in enumerate(comments, 1):
        print(f"\n[{idx}] {comment['author']} ({comment['createdTime']}):")
        print(f"    {comment['content']}")
        if comment.get('snippet'):
            print(f"    On: \"{comment['snippet']}\"")
        
        # Show replies
        for reply in comment.get('replies', []):
            print(f"    └─ {reply['author']}: {reply['content']}")
    
    return comments


def test_reply_to_comment(drive: DriveClient):
    """Reply to the first comment on a file."""
    print("\n=== REPLY TO COMMENT ===")
    comments = drive.get_comments(TEST_DOCUMENT_ID)
    
    if not comments:
        print("No comments found on this file.")
        return
    
    TEST_COMMENT_ID = comments[0]['id']
    print(f"Replying to comment by {comments[0]['author']}...")
    
    response = drive.reply_to_comment(
        TEST_DOCUMENT_ID,
        TEST_COMMENT_ID,
        "This is a test reply from the API!"
    )
    print(f"✓ Reply posted successfully (ID: {response['id']})")


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
    comments = test_get_comments(drive)
    
    # Uncomment to test replying (will post real comment!)
    # if comments:
    #     test_reply_to_comment(drive)
