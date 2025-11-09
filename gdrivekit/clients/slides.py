"""
Google Slides API v1 Client

WHY SLIDES API v1 INSTEAD OF DRIVE API v3?

The Drive API v3 can only export entire presentations as opaque files (HTML, PDF, PPTX).
It treats a presentation as a single exportable document with no structured access to:
  - Individual slides within a presentation
  - Text content from specific shapes and text boxes
  - Speaker notes for each slide
  - Image URLs and metadata
  - Proper slide ordering and layout information

The Slides API v1 provides programmatic access to presentation structure:
  - presentations().get() - Fetch complete presentation with all slides
  - Access to pageElements[] for each slide (shapes, images, tables, etc.)
  - Direct access to speaker notes via slideProperties.notesPage
  - Image URLs for downloading and caching
  - Structured text content instead of rendered HTML

For our markdown export use case, we need:
  1. To iterate through all slides individually (each becomes a markdown section)
  2. To extract text content from shapes and text boxes for slide content
  3. To access speaker notes for each slide
  4. To download images and save them to assets folder
  5. To match comment snippets against actual slide text

None of this is possible with Drive API exports alone, which is why we use Slides API v1.
"""
from typing import List, Dict, Any
from googleapiclient.discovery import build

from ..auth.client import create_client

import logging
logger = logging.getLogger(__name__)

class GDriveSlidesClient:
    """
    Client for Google Slides API (v1).
    
    Used for accessing presentation data directly via the Slides API
    instead of using Drive export links.
    """
    
    def __init__(self, client_name: str, client_id: str, client_secret: str, scopes: list[str]):
        """
        Initialize the Slides API client.
        
        Args:
            client_name: Name for the OAuth client
            client_id: OAuth client ID
            client_secret: OAuth client secret
            scopes: List of OAuth scopes (must include presentations read scope)
        """
        self.client_name = client_name
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes
        
        self.client = create_client(
            client_name=client_name,
            scopes=scopes,
            client_id=client_id,
            client_secret=client_secret
        )
        self.service = build('slides', 'v1', credentials=self.client.get_credentials())
    
    def fetch_presentation_data(self, presentation_id: str) -> Dict[str, Any]:
        """
        Fetch complete presentation with all slides, text content, speaker notes, and images.
        
        Args:
            presentation_id: The Google Slides presentation ID
            
        Returns:
            Dictionary containing presentation metadata and slides:
            {
                'presentation_id': '...',
                'title': 'Presentation Title',
                'slides': [
                    {
                        'slide_index': 0,
                        'object_id': 'slide_id_123',
                        'text_content': 'Combined text from all text elements',
                        'text_elements': [
                            {'text': 'Text from shape 1', 'type': 'SHAPE'},
                            {'text': 'Text from shape 2', 'type': 'SHAPE'},
                        ],
                        'speaker_notes': 'Notes for this slide',
                        'images': [
                            {
                                'url': 'https://...',
                                'title': 'image title',
                                'description': 'alt text'
                            },
                            ...
                        ]
                    },
                    ...
                ]
            }
        """
        try:
            logger.info(f"Fetching presentation data for {presentation_id}")
            
            # Fetch complete presentation with all fields
            presentation = self.service.presentations().get(
                presentationId=presentation_id
            ).execute()
            
            title = presentation.get('title', 'Untitled Presentation')
            slides_data = presentation.get('slides', [])
            
            logger.info(f"Found presentation '{title}' with {len(slides_data)} slides")
            
            # Process each slide
            processed_slides = []
            for idx, slide in enumerate(slides_data):
                slide_info = self._process_slide(slide, idx)
                processed_slides.append(slide_info)
                logger.debug(f"Processed slide {idx + 1}: {len(slide_info['text_content'])} chars text, "
                           f"{len(slide_info['images'])} images")
            
            result = {
                'presentation_id': presentation_id,
                'title': title,
                'slides': processed_slides
            }
            
            logger.info(f"Successfully fetched presentation data: {len(processed_slides)} slides")
            return result
            
        except Exception as e:
            raise ValueError(f"Failed to fetch presentation data for {presentation_id}: {str(e)}") from e
    
    def _process_slide(self, slide: Dict[str, Any], slide_index: int) -> Dict[str, Any]:
        """
        Process a single slide to extract text, images, and speaker notes.
        
        Args:
            slide: Slide data from Slides API
            slide_index: Zero-based index of the slide
            
        Returns:
            Dictionary with processed slide data
        """
        object_id = slide.get('objectId', '')
        
        # Extract text from all page elements
        text_elements = []
        images = []
        
        page_elements = slide.get('pageElements', [])
        for element in page_elements:
            # Extract text from shapes
            if 'shape' in element:
                shape = element['shape']
                text = self._extract_text_from_shape(shape)
                if text:
                    text_elements.append({
                        'text': text,
                        'type': 'SHAPE'
                    })
            
            # Extract text from tables
            elif 'table' in element:
                table = element['table']
                text = self._extract_text_from_table(table)
                if text:
                    text_elements.append({
                        'text': text,
                        'type': 'TABLE'
                    })
            
            # Extract images
            elif 'image' in element:
                image_data = self._extract_image_info(element['image'])
                if image_data:
                    images.append(image_data)
        
        # Combine all text content
        text_content = '\n\n'.join([elem['text'] for elem in text_elements])
        
        # Extract speaker notes
        speaker_notes = ''
        slide_properties = slide.get('slideProperties', {})
        notes_page = slide_properties.get('notesPage', {})
        if notes_page:
            speaker_notes = self._extract_speaker_notes(notes_page)
        
        return {
            'slide_index': slide_index,
            'object_id': object_id,
            'text_content': text_content,
            'text_elements': text_elements,
            'speaker_notes': speaker_notes,
            'images': images
        }
    
    def _extract_text_from_shape(self, shape: Dict[str, Any]) -> str:
        """
        Extract text content from a shape element.
        
        Args:
            shape: Shape data from Slides API
            
        Returns:
            Combined text content from the shape
        """
        text_parts = []
        text_content = shape.get('text', {})
        text_elements = text_content.get('textElements', [])
        
        for element in text_elements:
            text_run = element.get('textRun', {})
            content = text_run.get('content', '')
            if content and content.strip():
                text_parts.append(content.strip())
        
        return ' '.join(text_parts)
    
    def _extract_text_from_table(self, table: Dict[str, Any]) -> str:
        """
        Extract text content from a table element.
        
        Args:
            table: Table data from Slides API
            
        Returns:
            Combined text content from all table cells
        """
        text_parts = []
        table_rows = table.get('tableRows', [])
        
        for row in table_rows:
            table_cells = row.get('tableCells', [])
            for cell in table_cells:
                text_content = cell.get('text', {})
                text_elements = text_content.get('textElements', [])
                
                for element in text_elements:
                    text_run = element.get('textRun', {})
                    content = text_run.get('content', '')
                    if content and content.strip():
                        text_parts.append(content.strip())
        
        return ' '.join(text_parts)
    
    def _extract_image_info(self, image: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract image URL and metadata.
        
        Args:
            image: Image data from Slides API
            
        Returns:
            Dictionary with image information or None if no URL available
        """
        content_url = image.get('contentUrl')
        if not content_url:
            return None
        
        # Extract title and description if available
        image_properties = image.get('imageProperties', {})
        
        return {
            'url': content_url,
            'title': image.get('title', ''),
            'description': image.get('description', '')
        }
    
    def _extract_speaker_notes(self, notes_page: Dict[str, Any]) -> str:
        """
        Extract speaker notes from a slide's notes page.
        
        Speaker notes are in the first BODY placeholder shape on the notes page.
        
        Args:
            notes_page: Notes page data from Slides API
            
        Returns:
            Combined speaker notes text
        """
        text_parts = []
        page_elements = notes_page.get('pageElements', [])
        
        for element in page_elements:
            if 'shape' in element:
                shape = element['shape']
                # Look for the BODY placeholder which contains speaker notes
                placeholder = shape.get('placeholder', {})
                placeholder_type = placeholder.get('type', '')
                
                if placeholder_type == 'BODY':
                    notes_text = self._extract_text_from_shape(shape)
                    if notes_text:
                        text_parts.append(notes_text)
        
        return '\n\n'.join(text_parts)

