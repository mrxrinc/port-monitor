"""Application configuration constants."""

# Serial port configuration
TIMEOUT = 50  # milliseconds
DEFAULT_BAUD_RATE = 115200
COMMON_BAUD_RATES = [
    300, 1200, 2400, 4800, 9600, 19200, 38400, 
    57600, 115200, 230400, 460800, 921600
]

# Application metadata
VERSION = "2.0.0"
APP_NAME = "Port Monitor"
AUTHOR = "mrxrinc"
AUTHOR_LINK = "https://github.com/mrxrinc"

# Timer intervals (milliseconds)
PORT_REFRESH_INTERVAL = 1000
LOGGER_INTERVAL = TIMEOUT

# UI configuration
WINDOW_WIDTH_RATIO = 1.3
WINDOW_HEIGHT_RATIO = 1.2
PORT_LIST_WIDTH = 220
LOG_FONT_SIZE = 14
LOG_FONT_FAMILIES = ["Menlo", "Consolas", "Courier New"]

# ESP32 reboot timing
ESP32_REBOOT_DELAY = 100  # milliseconds
