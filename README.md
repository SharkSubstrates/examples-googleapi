# GDriveKit

A Python toolkit for Google Drive API automation. Built for agents and automation platforms that need reliable, programmatic access to Google Drive, Docs, Sheets, and Slides.

## Why This Exists

Most Google Drive libraries are built for humans. This one's built for machines. Clean API, minimal dependencies, designed for automated workflows and AI agents that need to interact with Google Drive content.

## Features

### Core Capabilities
- **Authentication**: OAuth2 with secure credential storage via system keyring
- **Drive Operations**: List, search, download, and manage files/folders
- **Export Engine**: Convert Google Docs, Sheets, and Slides to markdown, CSV, HTML, or other formats
- **Metadata Management**: Work with custom properties, labels, and permissions
- **Comments API**: Read and post comments on documents
- **Batch Operations**: Parallel export with intelligent caching
- **Search**: Content and filename search with folder scoping

### Document Export Features
- **Google Docs → Markdown**: Full document structure with images, tables, and formatting
- **Google Slides → Markdown**: Slide content with image extraction
- **Google Sheets → CSV/Excel**: Sheet export with formatting preservation
- **Asset Management**: Automatic image and media extraction
- **Smart Caching**: Skip re-exporting unchanged files

## Installation

```bash
# Using uv (recommended)
uv pip install git+https://github.com/yourusername/gdrivekit.git

# Or pip
pip install git+https://github.com/yourusername/gdrivekit.git
```

## Quick Start

### 1. Configure OAuth Credentials

Create a `gdfs.env` file:

```env
GOOGLE_OAUTH_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your_client_secret
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8080
GOOGLE_OAUTH_SCOPES=https://www.googleapis.com/auth/drive
```

### 2. Basic Usage

```python
from gdrivekit.auth.client import DriveAuthClient
from gdrivekit.clients.drive import DriveClient

# Authenticate
auth = DriveAuthClient()
drive_service = auth.get_authenticated_service()

# List files
client = DriveClient(drive_service)
files = client.list_items()

for file in files:
    print(f"{file.name} ({file.type})")
```

### 3. Export Documents

```python
from gdrivekit.export.docs.exporters import DocsExporter

exporter = DocsExporter(drive_service)
result = exporter.export_doc(
    file_id="your_doc_id",
    output_dir="./output"
)

print(f"Exported to: {result.output_path}")
# Content is in markdown: output/doc_id/content.md
# Images in: output/doc_id/assets/
# Comments in: output/doc_id/comments.json
```

## Use Cases

### For AI Agents
- Extract knowledge from Google Docs for RAG systems
- Convert company documentation to LLM-friendly formats
- Automated content processing pipelines

### For Automation
- Batch export documentation for versioning
- Sync Drive content to other platforms
- Automated backup and archival
- Content migration workflows

### For Data Processing
- Extract structured data from Sheets
- Process presentation content at scale
- Metadata analysis and tagging

## Examples

Check the `examples/` directory for detailed usage:

- `01_user_and_drives.py` - Authentication and drive listing
- `02_properties_and_labels.py` - Custom metadata management
- `03_comments.py` - Comment interaction
- `04_download.py` - File downloads
- `05_export_single.py` - Export single documents
- `06_batch_export.py` - Parallel batch export with caching
- `07_search.py` - Search functionality

## Architecture

```
gdrivekit/
├── auth/          # OAuth2 authentication and credential storage
├── clients/       # API clients (Drive, Sheets, Slides, Labels)
├── export/        # Export engine with format converters
│   ├── docs/      # Google Docs exporters
│   ├── sheets/    # Google Sheets exporters
│   └── slides/    # Google Slides exporters
└── item.py        # Core data models
```

## Requirements

- Python ≥ 3.12
- Google Cloud project with Drive API enabled
- OAuth2 credentials

## Dependencies

- google-api-python-client
- google-auth
- beautifulsoup4 (for HTML parsing)
- keyring (secure credential storage)
- python-dotenv

## License

MIT

## Contributing

This is a tool for getting shit done. PRs welcome if they add value.

