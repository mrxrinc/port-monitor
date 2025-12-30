# Port Monitor - Refactored Structure

## Project Structure

The application has been refactored following SOLID principles and clean code practices:

```
port-monitor/
├── main.py                      # Application entry point
├── requirements.txt             # Python dependencies
├── app/                         # Main application package
│   ├── __init__.py
│   ├── config.py               # Configuration constants
│   ├── services/               # Business logic services
│   │   ├── __init__.py
│   │   ├── crc_service.py     # CRC32 calculation service
│   │   └── serial_service.py  # Serial port management service
│   ├── ui/                     # User interface components
│   │   ├── __init__.py
│   │   └── main_window.py     # Main application window
│   ├── utils/                  # Utility functions
│   │   ├── __init__.py
│   │   └── log_formatter.py   # Log message formatting
│   └── widgets/                # Custom PyQt5 widgets
│       ├── __init__.py
│       └── custom_widgets.py  # DropButton and ClickableLabel
├── build/                      # Build artifacts
└── screenshot/                 # Screenshots
```

## Architecture

### SOLID Principles Applied

1. **Single Responsibility Principle (SRP)**

   - Each class has one clear purpose
   - `CRCService`: Only handles CRC calculations
   - `SerialPortService`: Only manages serial port connections
   - `LogFormatter`: Only formats log messages
   - `MainWindow`: Only handles UI coordination

2. **Open/Closed Principle (OCP)**

   - Services can be extended without modifying existing code
   - New log formatters can be added easily
   - UI components are decoupled from business logic

3. **Liskov Substitution Principle (LSP)**

   - Custom widgets extend PyQt5 widgets properly
   - Service classes can be easily mocked for testing

4. **Interface Segregation Principle (ISP)**

   - Services expose only necessary methods
   - No fat interfaces with unnecessary methods

5. **Dependency Inversion Principle (DIP)**
   - High-level UI depends on abstractions (services)
   - Business logic is independent of UI framework

### Clean Code Practices

- **Meaningful Names**: Clear, descriptive variable and function names
- **Small Functions**: Each function does one thing well
- **Comments**: Docstrings for all classes and methods
- **Error Handling**: Proper exception handling with user feedback
- **DRY**: No code duplication across modules
- **Separation of Concerns**: Logic, UI, and utilities are separated

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Running the Application

```bash
python main.py
```

## Module Descriptions

### `app/config.py`

Contains all application configuration constants:

- Serial port settings (baud rates, timeout)
- Application metadata (version, author)
- UI configuration (window size, font settings)

### `app/services/crc_service.py`

CRC32 calculation service with methods:

- `calculate_crc32()`: Calculate CRC for a file
- `format_crc32_hex()`: Format CRC as hex string
- `format_file_size()`: Format file size in KB

### `app/services/serial_service.py`

Serial port management service with methods:

- `get_available_usb_ports()`: List USB serial ports
- `open_port()`: Open serial connection
- `close_port()`: Close serial connection
- `read_line()`: Read from serial port
- `reboot_esp32()`: Reboot ESP32 device

### `app/utils/log_formatter.py`

Log message formatting utility:

- `colorize_line()`: Apply HTML colors to ESP-IDF logs
- `create_success_message()`: Format success messages
- `create_error_message()`: Format error messages
- `create_warning_message()`: Format warning messages

### `app/widgets/custom_widgets.py`

Custom PyQt5 widgets:

- `DropButton`: Button with drag-and-drop file support
- `ClickableLabel`: Label that copies CRC values to clipboard

### `app/ui/main_window.py`

Main application window that:

- Coordinates all UI components
- Uses services for business logic
- Manages application state
- Handles user interactions

## Benefits of This Structure

1. **Maintainability**: Easy to find and modify specific functionality
2. **Testability**: Services can be unit tested independently
3. **Reusability**: Services can be used in other applications
4. **Scalability**: Easy to add new features without breaking existing code
5. **Readability**: Clear organization makes code easy to understand
6. **Team Collaboration**: Multiple developers can work on different modules

## Development Guidelines

- Keep services independent of UI
- Add new features as services in `app/services/`
- UI components should only handle presentation
- Configuration belongs in `config.py`
- Utilities in `app/utils/` should be pure functions
- Follow existing naming conventions and documentation style
