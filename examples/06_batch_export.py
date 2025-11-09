"""
Example: Batch Export Operations

This example demonstrates how to:
- Export multiple files by their IDs in parallel
- Export entire folders recursively
- Handle caching to avoid re-exporting unchanged files
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
TEST_SLIDES_ID = "16vqnCLrQWeLqCjuFFyaaDC9mfX0sJPfYoeWKmfw7FNQ"
TEST_SHEET_ID = "1TABUvAt2w7LmWjdFPHVxnOAuzeb5u5KJZ34V9FUcfio"
TEST_FOLDER_ID = "1eLjPKiyZYHJc0DZwi7tamQSM8Nfy3EeB"


def test_batch_export_by_ids(client: GDriveClient):
    """Export multiple files by providing a list of specific IDs."""
    print("\n" + "="*80)
    print("TEST: Batch Export by IDs")
    print("="*80)
    
    test_ids = [
        TEST_DOCUMENT_ID,
        TEST_SLIDES_ID,
        TEST_SHEET_ID,
    ]
    
    result = client.batch_export_by_ids(
        item_ids=test_ids,
        output_path="./exported_docs",
        output_type="markdown",
        max_workers=3
    )
    
    print(f"\nResults:")
    print(f"  Total Processed: {result.total_processed}")
    print(f"  Successes: {len(result.successes)}")
    print(f"  Failures: {len(result.failures)}")
    print(f"  Skipped: {len(result.skipped)}")
    
    if result.successes:
        print("\n  Successful exports:")
        for item in result.successes:
            print(f"    - {item['name']} ({item['type']})")
    
    if result.failures:
        print("\n  Failed exports:")
        for item in result.failures:
            print(f"    - {item['name']}: {item['error']}")
    
    if result.skipped:
        print("\n  Skipped exports:")
        for item in result.skipped:
            print(f"    - {item['name']}: {item['reason']}")
    
    print("\n" + "="*80)
    return result


def test_batch_export_by_ids_second_run(client: GDriveClient):
    """Run batch export again to verify skip logic works for unchanged files."""
    print("\n" + "="*80)
    print("TEST: Batch Export by IDs - Second Run (should skip unchanged files)")
    print("="*80)
    
    test_ids = [
        TEST_DOCUMENT_ID,
        TEST_SLIDES_ID,
        TEST_SHEET_ID,
    ]
    
    result = client.batch_export_by_ids(
        item_ids=test_ids,
        output_path="./exported_docs",
        output_type="markdown",
        max_workers=3
    )
    
    print(f"\nResults:")
    print(f"  Total Processed: {result.total_processed}")
    print(f"  Successes: {len(result.successes)}")
    print(f"  Failures: {len(result.failures)}")
    print(f"  Skipped: {len(result.skipped)}")
    
    if result.skipped:
        print("\n  Skipped exports (expected - files already up-to-date):")
        for item in result.skipped:
            print(f"    - {item['name']}: {item['reason']}")
    
    print("\n" + "="*80)
    return result


def test_batch_export_folder(client: GDriveClient, folder_id: str, depth=None):
    """Export an entire folder recursively."""
    print("\n" + "="*80)
    print(f"TEST: Batch Export Folder (recursive, depth={depth})")
    print("="*80)
    
    result = client.batch_export(
        folder_id=folder_id,
        output_path="./exported_docs",
        depth=depth,
        output_type="markdown",
        max_workers=5
    )
    
    print(f"\nResults:")
    print(f"  Total Processed: {result.total_processed}")
    print(f"  Successes: {len(result.successes)}")
    print(f"  Failures: {len(result.failures)}")
    print(f"  Skipped: {len(result.skipped)}")
    
    if result.successes:
        print("\n  Successful exports:")
        for item in result.successes[:10]:  # Show first 10
            print(f"    - {item['name']} ({item['type']})")
        if len(result.successes) > 10:
            print(f"    ... and {len(result.successes) - 10} more")
    
    if result.failures:
        print("\n  Failed exports:")
        for item in result.failures[:5]:  # Show first 5
            print(f"    - {item['name']}: {item['error'][:80]}...")
        if len(result.failures) > 5:
            print(f"    ... and {len(result.failures) - 5} more")
    
    if result.skipped:
        print(f"\n  Skipped: {len(result.skipped)} files")
    
    print("\n" + "="*80)
    return result


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
    
    print("\n" + "="*80)
    print("BATCH EXPORT TESTS")
    print("="*80)
    
    # Test 1: Export by specific IDs
    test_batch_export_by_ids(client)
    
    # Test 2: Re-run to show caching works
    test_batch_export_by_ids_second_run(client)
    
    # Test 3: Export entire folder
    test_batch_export_folder(client, TEST_FOLDER_ID)
    
    print("\n" + "="*80)
    print("ALL TESTS COMPLETE")
    print("="*80)

