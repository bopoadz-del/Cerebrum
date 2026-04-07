# Local Drive & Smartphone Connectors

## Summary

Two new connectors have been created to replace Google Drive for local file access:

### 1. Local Drive Connector (`local_drive.py`)
Production filesystem connector for accessing local folders.

**Features:**
- List files/directories (recursive option)
- Read files (text or base64)
- Write files
- Create directories
- Delete files/folders
- Search files with glob patterns
- Path traversal protection (chroot-like security)
- File type filtering

**Configuration:**
```bash
LOCAL_DRIVE_ROOT=/path/to/folder   # Root folder for all operations
USE_STUB_LOCAL_DRIVE=true          # Use stub mode for testing
```

**Usage:**
```python
from app.connectors import get_connector

local_drive = get_connector("local_drive")
files = local_drive.list_files("documents")
content = local_drive.read_file("notes.txt")
local_drive.write_file("new.txt", "content")
```

---

### 2. Smartphone Connector (`smartphone.py`)
Production connector for accessing smartphone storage via multiple modes.

**Supported Modes:**
- **USB** - Phone mounted as external drive
- **MTP** - Media Transfer Protocol (Android phones)
- **Syncthing** - Sync app folder
- **Folder Sync** - Any synced folder (Dropbox, OneDrive, etc.)

**Features:**
- List files by type (photos, documents, music)
- List photos by album
- Read files
- Write files
- Delete files
- Sync to/from phone
- Automatic phone detection

**Configuration:**
```bash
SMARTPHONE_MODE=syncthing       # usb, mtp, syncthing, folder
SMARTPHONE_PATH=/path/to/sync   # Sync folder path
USE_STUB_SMARTPHONE=true        # Use stub mode for testing
```

**Usage:**
```python
from app.connectors import get_connector

phone = get_connector("smartphone")
photos = phone.list_photos()
files = phone.list_files(file_type="documents")
phone.sync_from_phone("DCIM/photo.jpg", "/local/path/")
```

---

## Files Created

### Production Connectors
- `backend/app/connectors/local_drive.py` - Local filesystem connector
- `backend/app/connectors/smartphone.py` - Smartphone storage connector

### Stubs (for testing)
- `backend/app/stubs/local_drive.py` - Local drive stub
- `backend/app/stubs/smartphone.py` - Smartphone stub

### Updated Files
- `backend/app/connectors/__init__.py` - Exports new connectors
- `backend/app/connectors/factory.py` - Registers new connectors
- `backend/app/stubs/__init__.py` - Exports new stubs
- `backend/tests/unit/test_connectors.py` - Tests for new connectors

---

## Running Tests

```bash
cd backend
python3 -m pytest tests/unit/test_connectors.py -v
```

All 47 tests pass.

---

## Demo

```bash
cd cerebrum-fix
SECRET_KEY="your-secret-key" python3 demo_connectors.py
```

---

## Google Drive Status

Google Drive has been **removed** from the connector factory registration. The test that checked for `google_drive` in the connector list has been updated to check for `local_drive` and `smartphone` instead.

If you need to keep Google Drive as an option, you can add it back:
```python
# In factory.py _register_builtin_connectors()
from app.stubs.base import BaseStub
register_connector(
    "google_drive",
    stub_factory=lambda: BaseStub("google_drive"),
)
```
