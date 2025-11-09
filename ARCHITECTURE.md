# GDriveKit Ecosystem Architecture

## Overview

GDriveKit has evolved from a monolithic package into a composable ecosystem of standalone Google API clients. This document explains the architecture, design decisions, and how everything fits together.

## The Decoupled Ecosystem

```
┌─────────────────────────────────────────────────────────────┐
│                    Authentication Layer                      │
├─────────────────────────────────────────────────────────────┤
│  googleapi-oauth        │  secretstore                       │
│  - OAuth2 flow          │  - Keyring storage                 │
│  - Token management     │  - Environment variables           │
│                         │  - Ephemeral (in-memory)           │
│                         │  - 1Password                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Client Layer                        │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ googleapi-   │ googleapi-   │ googleapi-   │ googleapi-     │
│ drive        │ docs         │ sheets       │ slides         │
│              │              │              │                │
│ - List files │ - Fetch      │ - Fetch      │ - Fetch        │
│ - Search     │   structured │   spreadsheet│   presentation │
│ - Download   │   content    │   data       │   data         │
│ - Properties │ - Export to  │ - Export to  │ - Export to    │
│ - Comments   │   markdown   │   markdown   │   markdown     │
│ - Labels     │              │   tables     │                │
│              │ Converters:  │              │ Converters:    │
│              │ - Markdown   │ Converters:  │ - Markdown     │
│              │              │ - Markdown   │                │
│              │              │ - HTML       │                │
└──────────────┴──────────────┴──────────────┴────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   User Applications                          │
├─────────────────────────────────────────────────────────────┤
│  - Compose workflows from individual clients                 │
│  - Use only what you need                                    │
│  - Examples in gdrive-tools repo                             │
└─────────────────────────────────────────────────────────────┘
```

## Design Principles

### 1. Loose Coupling

**Philosophy**: Each API client should work independently.

**Example**: Export a doc without Drive API
```python
# Know the doc ID? Don't need Drive!
from googleapi_docs import DocsClient

docs = DocsClient(auth)
markdown, assets = docs.export('doc_id_here')
```

**Rationale**: 
- Least privilege - request only necessary scopes
- Smaller dependency trees
- Easier testing and maintenance

### 2. Converters Stay With APIs

**Philosophy**: Converters are tightly coupled to API outputs, so they live in the same package.

**Structure**:
```
googleapi-docs/
├── client.py           # DocsClient
├── models.py           # ExportedAsset
└── converters/
    └── markdown.py     # Docs-specific markdown conversion
```

**Rationale**:
- Converters depend on exact API response structure
- Changes to API likely require converter updates
- Keeping them together reduces friction

### 3. No Orchestration Framework

**Philosophy**: Users compose their own workflows.

**Before (orchestrator)**:
```python
result = orchestrator.export_file(doc_id, output_dir)
```

**After (composition)**:
```python
item = drive.get_item(doc_id)
comments = drive.get_comments(doc_id)
markdown, assets = docs.export(doc_id, comments=comments)
# User saves however they want
```

**Rationale**:
- More flexible
- Easier to understand (no magic)
- Users can implement their own caching, error handling, etc.

### 4. Examples Over Frameworks

**Philosophy**: Show patterns, don't enforce them.

**Implementation**:
- `gdrive-tools` repo = examples only (not installable)
- Demonstrates common patterns (batch export, caching, etc.)
- Users copy/adapt to their needs

**Rationale**:
- Examples are easier to understand than frameworks
- No "one size fits all" - users have different needs
- Lower maintenance burden

## Package Details

### Authentication Packages

#### `googleapi-oauth`
**Purpose**: Generic OAuth2 client for Google APIs

**Features**:
- OAuth2 flow (authorization code grant)
- Token refresh
- Storage backend injection

**Dependencies**: `google-auth`, `google-auth-oauthlib`, `secretstore`

#### `secretstore`
**Purpose**: Pluggable secret storage backends

**Backends**:
- `KeyringStorage` - System keychain (macOS Keychain, Windows Credential Manager, etc.)
- `EnvVarStorage` - Environment variables (CI/CD friendly)
- `EphemeralStorage` - In-memory (testing, temporary)
- `OnePasswordStorage` - 1Password CLI integration

**Dependencies**: `keyring` (optional), `subprocess` for 1Password

### API Client Packages

#### `googleapi-drive`
**Purpose**: Drive API v3 operations

**Features**:
- List/search files and folders
- Download binary files
- Manage properties and labels
- Comments (get, reply)
- Drive metadata (My Drive, Shared Drives)

**Models**:
- `DriveItem` - File/folder representation
- `ItemType` - Enum for file types
- `DriveItemPermission` - Permission details

**Dependencies**: `google-api-python-client`, `google-auth`

#### `googleapi-docs`
**Purpose**: Docs API v1 access and markdown export

**Features**:
- Fetch structured document data (tabs, content, images)
- Export to markdown with full styling
- Handle tabbed documents
- Comment annotation in markdown

**Converters**: `converters/markdown.py`

**Dependencies**: `google-api-python-client`, `google-auth`, `requests`

#### `googleapi-sheets`
**Purpose**: Sheets API v4 access and markdown export

**Features**:
- Fetch spreadsheet data (all tabs)
- Export to markdown tables
- Process HTML exports (for charts)

**Converters**: 
- `converters/markdown.py` - Markdown tables
- `converters/html.py` - Asset extraction from HTML

**Dependencies**: `google-api-python-client`, `google-auth`, `beautifulsoup4`

#### `googleapi-slides`
**Purpose**: Slides API v1 access and markdown export

**Features**:
- Fetch presentation data
- Export to markdown with speaker notes
- Download slide images

**Converters**: `converters/markdown.py`

**Dependencies**: `google-api-python-client`, `google-auth`, `requests`

#### `googleapi-labels`
**Purpose**: Labels API v2 for enterprise label management

**Features**:
- List label definitions
- Get specific labels
- Enterprise taxonomy management

**Dependencies**: `google-api-python-client`, `google-auth`

## Workflow Patterns

### Pattern 1: Simple Export (Known ID)

```python
from googleapi_oauth import OAuth2Client
from secretstore import KeyringStorage
from googleapi_docs import DocsClient

auth = OAuth2Client(..., storage=KeyringStorage('app'))
docs = DocsClient(auth)

markdown, assets = docs.export('doc_id')
```

**Use case**: You know the doc ID, don't need metadata/comments

### Pattern 2: Full Workflow (Search + Export)

```python
from googleapi_drive import DriveClient
from googleapi_docs import DocsClient

drive = DriveClient(auth)
docs = DocsClient(auth)

# Search
results = drive.search_by_name("meeting", limit=5)

# Export with comments
for item in results:
    comments = drive.get_comments(item.id)
    markdown, assets = docs.export(item.id, comments=comments)
```

**Use case**: Discover files, need comments

### Pattern 3: Batch with Multiprocessing

```python
from multiprocessing import Pool

def export_doc(doc_id):
    # Each worker creates own client
    docs = DocsClient(auth)
    return docs.export(doc_id)

with Pool(4) as pool:
    results = pool.map(export_doc, doc_ids)
```

**Use case**: Export many files (10+)

## Key Design Decisions

### Why No Batch Exporter Class?

**Decision**: Examples only, no BatchExporter

**Reasoning**:
- Batch operations are just multiprocessing patterns
- Users have different needs (error handling, retry logic, progress tracking)
- Examples show the pattern, users adapt to their needs
- Lower maintenance burden

### Why No Cache Manager Class?

**Decision**: Simple caching examples, no CacheManager

**Reasoning**:
- Caching strategies vary (content hash, modified time, custom)
- Could be extracted as `export-cache` utility later if needed
- For now, examples show simple approach:
  ```python
  if cache['modified_time'] == item.modified_time:
      skip()
  ```

### Why Keep Converters in API Packages?

**Decision**: Converters are submodules, not separate packages

**Reasoning**:
- Tightly coupled to API response structure
- Changes to API response → changes to converter
- Keeping them together reduces friction
- If users want custom converters, they fork the API package

### Why No Factory Class?

**Decision**: Direct instantiation only

**Reasoning**:
- `DriveClient(auth)` is clearer than `ClientFactory.create_drive_only(auth)`
- Less magic, more explicit
- Users compose their own setup

## Migration Path

1. **Update imports** (`gdrivekit.auth` → `googleapi_oauth`)
2. **Remove factory** (instantiate clients directly)
3. **Remove orchestrator** (compose your own workflow)
4. **Remove batch exporter** (use multiprocessing pattern)

See `MIGRATION_GUIDE.md` for complete details.

## Future Possibilities

### Potential Additions

1. **export-cache** - Generic caching utility
   - Content-based hashing
   - Metadata tracking
   - Pluggable storage backends
   - Independent of Google APIs

2. **More converters**
   - Docs → HTML
   - Sheets → Excel
   - Slides → PDF

3. **More storage backends**
   - AWS Secrets Manager
   - Azure Key Vault
   - HashiCorp Vault

### What We Won't Add

- Orchestration framework (examples only)
- Batch processing framework (multiprocessing examples)
- Monolithic "do everything" package (ecosystem approach)

## Philosophy

**"Compose, don't orchestrate"**

Rather than building a framework that tries to handle every use case, we provide:
- Clean, focused clients for each Google API
- Examples showing common patterns
- Users compose their own workflows

This approach:
- ✓ More flexible
- ✓ Easier to understand
- ✓ Lower maintenance
- ✓ Better testability
- ✓ Encourages best practices

## Repository Structure

```
/Users/batteryshark/Projects/
├── googleapi-oauth/       # OAuth2 client
├── secretstore/           # Storage backends
├── googleapi-drive/       # Drive API client
├── googleapi-docs/        # Docs API client + converters
├── googleapi-sheets/      # Sheets API client + converters
├── googleapi-slides/      # Slides API client + converters
└── googleapi-labels/      # Labels API client

/Users/batteryshark/Downloads/gdrive_tools/  # Examples repo
├── examples/              # Usage examples
├── README.md             # Ecosystem overview
├── MIGRATION_GUIDE.md    # Migration from old gdrivekit
└── ARCHITECTURE.md       # This file
```

## Contributing

Each package is independent:
- File issues on the specific package repo
- PRs should be focused on a single package
- Examples go in the `gdrive-tools` repo

## Conclusion

The decoupled architecture provides:
- **Flexibility**: Use only what you need
- **Clarity**: Each package has one job
- **Maintainability**: Changes isolated to relevant packages
- **Extensibility**: Easy to add new converters or storage backends

This is a toolkit, not a framework. Compose your own solutions.

