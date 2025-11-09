"""
Example: Search Google Drive

This example demonstrates how to:
- Search files by name across all drives
- Search files by content across all drives
- Search within a specific folder
"""
import sys
import os
from pathlib import Path

# Add parent directory to path so we can import gdrivekit
sys.path.insert(0, str(Path(__file__).parent.parent))

from gdrivekit.clients import GDriveClient
from dotenv import load_dotenv


def test_search(client: GDriveClient):
    # Example 1: Search by name across all drives
    print("=" * 60)
    print("Example 1: Search by name across all drives")
    print("=" * 60)
    query = input("Enter search term for file names (or press Enter to skip): ").strip()
    if query:
        print(f"\nSearching for files with '{query}' in the name...")
        results = client.search_by_name(query, limit=10)
        
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
        results = client.search_by_content(query, limit=10)
        
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
            results = client.search_by_name(query, limit=10, folder_id=folder_id)
            
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
    
    # Run search tests
    test_search(client)

