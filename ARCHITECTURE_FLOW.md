# Dependency Flow Diagram

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         main.py                              │
│                    (Application Entry)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ creates
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   app.ui.MainWindow                          │
│                    (UI Coordinator)                          │
└───────┬─────────────┬─────────────┬────────────┬───────────┘
        │             │             │            │
        │ uses        │ uses        │ uses       │ uses
        ▼             ▼             ▼            ▼
┌──────────────┐ ┌──────────────┐ ┌────────┐ ┌──────────────┐
│CRCService    │ │SerialService │ │ Log    │ │Custom Widgets│
│              │ │              │ │Formatter│ │              │
│- calculate() │ │- open_port() │ │- color()│ │- DropButton  │
│- format()    │ │- read_line() │ │- format()│ │- ClickLabel  │
└──────────────┘ └──────────────┘ └────────┘ └──────────────┘
        │                  │
        │ uses            │ uses
        ▼                  ▼
┌──────────────────────────────────┐
│         app.config               │
│    (Constants & Settings)        │
│                                  │
│- BAUD_RATES                      │
│- VERSION                         │
│- TIMEOUT                         │
└──────────────────────────────────┘
```

## Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Presentation Layer                     │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ MainWindow   │  │ DropButton   │  │ClickableLabel│ │
│  │              │  │              │  │              │ │
│  │ (Coordinates)│  │  (Widget)    │  │  (Widget)    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
                           │
                           │ depends on
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    Business Logic Layer                  │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ CRCService   │  │SerialService │  │LogFormatter  │ │
│  │              │  │              │  │              │ │
│  │ (Pure Logic) │  │ (Pure Logic) │  │(Pure Logic)  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
                           │
                           │ uses
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   Configuration Layer                    │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │              app.config                            │ │
│  │  - Constants                                       │ │
│  │  - Settings                                        │ │
│  │  - Defaults                                        │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Dependency Rules

### ✅ Allowed Dependencies

```
UI → Services ✓
UI → Widgets ✓
UI → Config ✓
Services → Config ✓
Utilities → Config ✓
Widgets → (No dependencies) ✓
```

### ❌ Forbidden Dependencies

```
Services → UI ✗
Config → Anything ✗
Services → Widgets ✗
Utilities → Services ✗
```

## Data Flow Example: Loading Serial Port

```
1. MainWindow (UI)
   │
   │ calls
   ▼
2. SerialPortService.get_available_usb_ports()
   │
   │ returns ['/dev/tty.usb1', '/dev/tty.usb2']
   ▼
3. MainWindow displays in QListWidget
   │
   │ user selects port
   ▼
4. SerialPortService.open_port('/dev/tty.usb1')
   │
   │ returns success/failure
   ▼
5. LogFormatter.create_success_message()
   │
   │ returns HTML formatted message
   ▼
6. MainWindow displays in QTextEdit
```

## Data Flow Example: CRC Calculation

```
1. User drops file on DropButton (Widget)
   │
   │ triggers callback
   ▼
2. MainWindow._calculate_crc(filename)
   │
   │ calls
   ▼
3. CRCService.calculate_crc32(filename)
   │
   │ returns (crc, size, name)
   ▼
4. CRCService.format_crc32_hex(crc)
   │
   │ returns "0x12345678"
   ▼
5. ClickableLabel.set_crc_data(hex, name, size)
   │
   │ displays formatted result
   ▼
6. User clicks label → copies to clipboard
```

## Module Independence

### Testable in Isolation

```python
# Each service can be tested independently

# Test CRC Service
crc_service = CRCService()
result = crc_service.calculate_crc32('file.bin')

# Test Serial Service
serial_service = SerialPortService(115200)
ports = serial_service.get_available_usb_ports()

# Test Log Formatter
formatter = LogFormatter()
colored = formatter.colorize_line('[0;32mI Log message')
```

### Reusable Components

```python
# Services can be used in other applications
from app.services import CRCService

# CLI tool
crc = CRCService()
result = crc.calculate_crc32('firmware.bin')
print(result)

# Web API
@app.route('/crc')
def calculate():
    return CRCService().calculate_crc32(request.file)
```

## Benefits Summary

| Aspect                | Benefit                                 |
| --------------------- | --------------------------------------- |
| **Maintainability**   | Clear separation makes changes easy     |
| **Testability**       | Each module can be tested independently |
| **Reusability**       | Services can be used in other projects  |
| **Scalability**       | Easy to add new features                |
| **Understandability** | Clear flow and responsibilities         |
| **Debugging**         | Issues are isolated to specific modules |
| **Team Work**         | Multiple devs can work in parallel      |

## Code Metrics Comparison

### Before (Monolithic)

```
main.py
├── Lines: 750
├── Classes: 3
├── Functions: 15+
├── Dependencies: All in one file
└── Testability: Difficult
```

### After (Modular)

```
Total: 11 files
├── avg lines/file: ~100
├── Services: 2
├── Utilities: 1
├── Widgets: 2
├── UI: 1
├── Config: 1
└── Testability: Easy
```

## Extensibility Examples

### Adding a New Feature: Bluetooth Support

```
1. Create app/services/bluetooth_service.py
2. Import in MainWindow
3. Add UI components for Bluetooth
4. No changes needed to existing services
```

### Adding a New Log Format

```
1. Add method to LogFormatter
2. Use in MainWindow
3. No changes to services or widgets
```

### Adding Configuration File Support

```
1. Extend app/config.py
2. Add load/save methods
3. Services automatically use new config
```

This architecture makes all of these extensions simple and safe!
