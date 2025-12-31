# Cross-Platform Build Guide

This guide explains how to build Port Monitor executables for different platforms using Docker.

## Prerequisites

- Docker installed and running
- Sufficient disk space (~2GB for Windows build)

## Quick Start

### Build for All Platforms

```bash
./build.sh
```

### Build for Specific Platform

```bash
./build.sh windows    # Windows .exe only
./build.sh linux      # Linux binary only
```

### Clean Build Artifacts

```bash
./build.sh clean
```

## Build Details

### Linux Build

- **Output**: `dist-linux/Port Monitor/`
- **Time**: ~2-3 minutes
- **Size**: ~100MB
- Creates a folder with executable and dependencies

### Windows Build (.exe)

- **Output**: `dist-windows/PortMonitor.exe`
- **Time**: ~10-15 minutes (first build)
- **Size**: ~50MB single file
- Uses Wine for cross-compilation
- **Note**: Slower startup due to single-file extraction

## Native Windows Build (Recommended for Production)

For best performance, build on Windows directly:

### On Windows Machine:

1. **Install Python 3.10+**

   - Download from [python.org](https://www.python.org/downloads/)
   - Check "Add Python to PATH" during installation

2. **Install Dependencies**

   ```cmd
   pip install -r requirements.txt
   pip install pyinstaller
   ```

3. **Build Executable**

   ```cmd
   REM Folder build (recommended)
   pyinstaller --windowed --icon=icon.ico --name "Port Monitor" main.py

   REM Single file build
   pyinstaller --windowed --onefile --icon=icon.ico --name "Port Monitor" main.py
   ```

4. **Output**
   - Folder build: `dist/Port Monitor/`
   - Single file: `dist/Port Monitor.exe`

## Native macOS Build

For macOS executable (.app):

```bash
# Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# Build
pyinstaller --windowed --icon=icon.icns --name "Port Monitor" main.py

# Output: dist/Port Monitor.app/
```

## Icon Files

Different platforms require different icon formats:

- **macOS**: `icon.icns` (already provided)
- **Windows**: `icon.ico` (needs to be created)
- **Linux**: `icon.png` (already provided)

## Docker Build Architecture

The Dockerfile uses multi-stage builds:

```
┌─────────────┐
│    base     │  ← Ubuntu 22.04 + Python + Dependencies
└─────┬───────┘
      │
      ├──────────────┬──────────────┐
      │              │              │
┌─────▼────────┐ ┌──▼────────┐ ┌──▼────┐
│ linux-build  │ │windows-build│ │  dev  │
│              │ │   (Wine)    │ │       │
└──────────────┘ └─────────────┘ └───────┘
```

## Troubleshooting

### Docker Build Fails

**Issue**: Out of disk space

```bash
# Clean Docker
docker system prune -a
```

**Issue**: Wine installation timeout

```bash
# Increase Docker memory to 4GB in Docker Desktop settings
```

### Windows .exe Won't Run

**Issue**: Antivirus blocks execution

- Add exception in Windows Defender/Antivirus
- This is common with PyInstaller executables

**Issue**: "Failed to execute script"

- Rebuild with `--debug` flag to see error details
- Check that all dependencies are included

### Performance Issues

**Windows single-file .exe is slow to start**

- This is normal (extracts files at runtime)
- Use folder build for faster startup:
  ```bash
  pyinstaller --windowed --icon=icon.ico --name "Port Monitor" main.py
  ```

## Build Comparison

| Method             | Speed     | Size   | Startup | Recommended         |
| ------------------ | --------- | ------ | ------- | ------------------- |
| Native folder      | Fast      | Large  | Fast    | ✅ Yes              |
| Native single-file | Fast      | Medium | Slow    | ⚠️ Ok               |
| Docker Wine        | Very Slow | Medium | Slow    | ❌ Development only |

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build Executables

on: [push, pull_request]

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.10"
      - run: pip install -r requirements.txt pyinstaller
      - run: pyinstaller --windowed --icon=icon.ico --name "Port Monitor" main.py
      - uses: actions/upload-artifact@v3
        with:
          name: windows-build
          path: dist/

  build-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.10"
      - run: pip install -r requirements.txt pyinstaller
      - run: pyinstaller --windowed --icon=icon.icns --name "Port Monitor" main.py
      - uses: actions/upload-artifact@v3
        with:
          name: macos-build
          path: dist/
```

## Distribution

### Creating Installer (Windows)

Use [Inno Setup](https://jrsoftware.org/isinfo.php):

```iss
[Setup]
AppName=Port Monitor
AppVersion=2.0.0
DefaultDirName={autopf}\Port Monitor
OutputBaseFilename=PortMonitor-Setup

[Files]
Source: "dist\Port Monitor\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{group}\Port Monitor"; Filename: "{app}\Port Monitor.exe"
```

### Creating DMG (macOS)

```bash
# Create DMG
hdiutil create -volname "Port Monitor" -srcfolder "dist/Port Monitor.app" -ov -format UDZO PortMonitor.dmg
```

## Best Practices

1. ✅ **Use native builds** for production releases
2. ✅ **Test on target OS** before distribution
3. ✅ **Sign executables** to avoid security warnings
4. ✅ **Use folder build** for better performance
5. ⚠️ **Use Docker** only for quick cross-platform testing

## Support

For issues or questions:

- Check [README.md](README.md) for general usage
- Review [ARCHITECTURE.md](ARCHITECTURE.md) for code structure
- Open an issue on GitHub
