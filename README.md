# GDriveKit Examples

**A cookbook for working with Google Drive APIs in Python.**

This repo demonstrates how to use the decoupled Google API packages for real-world automation tasks. No installable package - just clean, practical examples showing how the pieces fit together.

## The Ecosystem

GDriveKit is now a collection of standalone packages, each focused on a single Google API:

### Core Packages

- **[`googleapi-oauth`](https://github.com/SharkSubstrates/googleapi-oauth)** - OAuth2 authentication for Google APIs
- **[`secretstore`](https://github.com/SharkSubstrates/utils-secretstore)** - Pluggable token storage (keyring, env vars, ephemeral, 1Password)

### API Clients

- **[`googleapi-drive`](https://github.com/SharkSubstrates/googleapi-drive)** - Drive API v3 (list, search, download, metadata, comments)
- **[`googleapi-docs`](https://github.com/SharkSubstrates/googleapi-docs)** - Docs API v1 (structured content, markdown export)
- **[`googleapi-sheets`](https://github.com/SharkSubstrates/googleapi-sheets)** - Sheets API v4 (spreadsheet data, markdown tables)
- **[`googleapi-slides`](https://github.com/SharkSubstrates/googleapi-slides)** - Slides API v1 (presentation data, markdown export)
- **[`googleapi-labels`](https://github.com/SharkSubstrates/googleapi-labels)** - Labels API v2 (enterprise label management)

### Why Decoupled?

**Loose Coupling**: Each API client is independent. Need just Docs? Install just `googleapi-docs`. No Drive dependency unless you need comments or metadata.

**Least Privilege**: Request only the scopes you need. A doc-only workflow doesn't need Drive permissions.

**Composable**: Mix and match packages for your workflow. The examples here show common patterns.

## Installation

Install only what you need:

```bash
# Authentication (required)
pip install googleapi-oauth secretstore

# API clients (pick what you need)
pip install googleapi-drive
pip install googleapi-docs
pip install googleapi-sheets
pip install googleapi-slides
pip install googleapi-labels
```

Or install from local paths during development:

```bash
pip install /path/to/googleapi-oauth
pip install /path/to/googleapi-drive
# etc.
```

## Quick Start

### Basic Authentication

```python
from googleapi_oauth import OAuth2Client
from secretstore import KeyringStorage

# Setup OAuth (one time, credentials cached)
auth = OAuth2Client(
    client_id='your_client_id.apps.googleusercontent.com',
    client_secret='your_client_secret',
    scopes=['https://www.googleapis.com/auth/drive.readonly'],
    storage=KeyringStorage('myapp')
)
```

### List Files in Drive

```python
from googleapi_drive import DriveClient

drive = DriveClient(auth)

# List My Drive
for item in drive.list_items('root'):
    print(f"{item.name} - {item.type.value}")

# Search by name
results = drive.search_by_name("meeting notes", limit=10)
```

### Export a Google Doc to Markdown

```python
from googleapi_docs import DocsClient

docs = DocsClient(auth)

# Export to markdown
markdown, assets = docs.export('document_id_here')

# Save output
with open('output.md', 'w') as f:
    f.write(markdown)

# Save images
for asset in assets:
    with open(f'assets/{asset.name}', 'wb') as f:
        f.write(asset.content)
```

### With Comments

```python
from googleapi_drive import DriveClient
from googleapi_docs import DocsClient

drive = DriveClient(auth)
docs = DocsClient(auth)

doc_id = 'your_doc_id'

# Fetch comments via Drive API
comments = drive.get_comments(doc_id)

# Export with comments annotated
markdown, assets = docs.export(doc_id, comments=comments)
```

## Examples

This repo contains practical examples showing real-world workflows:

### Basic Operations
- **`01_user_and_drives.py`** - Authentication and drive listing
- **`02_properties_and_labels.py`** - Custom metadata management
- **`03_comments.py`** - Comment interaction
- **`04_download.py`** - File downloads
- **`07_search.py`** - Search by name and content
- **`08_envvar_auth.py`** - Environment variable authentication

### Export Workflows
- **`05_export_single.py`** - Export a single document to markdown
- **`06_batch_export.py`** - Simple batch export (DEPRECATED, see 09_batch_export_parallel.py)
- **`09_batch_export_parallel.py`** - Parallel batch export with multiprocessing and caching

### Advanced Patterns
- **Recursive folder export** - Export entire folder hierarchies
- **Parallel processing** - Use multiprocessing for batch operations
- **Caching strategies** - Skip unchanged files, content-based hashing
- **Error handling** - Graceful failures and retries

## Common Patterns

### Pattern 1: Export Single Doc (No Drive Dependency)

```python
from googleapi_oauth import OAuth2Client
from secretstore import KeyringStorage
from googleapi_docs import DocsClient

auth = OAuth2Client(
    client_id='...',
    client_secret='...',
    scopes=['https://www.googleapis.com/auth/documents.readonly'],
    storage=KeyringStorage('myapp')
)

docs = DocsClient(auth)
markdown, assets = docs.export('doc_id')
```

**Note**: No `googleapi-drive` needed if you already know the doc ID!

### Pattern 2: Full Workflow with Drive + Export

```python
from googleapi_oauth import OAuth2Client
from secretstore import KeyringStorage
from googleapi_drive import DriveClient
from googleapi_docs import DocsClient

auth = OAuth2Client(
    client_id='...',
    client_secret='...',
    scopes=[
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/documents.readonly'
    ],
    storage=KeyringStorage('myapp')
)

drive = DriveClient(auth)
docs = DocsClient(auth)

# Search for docs
results = drive.search_by_name("meeting", limit=5)

# Export each
for item in results:
    if item.type == ItemType.DOCS_DOCUMENT:
        markdown, assets = docs.export(item.id)
        # Save to disk...
```

### Pattern 3: Batch Export with Multiprocessing

```python
from multiprocessing import Pool
from googleapi_docs import DocsClient

def export_doc(doc_id):
    docs = DocsClient(auth)  # Each worker gets own client
    return docs.export(doc_id)

doc_ids = ['id1', 'id2', 'id3', ...]

with Pool(4) as pool:
    results = pool.map(export_doc, doc_ids)
```

See `09_batch_export_parallel.py` for a complete implementation.

## Architecture Philosophy

### Before: Monolithic

```
gdrivekit (one big package)
├── Everything tightly coupled
└── Can't use docs without drive
```

### After: Composable Modules

```
Each API = standalone package
├── Use only what you need
├── No unnecessary dependencies
└── Converters stay with their APIs (tight coupling is fine there)
```

**Key Decisions**:
- **Drive, Docs, Sheets, Slides, Labels** → Separate packages (different APIs)
- **Converters** → Submodules within API packages (tightly coupled to API output)
- **Batch operations** → Examples, not a package (just multiprocessing patterns)
- **Orchestration** → Compose yourself, examples show how
- **Caching** → Could be extracted as `export-cache` utility (generic, reusable)

## Development Setup

### Using Local Packages (Recommended)

If you're developing the packages or have them cloned locally:

1. **Edit `pyproject.toml`** - Update paths to your local package directories:

```toml
dependencies = [
    "python-dotenv>=1.2.1",
    "googleapi-oauth @ file:///Users/you/Projects/googleapi-oauth",
    "secretstore @ file:///Users/you/Projects/secretstore",
    "googleapi-drive @ file:///Users/you/Projects/googleapi-drive",
    "googleapi-docs @ file:///Users/you/Projects/googleapi-docs",
    "googleapi-sheets @ file:///Users/you/Projects/googleapi-sheets",
    "googleapi-slides @ file:///Users/you/Projects/googleapi-slides",
    "googleapi-labels @ file:///Users/you/Projects/googleapi-labels",
]
```

2. **Sync dependencies**:

```bash
uv sync
```

3. **Configure `.env`** with your OAuth credentials (see Authentication Setup below)

4. **Run examples**:

```bash
uv run python 05_export_single.py
```

### Manual Installation

Alternatively, install packages individually:

```bash
# Clone packages
git clone https://github.com/you/googleapi-oauth
git clone https://github.com/you/googleapi-drive
# etc.

# Install in editable mode
cd googleapi-oauth && pip install -e .
cd googleapi-drive && pip install -e .
# etc.

# Run examples
cd gdrive-tools
python 01_user_and_drives.py
```

## Authentication Setup

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project or select existing
3. Enable APIs: Drive API, Docs API, Sheets API, Slides API, Labels API
4. Create OAuth 2.0 credentials (Desktop app)

### 2. Configure Environment

Copy the example configuration and fill in your credentials:

```bash
cp example.env .env
# Edit .env with your credentials
```

Your `.env` file should look like:

```env
CLIENT_ID=your_client_id.apps.googleusercontent.com
CLIENT_SECRET=your_client_secret
CLIENT_SCOPES=https://www.googleapis.com/auth/drive.readonly,https://www.googleapis.com/auth/documents.readonly,https://www.googleapis.com/auth/spreadsheets.readonly,https://www.googleapis.com/auth/presentations.readonly
```

Or use `KeyringStorage` for system keychain storage.

## Use Cases

### For AI Agents
- Extract knowledge from Google Docs for RAG systems
- Convert company documentation to LLM-friendly formats
- Automated content processing pipelines

### For Automation
- Batch export documentation for versioning
- Sync Drive content to other platforms
- Automated backup and archival

### For Data Processing
- Extract structured data from Sheets
- Process presentation content at scale
- Metadata analysis and tagging

## Requirements

- Python ≥ 3.10
- Google Cloud project with appropriate APIs enabled
- OAuth2 credentials

## Contributing

This is a cookbook. Got a useful pattern? Submit a PR with a new example.

## License

MIT

## Related Projects

- **[`googleapi-oauth`](https://github.com/SharkSubstrates/googleapi-oauth)** - OAuth2 for Google APIs
- **[`secretstore`](https://github.com/SharkSubstrates/secretstore)** - Secret storage backends
- **[`googleapi-drive`](https://github.com/SharkSubstrates/googleapi-drive)** - Drive API client
- **[`googleapi-docs`](https://github.com/SharkSubstrates/googleapi-docs)** - Docs API client
- **[`googleapi-sheets`](https://github.com/SharkSubstrates/googleapi-sheets)** - Sheets API client
- **[`googleapi-slides`](https://github.com/SharkSubstrates/googleapi-slides)** - Slides API client
- **[`googleapi-labels`](https://github.com/SharkSubstrates/googleapi-labels)** - Labels API client
