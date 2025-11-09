"""
Google Sheets API v4 Client

WHY SHEETS API v4 INSTEAD OF DRIVE API v3?

The Drive API v3 can only export entire spreadsheets as opaque files (HTML, PDF, CSV, etc.).
It treats a spreadsheet as a single exportable document with no structured access to:
  - Individual sheet tabs within a workbook
  - Raw cell values in their native format
  - Sheet metadata (names, IDs, grid properties)
  - Cell-by-cell or range-based data access

The Sheets API v4 provides programmatic access to spreadsheet structure:
  - spreadsheets().get() - Fetch metadata for all sheets/tabs in a workbook
  - spreadsheets().values().batchGet() - Retrieve cell data from multiple ranges at once
  - Structured data as 2D arrays (rows/columns) instead of rendered HTML
  - Control over value rendering (FORMATTED_VALUE, UNFORMATTED_VALUE, FORMULA)
  - Access to individual sheets within a multi-tab spreadsheet

For our markdown export use case, we need:
  1. To iterate through all sheet tabs individually (each becomes a markdown section)
  2. To access raw cell data as arrays for table generation
  3. To match comment snippets against actual cell values
  4. To preserve formula errors like #N/A (requires FORMATTED_VALUE option)

None of this is possible with Drive API exports alone, which is why we use Sheets API v4.
"""
from typing import List, Dict, Any
from googleapiclient.discovery import build

from ..auth.client import create_client

import logging
logger = logging.getLogger(__name__)


class GDriveSheetsClient:
    """
    Client for Google Sheets API (v4).
    
    Used for accessing spreadsheet data directly via the Sheets API
    instead of using Drive export links.
    """
    
    def __init__(self, client_name: str, client_id: str, client_secret: str, scopes: list[str]):
        """
        Initialize the Sheets API client.
        
        Args:
            client_name: Name for the OAuth client
            client_id: OAuth client ID
            client_secret: OAuth client secret
            scopes: List of OAuth scopes (must include spreadsheets read scope)
        """
        self.client = create_client(
            client_name=client_name,
            scopes=scopes,
            client_id=client_id,
            client_secret=client_secret
        )
        self.service = build('sheets', 'v4', credentials=self.client.get_credentials())
    
    def fetch_spreadsheet_data(self, spreadsheet_id: str) -> List[Dict[str, Any]]:
        """
        Fetch all sheets and their data from a Google Spreadsheet.
        
        Args:
            spreadsheet_id: The Google Sheets file ID
            
        Returns:
            List of dictionaries containing sheet metadata and data:
            [
                {
                    'sheet_name': 'Sheet1',
                    'sheet_id': 0,
                    'data_rows': [['Header1', 'Header2'], ['Value1', 'Value2'], ...]
                },
                ...
            ]
        """
        try:
            # Step 1: Get spreadsheet metadata to find all sheet names and IDs
            logger.info(f"Fetching spreadsheet metadata for {spreadsheet_id}")
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id,
                fields='sheets.properties'
            ).execute()
            
            sheets_metadata = spreadsheet.get('sheets', [])
            if not sheets_metadata:
                logger.warning(f"No sheets found in spreadsheet {spreadsheet_id}")
                return []
            
            # Step 2: Build ranges for batch fetch (all data from each sheet)
            ranges = []
            sheet_info = []
            for sheet in sheets_metadata:
                props = sheet.get('properties', {})
                sheet_name = props.get('title', 'Untitled')
                sheet_id = props.get('sheetId', 0)
                
                # Use A1 notation to fetch entire sheet
                ranges.append(f"'{sheet_name}'")
                sheet_info.append({
                    'sheet_name': sheet_name,
                    'sheet_id': sheet_id
                })
            
            logger.info(f"Fetching data for {len(ranges)} sheets")
            
            # Step 3: Batch fetch all sheet data
            # Use FORMATTED_VALUE to get what the user sees (including errors like #N/A)
            result = self.service.spreadsheets().values().batchGet(
                spreadsheetId=spreadsheet_id,
                ranges=ranges,
                valueRenderOption='FORMATTED_VALUE',  # Get formatted strings including error values
                dateTimeRenderOption='FORMATTED_STRING'  # Keep dates as readable strings
            ).execute()
            
            value_ranges = result.get('valueRanges', [])
            
            # Step 4: Combine metadata with data
            sheets_data = []
            for idx, value_range in enumerate(value_ranges):
                data_rows = value_range.get('values', [])
                
                sheets_data.append({
                    'sheet_name': sheet_info[idx]['sheet_name'],
                    'sheet_id': sheet_info[idx]['sheet_id'],
                    'data_rows': data_rows
                })
                
                logger.debug(f"Fetched {len(data_rows)} rows from sheet '{sheet_info[idx]['sheet_name']}'")
            
            logger.info(f"Successfully fetched data from {len(sheets_data)} sheets")
            return sheets_data
            
        except Exception as e:
            raise ValueError(f"Failed to fetch spreadsheet data for {spreadsheet_id}: {str(e)}") from e

