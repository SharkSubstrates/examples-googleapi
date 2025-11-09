"""
Example: Batch Export with Parallel Processing

This example demonstrates how to:
- Export multiple documents in parallel using multiprocessing
- Implement simple caching to skip unchanged files
- Handle errors gracefully

No BatchExporter class needed - just standard Python multiprocessing.
"""
import os
from pathlib import Path
from multiprocessing import Pool
from typing import List, Tuple
import json
import hashlib
from dotenv import load_dotenv

from googleapi_oauth import OAuth2Client
from secretstore import KeyringStorage
from googleapi_drive import DriveClient, ItemType
from googleapi_docs import DocsClient


# Global auth config (loaded once, shared across workers)
AUTH_CONFIG = None


def init_worker(client_id: str, client_secret: str, scopes: List[str]):
    """Initialize worker process with auth credentials."""
    global AUTH_CONFIG
    AUTH_CONFIG = {
        'client_id': client_id,
        'client_secret': client_secret,
        'scopes': scopes
    }


def export_document_worker(args: Tuple[str, Path]) -> dict:
    """
    Worker function to export a single document.
    
    Args:
        args: Tuple of (doc_id, output_base_dir)
        
    Returns:
        Result dict with status and info
    """
    doc_id, output_base_dir = args
    
    try:
        # Create clients (each worker needs its own)
        auth = OAuth2Client(
            client_id=AUTH_CONFIG['client_id'],
            client_secret=AUTH_CONFIG['client_secret'],
            scopes=AUTH_CONFIG['scopes'],
            storage=KeyringStorage("batch-export-worker")
        )
        
        drive = DriveClient(auth)
        docs = DocsClient(auth)
        
        # Get file metadata
        item = drive.get_item(doc_id)
        
        # Check if file changed (simple caching)
        output_dir = output_base_dir / doc_id
        cache_file = output_dir / '.cache.json'
        
        if cache_file.exists():
            cache_data = json.loads(cache_file.read_text())
            if cache_data.get('modified_time') == item.modified_time:
                return {
                    'status': 'cached',
                    'doc_id': doc_id,
                    'title': item.name,
                    'message': 'File unchanged, skipped'
                }
        
        # Export document
        comments = drive.get_comments(doc_id)
        markdown, assets = docs.export(doc_id, comments=comments)
        
        # Save to disk
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save markdown
        (output_dir / 'content.md').write_text(markdown)
        
        # Save assets
        if assets:
            assets_dir = output_dir / 'assets'
            assets_dir.mkdir(exist_ok=True)
            for asset in assets:
                (assets_dir / asset.name).write_bytes(asset.content)
        
        # Save cache metadata
        cache_data = {
            'doc_id': doc_id,
            'title': item.name,
            'modified_time': item.modified_time,
            'exported_at': str(Path(output_dir).stat().st_mtime),
            'content_hash': hashlib.md5(markdown.encode()).hexdigest()
        }
        cache_file.write_text(json.dumps(cache_data, indent=2))
        
        return {
            'status': 'success',
            'doc_id': doc_id,
            'title': item.name,
            'assets': len(assets),
            'comments': len(comments)
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'doc_id': doc_id,
            'error': str(e)
        }


def batch_export_parallel(
    doc_ids: List[str],
    output_dir: Path,
    auth_config: dict,
    num_workers: int = 4
) -> List[dict]:
    """
    Export multiple documents in parallel.
    
    Args:
        doc_ids: List of document IDs to export
        output_dir: Base output directory
        auth_config: Dict with client_id, client_secret, scopes
        num_workers: Number of parallel workers
        
    Returns:
        List of result dicts
    """
    print(f"\n=== BATCH EXPORT: {len(doc_ids)} documents, {num_workers} workers ===\n")
    
    # Prepare arguments for each worker
    args = [(doc_id, output_dir) for doc_id in doc_ids]
    
    # Run in parallel
    with Pool(
        processes=num_workers,
        initializer=init_worker,
        initargs=(
            auth_config['client_id'],
            auth_config['client_secret'],
            auth_config['scopes']
        )
    ) as pool:
        results = pool.map(export_document_worker, args)
    
    # Print summary
    success_count = sum(1 for r in results if r['status'] == 'success')
    cached_count = sum(1 for r in results if r['status'] == 'cached')
    error_count = sum(1 for r in results if r['status'] == 'error')
    
    print(f"\n=== BATCH EXPORT COMPLETE ===")
    print(f"Success: {success_count}")
    print(f"Cached: {cached_count}")
    print(f"Errors: {error_count}")
    
    # Show details
    for result in results:
        if result['status'] == 'success':
            print(f"✓ {result['title']} ({result['doc_id']})")
        elif result['status'] == 'cached':
            print(f"⊙ {result['title']} (cached)")
        else:
            print(f"✗ {result['doc_id']}: {result['error']}")
    
    return results


def search_and_export(
    drive: DriveClient,
    search_query: str,
    limit: int,
    output_dir: Path,
    auth_config: dict
):
    """
    Search for documents and export them in parallel.
    
    Demonstrates a complete workflow: search → filter → batch export.
    """
    print(f"\n=== SEARCHING FOR: '{search_query}' ===")
    
    # Search for documents
    results = drive.search_by_name(search_query, limit=limit)
    
    # Filter to just Google Docs
    doc_ids = [
        item.id for item in results
        if item.type == ItemType.DOCS_DOCUMENT
    ]
    
    print(f"Found {len(doc_ids)} Google Docs")
    
    if not doc_ids:
        print("No documents to export")
        return
    
    # Batch export
    batch_export_parallel(doc_ids, output_dir, auth_config, num_workers=4)


if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()
    
    # Auth config
    auth_config = {
        'client_id': os.getenv('CLIENT_ID'),
        'client_secret': os.getenv('CLIENT_SECRET'),
        'scopes': os.getenv('CLIENT_SCOPES', '').split(',')
    }
    
    # Create main thread clients (for searching)
    auth = OAuth2Client(
        client_id=auth_config['client_id'],
        client_secret=auth_config['client_secret'],
        scopes=auth_config['scopes'],
        storage=KeyringStorage("batch-export-main")
    )
    
    drive = DriveClient(auth)
    
    # Output directory
    output_dir = Path(__file__).parent / "batch_exported"
    output_dir.mkdir(exist_ok=True)
    
    # Example 1: Export specific document IDs
    doc_ids = [
        "YOUR_DOCUMENT_ID_HERE",
        # Add more doc IDs here...
    ]
    
    batch_export_parallel(doc_ids, output_dir, auth_config, num_workers=4)
    
    # Example 2: Search and export
    # search_and_export(drive, "meeting notes", limit=10, output_dir=output_dir, auth_config=auth_config)
    
    # Example 3: Recursively export all docs in a folder
    # Replace with your folder ID (see MY_TEST_IDS.txt)
    # TEST_FOLDER_ID = "YOUR_FOLDER_ID_HERE"
    # folder_items = drive.list_items(folder_id=TEST_FOLDER_ID, recursive=True)
    # doc_ids = [item.id for item in folder_items if item.type == ItemType.DOCS_DOCUMENT]
    # batch_export_parallel(doc_ids, output_dir, auth_config, num_workers=4)
    
    print(f"\n✓ Batch export complete!")
    print(f"Output saved to: {output_dir}")

