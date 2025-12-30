# Port Monitor

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyQt5](https://img.shields.io/badge/PyQt5-5.15+-green.svg)](https://pypi.org/project/PyQt5/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A professional serial port monitoring application with CRC32 generation capabilities. Built with PyQt5 and following clean code architecture principles.

## Features

- 🔌 **Multi-Port Monitoring** - Monitor multiple USB serial ports simultaneously
- 📊 **Real-Time Logging** - Color-coded logs with smart auto-scrolling
- 🔄 **ESP32 Support** - One-click ESP32 device reboot functionality
- 🔐 **CRC32 Generator** - Drag-and-drop file CRC calculation with clipboard copy
- ⚡ **Dynamic Port Detection** - Automatic USB device discovery and connection
- 💾 **Log Management** - Save logs to file with timestamp
- 🎨 **Intuitive UI** - Clean, modern interface with status indicators

## Screenshots

![Port Monitor Interface](screenshot/main-window.png)

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/mrxrinc/port-monitor.git
   cd port-monitor
   ```

2. **Create and activate virtual environment** (recommended)
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # or
   venv\Scripts\activate     # On Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Running the Application

```bash
python main.py
```

### Basic Operations

1. **Monitor Serial Ports**
   - Connect USB devices to your computer
   - Ports appear automatically in the left panel
   - Click on a port to view its logs

2. **Change Baud Rate**
   - Select desired baud rate from dropdown
   - All ports reconnect automatically

3. **Calculate CRC32**
   - Click "Click or Drop File Here" button, or
   - Drag and drop a file onto the button
   - Click the result to copy CRC to clipboard

4. **Reboot ESP32**
   - Select the port with your ESP32 device
   - Click "Reboot ESP32" button

5. **Save Logs**
   - Select a port
   - Click "Save Logs" to export to text file

## Building Executables

### Recommended Build (Multiple Files)

This creates a distributable folder with better performance and compatibility:

```bash
# Activate virtual environment first
source venv/bin/activate

# Build application
python -m PyInstaller \
  --windowed \
  --icon=icon.icns \
  --name 'Port Monitor' \
  main.py
```

The executable will be in the `dist/Port Monitor/` directory.

### Single File Build (Not Recommended)

Creates a single executable file but with slower startup and larger size:

```bash
pyinstaller --windowed --onefile --icon=icon.icns --name 'Port Monitor' main.py
```

⚠️ **Note:** Single file builds are not recommended because:
- Slower startup time (needs to extract at runtime)
- Larger file size
- Potential antivirus false positives
- Debugging is more difficult

## Project Structure

```
port-monitor/
├── main.py                      # Application entry point
├── requirements.txt             # Python dependencies
├── app/                         # Main application package
│   ├── config.py               # Configuration and constants
│   ├── services/               # Business logic layer
│   │   ├── crc_service.py     # CRC32 calculations
│   │   └── serial_service.py  # Serial port management
│   ├── ui/                     # User interface layer
│   │   └── main_window.py     # Main application window
│   ├── utils/                  # Utility functions
│   │   └── log_formatter.py   # Log formatting and colorization
│   └── widgets/                # Custom PyQt5 widgets
│       └── custom_widgets.py  # DropButton and ClickableLabel
├── icon.icns                   # Application icon (macOS)
├── icon.png                    # Application icon (source)
└── screenshot/                 # Application screenshots
```

## Architecture

This project follows **SOLID principles** and **clean code practices**:

- **Separation of Concerns** - UI, business logic, and utilities are separated
- **Single Responsibility** - Each module has one clear purpose
- **Dependency Inversion** - High-level modules don't depend on low-level details
- **Testability** - Services can be unit tested independently
- **Maintainability** - Clear structure makes changes easy

For detailed architecture documentation, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Configuration

Common configuration values can be modified in `app/config.py`:

```python
# Serial port settings
DEFAULT_BAUD_RATE = 115200
COMMON_BAUD_RATES = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]

# UI settings
PORT_LIST_WIDTH = 220
LOG_FONT_SIZE = 14
```

## Supported Platforms

- ✅ macOS 10.13+
- ✅ Linux (Ubuntu 18.04+, Debian, Fedora)
- ✅ Windows 10/11

## Troubleshooting

### Port Not Detected
- Ensure the USB device is properly connected
- Check that the device drivers are installed
- On Linux, you may need to add your user to the `dialout` group:
  ```bash
  sudo usermod -a -G dialout $USER
  ```
  Then log out and back in.

### Permission Denied
- On macOS/Linux, you may need to grant permissions to access serial ports
- Check that you have read/write access to `/dev/tty.*` devices

### Application Won't Start
- Verify Python version: `python --version` (should be 3.8+)
- Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`
- Check for import errors: `python -c "from app.ui import MainWindow"`

## Development

### Running Tests
```bash
# Run all tests (when implemented)
pytest

# Run with coverage
pytest --cov=app
```

### Code Style
This project follows PEP 8 style guidelines. Format code with:
```bash
black app/
flake8 app/
```

### Contributing
Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Dependencies

- **PyQt5** (5.15+) - GUI framework
- **pyserial** (3.5+) - Serial port communication

See [requirements.txt](requirements.txt) for complete list.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

**Mohammad Mirzaei** ([@mrxrinc](https://github.com/mrxrinc))

## Acknowledgments

- Built with [PyQt5](https://www.riverbankcomputing.com/software/pyqt/)
- Serial communication via [pySerial](https://pythonhosted.org/pyserial/)
- ESP-IDF log format support

## Version History

### v2.0.0 (Current)
- ✨ Complete architecture refactor following SOLID principles
- 🎨 Modular code structure for better maintainability
- 📚 Comprehensive documentation
- 🧪 Improved testability
- 🔧 Configuration centralization

### v1.0.0
- Initial release with basic monitoring features

---

**Note:** For detailed architecture information and development guidelines, refer to:
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture and design patterns
- [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md) - Refactoring details
- [ARCHITECTURE_FLOW.md](ARCHITECTURE_FLOW.md) - Component interaction diagrams
