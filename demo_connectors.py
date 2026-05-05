run #!/usr/bin/env python3
"""
Local Drive and Smartphone Connector Demo

This script demonstrates the new connectors.
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.connectors import get_connector, list_connectors

print("=" * 60)
print("LOCAL DRIVE & SMARTPHONE CONNECTOR DEMO")
print("=" * 60)

# List all available connectors
print("\n📦 Available Connectors:")
for name in list_connectors():
    print(f"   • {name}")

# Test Local Drive Connector (using stub mode)
print("\n" + "=" * 60)
print("💾 LOCAL DRIVE CONNECTOR")
print("=" * 60)

os.environ["USE_STUB_LOCAL_DRIVE"] = "true"
local_drive = get_connector("local_drive")

print(f"\nConnector Type: {type(local_drive).__name__}")
print(f"Health: {local_drive.health_check()['status']}")
print(f"Info: {local_drive.get_info()['capabilities']}")

# List files
result = local_drive.list_files()
print(f"\n📁 Root Directory:")
for f in result.data["files"]:
    icon = "📂" if f["is_dir"] else "📄"
    print(f"   {icon} {f['name']}")

# List documents
result = local_drive.list_files("documents")
print(f"\n📄 Documents Folder:")
for f in result.data["files"]:
    print(f"   📄 {f['name']} ({f['size_human']})")

# Read a file
result = local_drive.read_file("documents/meeting_notes.txt")
if result.success:
    print(f"\n📖 Content of meeting_notes.txt:")
    print("   " + "-" * 40)
    for line in result.data["content"].split("\n")[:5]:
        print(f"   {line}")
    print("   " + "-" * 40)

# Test Smartphone Connector (using stub mode)
print("\n" + "=" * 60)
print("📱 SMARTPHONE CONNECTOR")
print("=" * 60)

os.environ["USE_STUB_SMARTPHONE"] = "true"
smartphone = get_connector("smartphone")

print(f"\nConnector Type: {type(smartphone).__name__}")
print(f"Health: {smartphone.health_check()['status']}")

info = smartphone.get_info()
print(f"Phone: {info['phone']['name']} ({info['phone']['model']})")
print(f"Connection: {info['phone']['connection_type']}")
print(f"Capabilities: {info['capabilities']}")

# List photos
result = smartphone.list_photos()
print(f"\n📸 Photos ({result.data['count']} total):")
for p in result.data["photos"][:3]:
    print(f"   📸 {p['name']} (Album: {p['album']})")

# List files by type
result = smartphone.list_files(file_type="documents")
print(f"\n📄 Documents ({result.data['count']}):")
for f in result.data["files"]:
    print(f"   📄 {f['name']}")

print("\n" + "=" * 60)
print("✅ Demo Complete!")
print("=" * 60)

print("""
Configuration Options:

Local Drive:
  - LOCAL_DRIVE_ROOT=/path/to/folder  # Set root folder
  - USE_STUB_LOCAL_DRIVE=true         # Use stub mode

Smartphone:
  - SMARTPHONE_MODE=usb|mtp|syncthing|folder  # Connection mode
  - SMARTPHONE_PATH=/path/to/sync             # Sync folder path
  - USE_STUB_SMARTPHONE=true                  # Use stub mode
""")
