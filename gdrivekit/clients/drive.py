from typing import List, Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import threading

from ..auth.client import create_client
from ..item import DriveItem, ItemType

import logging
logger = logging.getLogger(__name__)

class GDriveClient:
    def __init__(self, client_name: str, client_id: str, client_secret: str, scopes: list[str]):
        # Create OAuth client
        self.client = create_client(
        client_name=client_name,
            scopes=scopes,
            client_id=client_id,
            client_secret=client_secret
        )
        self.service = build('drive', 'v3', credentials=self.client.get_credentials())
        # Thread-local service storage for concurrent operations
        self._thread_local = threading.local()
        
        # Get Client User Information
        result = self.service.about().get(fields="user").execute()
        if not 'user' in result:
            raise ValueError("User information not found")
        self.user_id = result['user']['permissionId']
        self.user_name = result['user']['displayName']
        self.user_email = result['user']['emailAddress']
        self.drives = self.get_drives_info()
    
    def _get_service(self):
        """Get service object (thread-local if in batch mode, otherwise shared)."""
        if hasattr(self._thread_local, 'service'):
            return self._thread_local.service
        return self.service
    
    def _set_thread_service(self):
        """Create a thread-local service object for concurrent operations."""
        if not hasattr(self._thread_local, 'service'):
            self._thread_local.service = build('drive', 'v3', credentials=self.client.get_credentials())

    def get_user_info(self) -> dict:
        return {
            'id': self.user_id,
            'name': self.user_name,
            'email': self.user_email
        }

    def get_drives_info(self) -> List[DriveItem]:
        """
        List My Drive and all Shared Drives accessible to the client user.
        
        Returns:
            List of dictionaries containing 'id' and 'name' for each drive.
            First item is always My Drive.
        """
        self.drives = []
        
        # Get My Drive - use 'root' as the ID (standard for user's personal drive)
        root_drive = DriveItem(id='root')
        # Slight hack to add the right name to the root drive
        root_drive.populate(name='My Drive')
        self.drives.append(root_drive)
        
        # List all Shared Drives
        try:
            shared_drives = self._get_service().drives().list().execute()
            for drive in shared_drives.get('drives', []):
                self.drives.append(DriveItem(id=drive['id']))
        except Exception as e:
            # If the user doesn't have access to Shared Drives API or no shared drives exist
            pass
        
        return self.drives

    def get_item(self, item_id: str) -> DriveItem:
        """
        Fetch a DriveItem by ID from Google Drive API.
        
        Args:
            item_id: The ID of the item to fetch
            
        Returns:
            Fully populated DriveItem
            
        Raises:
            ValueError: If the file is not found or the API call fails
        """
        try:
            file_info = self._get_service().files().get(
                fileId=item_id,
                fields='id, name, createdTime, modifiedTime, mimeType, kind, capabilities, owners, appProperties, properties, exportLinks',
                supportsAllDrives=True
            ).execute()
            
            if not file_info:
                raise ValueError(f"File with ID '{item_id}' not found")
            
            item = DriveItem(id=item_id)
            return item.update_from_api(file_info)
        except Exception as e:
            raise ValueError(f"Failed to fetch file '{item_id}': {str(e)}") from e

    def list_items(self, parent_id: str, limit: int = None) -> List[DriveItem]:
        """
        List all items in a directory with pagination support.
        
        Args:
            parent_id: The ID of the parent directory
            limit: Optional maximum number of items to return. If None, returns all items.
            
        Returns:
            List of fully populated DriveItem objects
            
        Note:
            This method handles pagination automatically, fetching all pages until
            no more results exist or the limit is reached. Offset is not supported
            as the API uses token-based pagination.
        """
        drive_items = []
        page_token = None
        page_size = min(1000, limit) if limit else 1000  # API max is 1000
        
        while True:
            # Build request parameters
            request_params = {
                'q': f"'{parent_id}' in parents and trashed=false",
                'fields': 'nextPageToken, files(id, name, createdTime, modifiedTime, mimeType, kind, capabilities, owners, appProperties, properties)',
                'supportsAllDrives': True,
                'includeItemsFromAllDrives': True,
                'pageSize': page_size
            }
            
            if page_token:
                request_params['pageToken'] = page_token
            
            # Execute request
            response = self._get_service().files().list(**request_params).execute()
            items = response.get('files', [])
            
            # Process items
            for item_data in items:
                if limit and len(drive_items) >= limit:
                    return drive_items
                    
                item = DriveItem(id=item_data['id'])
                item.update_from_api(item_data)
                drive_items.append(item)
            
            # Check for next page
            page_token = response.get('nextPageToken')
            if not page_token:
                break
                
            # Adjust page size for next request if we're near the limit
            if limit:
                remaining = limit - len(drive_items)
                if remaining <= 0:
                    break
                page_size = min(1000, remaining)
        
        return drive_items
    
    def _collect_folder_ids_recursive(self, folder_id: str, visited: set = None) -> List[str]:
        """
        Recursively collect all folder IDs under a given folder (including the folder itself).
        
        Args:
            folder_id: The root folder ID to start from
            visited: Set of already visited folder IDs to prevent cycles
            
        Returns:
            List of all folder IDs including the root folder and all subfolders
        """
        if visited is None:
            visited = set()
        
        # Prevent circular references
        if folder_id in visited:
            return []
        
        visited.add(folder_id)
        folder_ids = [folder_id]
        
        try:
            # List all items in this folder
            items = self.list_items(folder_id)
            
            # Recursively collect subfolder IDs
            for item in items:
                if item.type == ItemType.DIRECTORY:
                    subfolder_ids = self._collect_folder_ids_recursive(item.id, visited)
                    folder_ids.extend(subfolder_ids)
        except Exception as e:
            logger.warning(f"Failed to list items in folder {folder_id}: {e}")
        
        return folder_ids
    
    def search_by_name(
        self,
        query: str,
        limit: int = 25,
        folder_id: Optional[str] = None
    ) -> List[DriveItem]:
        """
        Search for files by name across all drives (My Drive + Shared Drives).
        
        Args:
            query: Search query string to match against file names
            limit: Maximum number of results to return (default: 25)
            folder_id: Optional folder ID to restrict search to this folder and its subfolders
            
        Returns:
            List of DriveItem objects matching the search criteria
            
        Example:
            >>> client = GDriveClient(...)
            >>> results = client.search_by_name("meeting notes", limit=10)
            >>> for item in results:
            ...     print(f"{item.name} ({item.id})")
        """
        # Escape single quotes in query
        escaped_query = query.replace("'", "\\'")
        
        # Build base query
        search_query = f"name contains '{escaped_query}' and trashed=false"
        
        # Add folder restriction if specified
        if folder_id:
            logger.info(f"Collecting folder IDs for recursive search under {folder_id}")
            folder_ids = self._collect_folder_ids_recursive(folder_id)
            logger.info(f"Found {len(folder_ids)} folders to search in")
            
            # Build OR clause for all folders
            if folder_ids:
                escaped_folder_ids = [fid.replace("'", "\\'") for fid in folder_ids]
                folder_clauses = " or ".join([f"'{fid}' in parents" for fid in escaped_folder_ids])
                search_query = f"({search_query}) and ({folder_clauses})"
        
        logger.info(f"Searching by name: '{query}' (limit={limit})")
        
        # Execute search with pagination
        drive_items = []
        page_token = None
        page_size = min(1000, limit)
        
        while True:
            # Build request parameters
            request_params = {
                'q': search_query,
                'fields': 'nextPageToken, files(id, name, createdTime, modifiedTime, mimeType, kind, capabilities, owners, appProperties, properties)',
                'supportsAllDrives': True,
                'includeItemsFromAllDrives': True,
                'pageSize': page_size
            }
            
            if page_token:
                request_params['pageToken'] = page_token
            
            # Execute request
            response = self._get_service().files().list(**request_params).execute()
            items = response.get('files', [])
            
            # Process items
            for item_data in items:
                if len(drive_items) >= limit:
                    logger.info(f"Search by name returned {len(drive_items)} results")
                    return drive_items
                    
                item = DriveItem(id=item_data['id'])
                item.update_from_api(item_data)
                drive_items.append(item)
            
            # Check for next page
            page_token = response.get('nextPageToken')
            if not page_token:
                break
                
            # Adjust page size for next request if we're near the limit
            remaining = limit - len(drive_items)
            if remaining <= 0:
                break
            page_size = min(1000, remaining)
        
        logger.info(f"Search by name returned {len(drive_items)} results")
        return drive_items
    
    def search_by_content(
        self,
        query: str,
        limit: int = 25,
        folder_id: Optional[str] = None
    ) -> List[DriveItem]:
        """
        Search for files by full-text content across all drives (My Drive + Shared Drives).
        
        Args:
            query: Search query string to match against file contents
            limit: Maximum number of results to return (default: 25)
            folder_id: Optional folder ID to restrict search to this folder and its subfolders
            
        Returns:
            List of DriveItem objects matching the search criteria
            
        Note:
            Full-text search works for Google Docs, Sheets, Slides, and some binary formats.
            Not all file types support content search.
            
        Example:
            >>> client = GDriveClient(...)
            >>> results = client.search_by_content("quarterly revenue", limit=10)
            >>> for item in results:
            ...     print(f"{item.name} ({item.id})")
        """
        # Escape single quotes in query
        escaped_query = query.replace("'", "\\'")
        
        # Build base query
        search_query = f"fullText contains '{escaped_query}' and trashed=false"
        
        # Add folder restriction if specified
        if folder_id:
            logger.info(f"Collecting folder IDs for recursive search under {folder_id}")
            folder_ids = self._collect_folder_ids_recursive(folder_id)
            logger.info(f"Found {len(folder_ids)} folders to search in")
            
            # Build OR clause for all folders
            if folder_ids:
                escaped_folder_ids = [fid.replace("'", "\\'") for fid in folder_ids]
                folder_clauses = " or ".join([f"'{fid}' in parents" for fid in escaped_folder_ids])
                search_query = f"({search_query}) and ({folder_clauses})"
        
        logger.info(f"Searching by content: '{query}' (limit={limit})")
        
        # Execute search with pagination
        drive_items = []
        page_token = None
        page_size = min(1000, limit)
        
        while True:
            # Build request parameters
            request_params = {
                'q': search_query,
                'fields': 'nextPageToken, files(id, name, createdTime, modifiedTime, mimeType, kind, capabilities, owners, appProperties, properties)',
                'supportsAllDrives': True,
                'includeItemsFromAllDrives': True,
                'pageSize': page_size
            }
            
            if page_token:
                request_params['pageToken'] = page_token
            
            # Execute request
            response = self._get_service().files().list(**request_params).execute()
            items = response.get('files', [])
            
            # Process items
            for item_data in items:
                if len(drive_items) >= limit:
                    logger.info(f"Search by content returned {len(drive_items)} results")
                    return drive_items
                    
                item = DriveItem(id=item_data['id'])
                item.update_from_api(item_data)
                drive_items.append(item)
            
            # Check for next page
            page_token = response.get('nextPageToken')
            if not page_token:
                break
                
            # Adjust page size for next request if we're near the limit
            remaining = limit - len(drive_items)
            if remaining <= 0:
                break
            page_size = min(1000, remaining)
        
        logger.info(f"Search by content returned {len(drive_items)} results")
        return drive_items
    
    def update_properties(
        self,
        item: DriveItem,
        properties: dict[str, str],
        global_props: bool = False
    ) -> DriveItem:
        """
        Update file properties via Google Drive API.
        
        Args:
            item: The DriveItem to update
            properties: Dictionary of properties to set
            global_props: If True, updates properties (global). If False, updates appProperties (app-specific)
            
        Returns:
            Updated DriveItem (refreshed from API)
            
        Raises:
            ValueError: If the update fails
        """
        try:
            # Filter None values - those need to be explicitly deleted
            props_to_set = {k: v for k, v in properties.items() if v is not None}
            props_to_delete = [k for k, v in properties.items() if v is None]
            
            update_body = {}
            prop_key = 'properties' if global_props else 'appProperties'
            
            # Set non-None properties
            if props_to_set:
                update_body[prop_key] = props_to_set
            
            self._get_service().files().update(
                fileId=item.id,
                body=update_body,
                fields='id',
                supportsAllDrives=True
            ).execute()
            
            # Delete None properties separately
            for prop in props_to_delete:
                delete_body = {prop_key: {prop: None}}
                self._get_service().files().update(
                    fileId=item.id,
                    body=delete_body,
                    fields='id',
                    supportsAllDrives=True
                ).execute()
            
            # Refresh and return updated item
            return self.get_item(item.id)
        except Exception as e:
            raise ValueError(f"Failed to update properties for file '{item.id}': {str(e)}") from e

    def download_file(
        self,
        item: DriveItem,
        filesystem_path: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Download raw binary data from a Drive file.
        
        Args:
            item: The DriveItem to download
            filesystem_path: Optional path to save file on disk. If None, returns bytes in memory.
            
        Returns:
            bytes if filesystem_path is None, otherwise None (file saved to disk)
            
        Raises:
            ValueError: If item is a Google Docs type or directory, or download fails
        """
        # Check if item is a directory or Google Docs type
        if item.type == ItemType.DIRECTORY:
            raise ValueError(f"Cannot download directory: {item.name}")
        
        if item.type in [ItemType.DOCS_DOCUMENT, ItemType.DOCS_SLIDES, ItemType.DOCS_SHEETS]:
            raise ValueError(f"Cannot download Google Docs type: {item.type.value}. Use export instead.")
        
        try:
            # Request file download
            request = self._get_service().files().get_media(fileId=item.id, supportsAllDrives=True)
            
            # Download to memory buffer
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            # Get the binary data
            file_buffer.seek(0)
            binary_data = file_buffer.read()
            
            # Save to disk or return bytes
            if filesystem_path:
                with open(filesystem_path, 'wb') as f:
                    f.write(binary_data)
                return None
            else:
                return binary_data
                
        except Exception as e:
            raise ValueError(f"Failed to download file '{item.id}': {str(e)}") from e

    def get_comments(self, file_id: str) -> List[dict]:
        """
        Get all comments for a file.
        
        Args:
            file_id: The file ID
            
        Returns:
            List of comment dictionaries
        """
        try:
            comments = []
            page_token = None
            
            while True:
                response = self._get_service().comments().list(
                    fileId=file_id,
                    fields='nextPageToken, comments(id, content, author, createdTime, modifiedTime, quotedFileContent, replies, resolved, anchor)',
                    pageToken=page_token,
                    includeDeleted=False
                ).execute()
                
                comments.extend(response.get('comments', []))
                
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
            
            logger.info(f"Retrieved {len(comments)} comments for file {file_id}")
            # Okay, let's format the comments and replies into something a little cleaner.
            formatted_comments = []
            for comment in comments:
                # Format the comment time to be YYYY-MM-DD HH:MM
                created_dt = datetime.fromisoformat(comment['createdTime'].replace('Z', '+00:00'))
                modified_dt = datetime.fromisoformat(comment['modifiedTime'].replace('Z', '+00:00'))
                formatted_comment = {
                    'id': comment['id'],
                    'author': comment.get('author', {}).get('displayName', 'Unknown'),
                    'content': comment.get('content', ''),
                    'snippet': comment.get('quotedFileContent', {}).get('value', ''),
                    'createdTime': created_dt.strftime('%Y-%m-%d %H:%M'),
                    'modifiedTime': modified_dt.strftime('%Y-%m-%d %H:%M'),
                    'resolved': comment.get('resolved', False),
                    'anchor': comment.get('anchor', ''),
                    'replies': []
                }
                for reply in comment.get('replies', []):
                    # Format these to be YYYY-MM-DD HH:MM
                    reply_created_dt = datetime.fromisoformat(reply['createdTime'].replace('Z', '+00:00'))
                    reply_modified_dt = datetime.fromisoformat(reply['modifiedTime'].replace('Z', '+00:00'))
                    formatted_comment['replies'].append({
                        'id': reply['id'],
                        'author': reply.get('author', {}).get('displayName', 'Unknown'),
                        'content': reply.get('content', ''),
                        'createdTime': reply_created_dt.strftime('%Y-%m-%d %H:%M'), 
                        'modifiedTime': reply_modified_dt.strftime('%Y-%m-%d %H:%M'),
                    })
                formatted_comments.append(formatted_comment)
            return formatted_comments
        except Exception as e:
            logger.error(f"Error getting comments for file {file_id}: {e}")
            # Return empty list if comments API fails (some files don't support comments)
            return []

    def reply_to_comment(self, file_id: str, comment_id: str, content: str) -> dict:
        """
        Reply to a comment.
        
        Args:
            file_id: The file ID
            comment_id: The comment ID
            content: The content of the reply
        """
        try:
            response = self._get_service().replies().create(
                fileId=file_id,
                commentId=comment_id,
                body={'content': content},
                fields='id'
            ).execute()
            return response
        except Exception as e:
            raise ValueError(f"Failed to reply to comment {comment_id} for file {file_id}: {str(e)}") from e

    def check_item_access(self, item_id: str) -> bool:
        """
        Check if the current user has access to a file.
        """
        try:
            self._get_service().files().get(fileId=item_id, supportsAllDrives=True).execute()
            return True
        except Exception as e:
            return False
        except Exception as e:
            raise ValueError(f"Failed to check item access for {item_id}: {str(e)}") from e

    def get_labels(self, item_id: str) -> List[dict]:
        """
        Get the labels applied to a file.
        
        Args:
            item_id: The item ID
            
        Returns:
            List of labels applied to the file
        """
        try:
            response = self._get_service().files().listLabels(fileId=item_id).execute()
            return response.get('labels', [])
        except Exception as e:
            raise ValueError(f"Failed to get labels for item {item_id}: {str(e)}") from e

    def export_document(
        self,
        item_id: str,
        output_type: str = "markdown",
        save_to_disk: bool = False,
        cache_base_path: str = "./exported_docs"
    ):
        """
        Export a Google Workspace document (Docs, Sheets, Slides) to a more AI-friendly format.
        
        This method exports documents to either PDF or Markdown format. For Markdown, it converts
        from HTML with proper asset extraction and comment anchor preservation. The result can be
        kept in memory or cached to disk in a structured format.
        
        Args:
            item_id: The Google Drive file ID
            output_type: Export format - "markdown" or "pdf" (default: "markdown")
            save_to_disk: If True, cache the export to disk (default: False)
            cache_base_path: Base directory for disk cache (default: "./exported_docs")
            
        Returns:
            ExportedItem object containing the exported document with content, assets, and comments
            
        Raises:
            ValueError: If the item is not an exportable document type or export fails
            
        Example:
            >>> client = GDriveClient(...)
            >>> exported = client.export_document("1abc123xyz", output_type="markdown")
            >>> print(exported.content)  # Markdown content
            >>> print(len(exported.assets))  # Number of extracted images/charts
            >>> print(len(exported.comments))  # Number of comments with anchors
        """
        from ..export.models import ExportedItem
        from ..export import cache
        from ..export.docs import exporters as docs_exporters, converters as docs_converters
        from ..export.slides import exporters as slides_exporters, converters as slides_converters
        from ..export.sheets import exporters as sheets_exporters, converters as sheets_converters
        
        # Step 1: Get item metadata
        logger.info(f"Exporting document {item_id} to {output_type}")
        item = self.get_item(item_id)
        
        # Step 2: Validate item type is exportable
        exportable_types = [ItemType.DOCS_DOCUMENT, ItemType.DOCS_SHEETS, ItemType.DOCS_SLIDES]
        if item.type not in exportable_types:
            raise ValueError(
                f"Cannot export item of type {item.type}. "
                f"Only Google Docs, Sheets, and Slides are supported."
            )
        
        # Step 3: Validate output type
        if output_type not in ["markdown", "pdf"]:
            raise ValueError(f"Invalid output_type: {output_type}. Must be 'markdown' or 'pdf'")
        
        # Step 4: Fetch comments (for Docs and Slides)
        comments = []
        if item.type in [ItemType.DOCS_DOCUMENT, ItemType.DOCS_SLIDES]:
            logger.info(f"Fetching comments for {item_id}")
            comments = self.get_comments(item_id)
        
        # Step 5: Export based on document type and output type
        if item.type == ItemType.DOCS_DOCUMENT:
            if output_type == "markdown":
                # Export to native markdown first (clean content)
                logger.info(f"Exporting {item_id} to Markdown")
                markdown_content = docs_exporters.export_docs_to_markdown(self._get_service(), item)
                
                # Export to HTML to get comment positions
                logger.info(f"Exporting {item_id} to HTML for comment positioning")
                html_content = docs_exporters.export_docs_to_html(self._get_service(), item)
                
                # Process markdown with HTML for comment positioning
                logger.info(f"Processing markdown export for {item_id}")
                markdown_content, assets = docs_converters.process_docs_markdown_export(
                    markdown_content,
                    html_content,
                    comments
                )
                
                content = markdown_content
                content_format = "markdown"
            else:  # pdf
                logger.info(f"Exporting {item_id} to PDF")
                pdf_content = docs_exporters.export_docs_to_pdf(self._get_service(), item)
                content = pdf_content
                content_format = "pdf"
                assets = []
                
        elif item.type == ItemType.DOCS_SLIDES:
            if output_type == "markdown":
                logger.info(f"Exporting Slides {item_id} to Markdown via API")
                
                # Fetch presentation data via Slides API
                presentation_data = slides_exporters.export_slides_via_api(
                    client_name=self.client.client_name,
                    client_id=self.client.client_id,
                    client_secret=self.client.client_secret,
                    scopes=self.client.scopes,
                    presentation_id=item_id
                )
                
                # Convert to markdown with comments
                logger.info(f"Converting Slides data to markdown")
                markdown_content, assets = slides_converters.convert_slides_to_markdown(
                    presentation_data,
                    comments
                )
                
                content = markdown_content
                content_format = "markdown"
            else:  # pdf
                logger.info(f"Exporting Slides {item_id} to PDF")
                pdf_content = slides_exporters.export_slides_to_pdf(self._get_service(), item)
                content = pdf_content
                content_format = "pdf"
                assets = []
            
        elif item.type == ItemType.DOCS_SHEETS:
            if output_type == "markdown":
                # Import sheets client
                from .sheets import GDriveSheetsClient
                from googleapiclient.errors import HttpError
                
                logger.info(f"Exporting Sheets {item_id} to Markdown")
                
                # Fetch comments
                logger.info(f"Fetching comments for {item_id}")
                comments = self.get_comments(item_id)
                
                # Create Sheets API client
                logger.info(f"Creating Sheets API client")
                sheets_client = GDriveSheetsClient(
                    client_name=self.client.client_name,
                    client_id=self.client.client_id,
                    client_secret=self.client.client_secret,
                    scopes=self.client.scopes
                )
                
                # Fetch spreadsheet data with better error handling
                logger.info(f"Fetching spreadsheet data")
                try:
                    sheets_data = sheets_client.fetch_spreadsheet_data(item_id)
                except ValueError as e:
                    # Check if this is a Sheets API access error
                    error_str = str(e)
                    if 'SERVICE_DISABLED' in error_str or 'has not been used' in error_str:
                        raise ValueError(
                            f"Google Sheets API is not enabled for this project. "
                            f"Markdown export for Sheets requires the Sheets API v4. "
                            f"Either:\n"
                            f"  1. Enable Sheets API in Google Cloud Console for your OAuth client\n"
                            f"  2. Use output_type='pdf' instead (doesn't require Sheets API)\n"
                            f"Original error: {e}"
                        ) from e
                    elif '403' in error_str or 'PERMISSION_DENIED' in error_str:
                        raise ValueError(
                            f"Insufficient permissions to access Google Sheets API. "
                            f"Your OAuth client may need additional scopes. "
                            f"Try adding 'https://www.googleapis.com/auth/spreadsheets.readonly' to your scopes.\n"
                            f"Original error: {e}"
                        ) from e
                    else:
                        # Re-raise other errors as-is
                        raise
                
                # Convert to markdown
                logger.info(f"Converting sheets data to markdown")
                markdown_content = sheets_converters.convert_sheets_to_markdown(
                    sheets_data,
                    comments
                )
                
                # Extract assets from HTML export (for charts/images) if available
                assets = []
                if 'text/html' in item.export_links:
                    logger.info(f"Extracting assets from HTML export")
                    try:
                        html_content = sheets_exporters.export_sheets_to_html(self._get_service(), item)
                        _, assets = sheets_converters.extract_assets_from_sheets_html(html_content)
                    except Exception as e:
                        logger.debug(f"Could not extract assets from HTML: {e}")
                else:
                    logger.debug(f"HTML export not available, skipping asset extraction")
                
                content = markdown_content
                content_format = "markdown"
                
            else:  # pdf
                logger.info(f"Exporting Sheets {item_id} to PDF")
                pdf_content = sheets_exporters.export_sheets_to_pdf(self._get_service(), item)
                content = pdf_content
                content_format = "pdf"
                assets = []
        
        # Step 6: Build ExportedItem
        exported_item = ExportedItem(
            item_id=item_id,
            item_type=item.type,
            title=item.name,
            created_time=item.created_time,
            modified_time=item.modified_time,
            content=content,
            content_format=content_format,
            assets=assets,
            comments=comments
        )
        
        # Step 7: Save to disk if requested
        if save_to_disk:
            logger.info(f"Saving exported item to disk: {cache_base_path}")
            cache.save_to_disk(exported_item, cache_base_path)
        
        logger.info(f"Export complete: {item.name} ({content_format})")
        return exported_item

    def _process_single_item(
        self,
        item: DriveItem,
        output_path: str,
        output_type: str,
        parent_path: str = None
    ) -> dict:
        """
        Process a single item for batch export.
        
        Args:
            item: DriveItem to process
            output_path: Base path for exports
            output_type: "markdown" or "pdf"
            parent_path: Optional parent directory path for hierarchical exports
            
        Returns:
            dict with result information: {"status": "success"|"failure"|"skipped", "item_id", "name", "type", ...}
        """
        try:
            item_type = item.type
            
            # Determine actual export path (hierarchical if parent_path provided)
            if parent_path:
                actual_output_path = str(Path(parent_path) / "children" / item.id)
            else:
                actual_output_path = str(Path(output_path) / item.id)
            
            # Handle directories - skip them in single item processing
            if item_type == ItemType.DIRECTORY:
                return {
                    "status": "skipped",
                    "item_id": item.id,
                    "name": item.name,
                    "reason": "Directory (not a file)"
                }
            
            # Check if we should skip based on cache  
            if item_type in [ItemType.DOCS_DOCUMENT, ItemType.DOCS_SLIDES, ItemType.DOCS_SHEETS]:
                from .export import cache
                # Check cache in the actual output location
                check_path = Path(actual_output_path).parent if parent_path else output_path
                if cache.should_skip_export(item.id, item.modified_time, str(check_path)):
                    logger.info(f"Skipping {item.name} (already up-to-date)")
                    return {
                        "status": "skipped",
                        "item_id": item.id,
                        "name": item.name,
                        "reason": "Already up-to-date"
                    }
                
                # Export workspace document
                logger.info(f"Exporting {item.name} ({item_type.value})")
                # For hierarchical exports, we need to save directly to the item folder
                if parent_path:
                    # Create the item directory and save there
                    item_dir = Path(actual_output_path)
                    item_dir.mkdir(parents=True, exist_ok=True)
                    exported_item = self.export_document(
                        item.id,
                        output_type=output_type,
                        save_to_disk=True,
                        cache_base_path=str(item_dir.parent)
                    )
                else:
                    exported_item = self.export_document(
                        item.id,
                        output_type=output_type,
                        save_to_disk=True,
                        cache_base_path=output_path
                    )
                
                return {
                    "status": "success",
                    "item_id": item.id,
                    "name": item.name,
                    "type": item_type.value,
                    "path": actual_output_path
                }
            
            elif item_type == ItemType.RAW_FILE:
                from .export import cache
                # Check if raw file already exists
                if cache.raw_file_exists(item.id, item.name, output_path):
                    logger.info(f"Skipping {item.name} (already downloaded)")
                    return {
                        "status": "skipped",
                        "item_id": item.id,
                        "name": item.name,
                        "reason": "Already downloaded"
                    }
                
                # Download raw file
                logger.info(f"Downloading {item.name}")
                item_dir = Path(actual_output_path)
                item_dir.mkdir(parents=True, exist_ok=True)
                file_path = item_dir / item.name
                
                self.download_file(item, filesystem_path=str(file_path))
                
                return {
                    "status": "success",
                    "item_id": item.id,
                    "name": item.name,
                    "type": item_type.value,
                    "path": str(file_path)
                }
            
            else:
                return {
                    "status": "skipped",
                    "item_id": item.id,
                    "name": item.name,
                    "reason": f"Unsupported type: {item_type.value}"
                }
                
        except Exception as e:
            logger.error(f"Failed to process {item.name}: {e}")
            return {
                "status": "failure",
                "item_id": item.id,
                "name": item.name,
                "error": str(e)
            }

    def batch_export_by_ids(
        self,
        item_ids: List[str],
        output_path: str = "./exported_docs",
        output_type: str = "markdown",
        max_workers: int = 5
    ):
        """
        Batch export/download multiple files by their IDs.
        
        This method processes a list of file IDs in parallel, downloading raw files
        and exporting Google Workspace documents. Files can be from any location in Drive.
        
        Args:
            item_ids: List of Google Drive file IDs to export
            output_path: Base directory for exports (default: "./exported_docs")
            output_type: Export format - "markdown" or "pdf" (default: "markdown")
            max_workers: Number of concurrent workers (default: 5)
            
        Returns:
            BatchExportResult with successes, failures, and skipped items
            
        Example:
            >>> result = client.batch_export_by_ids(["file1", "file2", "file3"])
            >>> print(f"Exported: {len(result.successes)}, Failed: {len(result.failures)}")
        """
        from .export.models import BatchExportResult
        
        logger.info(f"Starting batch export of {len(item_ids)} items with {max_workers} workers")
        
        # Thread-safe result collection
        results_lock = threading.Lock()
        successes = []
        failures = []
        skipped = []
        
        # Thread-local storage for service objects (googleapiclient is NOT thread-safe)
        thread_local = threading.local()
        
        def get_thread_service():
            """Get or create a thread-local service object."""
            if not hasattr(thread_local, 'service'):
                thread_local.service = build('drive', 'v3', credentials=self.client.get_credentials())
            return thread_local.service
        
        def process_item_wrapper(item_id: str):
            """Wrapper to fetch item and process it."""
            try:
                # Set up thread-local service to avoid SSL corruption
                self._set_thread_service()
                
                # Fetch item using thread-local service
                file_info = self._get_service().files().get(
                    fileId=item_id,
                    fields='id, name, createdTime, modifiedTime, mimeType, kind, capabilities, owners, appProperties, properties, exportLinks',
                    supportsAllDrives=True
                ).execute()
                
                item = DriveItem(id=item_id)
                item.update_from_api(file_info)
                
                result = self._process_single_item(item, output_path, output_type)
                
                with results_lock:
                    if result["status"] == "success":
                        successes.append(result)
                    elif result["status"] == "failure":
                        failures.append(result)
                    elif result["status"] == "skipped":
                        skipped.append(result)
                        
            except Exception as e:
                logger.error(f"Failed to fetch item {item_id}: {e}")
                with results_lock:
                    failures.append({
                        "item_id": item_id,
                        "name": "Unknown",
                        "error": f"Failed to fetch item: {str(e)}"
                    })
        
        # Process items in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_item_wrapper, item_id) for item_id in item_ids]
            
            # Wait for all to complete
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Unexpected error in worker: {e}")
        
        total = len(successes) + len(failures) + len(skipped)
        logger.info(f"Batch export complete: {len(successes)} succeeded, {len(failures)} failed, {len(skipped)} skipped")
        
        return BatchExportResult(
            total_processed=total,
            successes=successes,
            failures=failures,
            skipped=skipped
        )

    def batch_export(
        self,
        folder_id: str,
        output_path: str = "./exported_docs",
        depth: Optional[int] = None,
        output_type: str = "markdown",
        max_workers: int = 5
    ):
        """
        Recursively export/download all files in a folder with hierarchical structure.
        
        This is a convenience method that exports a single folder. For multiple folders
        or mixed files/folders, use batch_export_by_ids() instead.
        
        The exported structure preserves hierarchy:
        - Each folder gets metadata.json with folder info
        - Files/subfolders are placed in a "children" subdirectory
        - Nested folders maintain the same structure recursively
        
        Args:
            folder_id: Folder ID to export from
            output_path: Base directory for exports (default: "./exported_docs")
            depth: Maximum depth to traverse (None = infinite, 0 = current folder only)
            output_type: Export format - "markdown" or "pdf" (default: "markdown")
            max_workers: Number of concurrent workers (default: 5)
            
        Returns:
            BatchExportResult with successes, failures, and skipped items
            
        Example:
            >>> # Export entire folder recursively
            >>> result = client.batch_export("folder_id_here")
            >>> 
            >>> # Export only current folder (depth=0)
            >>> result = client.batch_export("folder_id_here", depth=0)
        """
        from .export.models import BatchExportResult
        
        logger.info(f"Starting batch export from folder {folder_id} (depth={depth})")
        
        # Thread-safe result collection
        results_lock = threading.Lock()
        successes = []
        failures = []
        skipped = []
        
        def collect_and_export_recursive(
            current_folder_id: str, 
            current_folder_item: DriveItem,
            current_depth: int,
            parent_export_path: str = None,
            visited: set = None
        ):
            """Recursively collect and export items, preserving folder structure."""
            if visited is None:
                visited = set()
            
            # Prevent circular references
            if current_folder_id in visited:
                logger.warning(f"Skipping already visited folder: {current_folder_id}")
                return
            
            visited.add(current_folder_id)
            
            # Determine folder export path
            if parent_export_path:
                folder_export_path = str(Path(parent_export_path) / "children" / current_folder_id)
            else:
                folder_export_path = str(Path(output_path) / current_folder_id)
            
            try:
                # Create folder metadata
                folder_dir = Path(folder_export_path)
                folder_dir.mkdir(parents=True, exist_ok=True)
                
                metadata = {
                    "item_id": current_folder_id,
                    "item_type": "directory",
                    "name": current_folder_item.name if current_folder_item else "Root",
                    "created_time": current_folder_item.created_time if current_folder_item else None,
                    "modified_time": current_folder_item.modified_time if current_folder_item else None,
                }
                
                metadata_path = folder_dir / "metadata.json"
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
                
                # List all items in current folder
                logger.info(f"Listing items in folder (depth={current_depth})")
                items = self.list_items(current_folder_id)
                logger.info(f"Found {len(items)} items at depth {current_depth}")
                
                # Create children directory
                children_dir = folder_dir / "children"
                children_dir.mkdir(exist_ok=True)
                
                for item in items:
                    if item.type == ItemType.DIRECTORY:
                        # If we haven't reached depth limit, recurse into subdirectory
                        if depth is None or current_depth < depth:
                            logger.info(f"Recursing into folder: {item.name} (depth {current_depth + 1})")
                            collect_and_export_recursive(
                                item.id, 
                                item,
                                current_depth + 1,
                                folder_export_path,
                                visited
                            )
                    else:
                        # Process file with hierarchical path
                        result = self._process_single_item(item, output_path, output_type, folder_export_path)
                        
                        with results_lock:
                            if result["status"] == "success":
                                successes.append(result)
                            elif result["status"] == "failure":
                                failures.append(result)
                            elif result["status"] == "skipped":
                                skipped.append(result)
                        
            except Exception as e:
                logger.error(f"Failed to process folder {current_folder_id}: {e}")
                with results_lock:
                    failures.append({
                        "item_id": current_folder_id,
                        "name": current_folder_item.name if current_folder_item else "Unknown",
                        "error": f"Failed to process folder: {str(e)}"
                    })
        
        # Fetch root folder item
        logger.info(f"Fetching folder metadata for {folder_id}")
        try:
            root_folder_item = self.get_item(folder_id)
        except Exception as e:
            logger.error(f"Failed to fetch folder {folder_id}: {e}")
            root_folder_item = None
        
        # Recursively collect and export with hierarchical structure
        logger.info("Starting hierarchical export...")
        self._set_thread_service()  # Set up thread-local for main thread
        collect_and_export_recursive(folder_id, root_folder_item, 0)
        
        total = len(successes) + len(failures) + len(skipped)
        logger.info(f"Batch export complete: {len(successes)} succeeded, {len(failures)} failed, {len(skipped)} skipped")
        
        return BatchExportResult(
            total_processed=total,
            successes=successes,
            failures=failures,
            skipped=skipped
        )

    