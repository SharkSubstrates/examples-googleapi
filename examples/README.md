# GDrive Tools - Examples

This directory contains examples demonstrating various features of the GDrive Tools library.

## Setup

Before running any examples, ensure you have:
1. Installed dependencies: `uv pip install -r ../requirements.txt`
2. Configured your OAuth credentials in `../gdfs.env`

## Examples

### 01_user_and_drives.py
Get authenticated user information and list all available drives (including shared drives).

```bash
uv run python 01_user_and_drives.py
```

### 02_properties_and_labels.py
Work with custom file properties and Google Drive labels. Demonstrates getting, setting, and clearing custom properties.

```bash
uv run python 02_properties_and_labels.py
```

### 03_comments.py
Interact with file comments - retrieve comments and post replies.

```bash
uv run python 03_comments.py
```

### 04_download.py
Download binary files from Google Drive and save them to disk.

```bash
uv run python 04_download.py
```

### 05_export_single.py
Export individual Google Docs, Sheets, and Slides to markdown or other formats.

```bash
uv run python 05_export_single.py
```

### 06_batch_export.py
Batch export multiple files in parallel. Includes:
- Export by specific file IDs
- Export entire folders recursively
- Smart caching to avoid re-exporting unchanged files

```bash
uv run python 06_batch_export.py
```

### 07_search.py
Search Google Drive by filename or content, with support for folder-scoped searches.

```bash
uv run python 07_search.py
```

## Notes

- Most examples use test file IDs that you'll need to replace with your own
- The examples automatically add the parent directory to Python's path to import `gdrivekit`
- All examples load OAuth credentials from `../gdfs.env`

