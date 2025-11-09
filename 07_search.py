"""
Example: Search Google Drive

This example demonstrates how to:
- Search files by name across all drives
- Search files by content across all drives
- Search within a specific folder
"""
import os
from pathlib import Path
from dotenv import load_dotenv

from googleapi_oauth import OAuth2Client
from secretstore import KeyringStorage
from googleapi_drive import DriveClient


def test_search(drive: DriveClient):
    # Example 1: Search by name across all drives
    print("=" * 60)
    print("Example 1: Search by name across all drives")
    print("=" * 60)
    query = input("Enter search term for file names (or press Enter to skip): ").strip()
    if query:
        print(f"\nSearching for files with '{query}' in the name...")
        results = drive.search_by_name(query, limit=10)
        
        if results:
            print(f"\nFound {len(results)} results:")
            for i, item in enumerate(results, 1):
                print(f"  {i}. {item.name}")
                print(f"     ID: {item.id}")
                print(f"     Type: {item.type.value}")
                print(f"     Modified: {item.modified_time}")
                print()
        else:
            print("No results found.\n")
    
    # Example 2: Search by content across all drives
    print("=" * 60)
    print("Example 2: Search by content across all drives")
    print("=" * 60)
    query = input("Enter search term for file contents (or press Enter to skip): ").strip()
    if query:
        print(f"\nSearching for files containing '{query}'...")
        results = drive.search_by_content(query, limit=10)
        
        if results:
            print(f"\nFound {len(results)} results:")
            for i, item in enumerate(results, 1):
                print(f"  {i}. {item.name}")
                print(f"     ID: {item.id}")
                print(f"     Type: {item.type.value}")
                print(f"     Modified: {item.modified_time}")
                print()
        else:
            print("No results found.\n")
    
    # Example 3: Search within a specific folder
    print("=" * 60)
    print("Example 3: Search within a specific folder")
    print("=" * 60)
    folder_id = input("Enter folder ID to search within (or press Enter to skip): ").strip()
    if folder_id:
        query = input("Enter search term: ").strip()
        if query:
            print(f"\nSearching for '{query}' in folder {folder_id} and its subfolders...")
            results = drive.search_by_name(query, limit=10, folder_id=folder_id)
            
            if results:
                print(f"\nFound {len(results)} results:")
                for i, item in enumerate(results, 1):
                    print(f"  {i}. {item.name}")
                    print(f"     ID: {item.id}")
                    print(f"     Type: {item.type.value}")
                    print(f"     Modified: {item.modified_time}")
                    print()
            else:
                print("No results found.\n")
    
    print("=" * 60)
    print("Search examples complete!")
    print("=" * 60)


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
    
    # Run search tests
    test_search(drive)
