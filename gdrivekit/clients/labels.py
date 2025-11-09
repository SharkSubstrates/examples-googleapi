from typing import List
from googleapiclient.discovery import build

from ..auth.client import create_client

import logging
logger = logging.getLogger(__name__)


"""A developer's guide to Google Drive Labels API v2 scopes.

https://www.googleapis.com/auth/drive.labels.readonly
    - USE: Read labels and their values *on* files.

https://www.googleapis.com/auth/drive.labels
    - USE: Read/write *SHARED* labels and their values *on* files.

https://www.googleapis.com/auth/drive.admin.labels.readonly
    - USE: Read the organization's label definitions (taxonomy).

https://www.googleapis.com/auth/drive.admin.labels
    - USE: Read/write the organization's label definitions (create/edit/delete).
"""

class GDriveLabelsClient:
    """
    Client for Google Drive Labels API (v2).
    
    Used for enterprise label management - listing label definitions,
    getting labels applied to files, etc. Most automation agents won't need this.
    """
    
    def __init__(self, client_name: str, client_id: str, client_secret: str, scopes: list[str]):
        """
        Initialize the Labels API client.
        
        Args:
            client_name: Name for the OAuth client
            client_id: OAuth client ID
            client_secret: OAuth client secret
            scopes: List of OAuth scopes (e.g., ['https://www.googleapis.com/auth/drive.labels.readonly'])
        """
        self.client = create_client(
            client_name=client_name,
            scopes=scopes,
            client_id=client_id,
            client_secret=client_secret
        )
        self.service = build('drivelabels', 'v2', credentials=self.client.get_credentials())
    
    def list_all_labels(self) -> List[dict]:
        """
        List all label definitions available to the user.
        
        Returns:
            List of label definition dictionaries
        """
        try:
            response = self.service.labels().list().execute()
            return response.get('labels', [])
        except Exception as e:
            raise ValueError(f"Failed to list all labels: {str(e)}") from e
    
    def get_label(self, label_id: str) -> dict:
        """
        Get a specific label definition by ID.
        
        Args:
            label_id: The label ID
            
        Returns:
            Label definition dictionary
        """
        try:
            response = self.service.labels().get(name=f'labels/{label_id}').execute()
            return response
        except Exception as e:
            raise ValueError(f"Failed to get label {label_id}: {str(e)}") from e

