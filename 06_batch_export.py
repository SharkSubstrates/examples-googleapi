"""
Example: Batch Export Operations (DEPRECATED)

This example is deprecated. Please see 09_batch_export_parallel.py for the new approach.

The old gdrivekit had a BatchExporter class with orchestration. The new approach
uses standard Python multiprocessing patterns, giving you more control and flexibility.

Key differences:
- Old: BatchExporter class with complex state management
- New: Simple multiprocessing.Pool with worker functions

See: 09_batch_export_parallel.py for the recommended pattern.

This file is kept for reference but will be removed in the future.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

from googleapi_oauth import OAuth2Client
from secretstore import KeyringStorage
from googleapi_drive import DriveClient, ItemType
from googleapi_docs import DocsClient


def simple_batch_export_example():
    """
    Simple batch export without multiprocessing.
    For parallel processing, see 09_batch_export_parallel.py
    """
    print("\n=== SIMPLE BATCH EXPORT ===")
    print("Exporting multiple documents sequentially...")
    print("(For parallel processing, see 09_batch_export_parallel.py)\n")
    
    # Test file IDs - replace with a list of your own ids to export
    test_ids = [
        "YOUR_DOCUMENT_ID_HERE",
        # Add more IDs here...
    ]
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Create clients - Set to ephemeral storage for testing
    auth = OAuth2Client(
        client_id=os.getenv('CLIENT_ID'),
        client_secret=os.getenv('CLIENT_SECRET'),
        scopes=os.getenv('CLIENT_SCOPES', '').split(',')
    )
    
    drive = DriveClient(auth)
    docs = DocsClient(auth)
    
    # Output directory
    output_base = Path(__file__).parent / "batch_exported"
    output_base.mkdir(exist_ok=True)
    
    # Export each document
    results = {'success': 0, 'failed': 0}
    
    for doc_id in test_ids:
        try:
            # Get metadata
            item = drive.get_item(doc_id)
            
            # Skip if not a doc
            if item.type != ItemType.DOCS_DOCUMENT:
                print(f"⊙ Skipping {item.name} (not a Google Doc)")
                continue
            
            print(f"Exporting: {item.name}...")
            
            # Get comments
            comments = drive.get_comments(doc_id)
            
            # Export
            markdown, assets = docs.export(doc_id, comments=comments)
            
            # Save
            doc_output = output_base / doc_id
            doc_output.mkdir(parents=True, exist_ok=True)
            
            (doc_output / 'content.md').write_text(markdown)
            
            if assets:
                assets_dir = doc_output / 'assets'
                assets_dir.mkdir(exist_ok=True)
                for asset in assets:
                    (assets_dir / asset.name).write_bytes(asset.content)
            
            print(f"✓ Exported {item.name}")
            results['success'] += 1
            
        except Exception as e:
            print(f"✗ Failed to export {doc_id}: {e}")
            results['failed'] += 1
    
    print(f"\n=== RESULTS ===")
    print(f"Success: {results['success']}")
    print(f"Failed: {results['failed']}")
    print(f"\nOutput saved to: {output_base}")
    print(f"\n💡 TIP: For faster batch exports, see 09_batch_export_parallel.py")


if __name__ == "__main__":
    print("="*80)
    print("⚠️  DEPRECATED: This example is deprecated")
    print("="*80)
    print()
    print("This old batch exporter pattern is no longer recommended.")
    print("Please use 09_batch_export_parallel.py for the new approach.")
    print()
    print("Press Enter to run a simple sequential export demo, or Ctrl+C to exit...")
    input()
    
    simple_batch_export_example()
