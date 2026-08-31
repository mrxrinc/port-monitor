"""Main application window."""

import os
import time
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QTextEdit, QPushButton, QListWidget, QFileDialog, QMessageBox, 
    QAction, QMenuBar, QApplication
)
from PyQt5.QtCore import QTimer, Qt, QSettings
from typing import Dict, List

from app.config import (
    DEFAULT_BAUD_RATE, COMMON_BAUD_RATES, VERSION, APP_NAME, 
    AUTHOR_LINK, PORT_REFRESH_INTERVAL, LOGGER_INTERVAL,
    PORT_LIST_WIDTH, LOG_FONT_SIZE, LOG_FONT_FAMILIES,
    WINDOW_WIDTH_RATIO, WINDOW_HEIGHT_RATIO, ESP32_REBOOT_DELAY
)
from app.services import CRCService, SerialPortService, DefmtDecoderService
from app.services.defmt_service import looks_like_defmt_stream, find_elf_candidates, is_valid_elf
from app.utils import LogFormatter
from app.widgets import DropButton, ClickableLabel

DEFMT_PROBE_MIN_BYTES = 32
DEFMT_PROBE_WINDOW_BYTES = 64
DEFMT_DISCOVERY_COOLDOWN_SECONDS = 5


class MainWindow(QWidget):
    """Main application window for serial port monitoring."""
    
    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        
        # Initialize services
        self.serial_service = SerialPortService(DEFAULT_BAUD_RATE)
        self.crc_service = CRCService()
        self.defmt_service = DefmtDecoderService()
        self.log_formatter = LogFormatter()
        self.settings = QSettings('PortMonitor', 'PortMonitor')
        
        # State management
        self.port_logs: Dict[str, List[str]] = {}
        self.active_port: str = None
        self.auto_scroll: bool = True
        
        # defmt auto-detection state, keyed by port name
        self.port_probe_buffer: Dict[str, bytes] = {}
        self.port_text_buffer: Dict[str, bytes] = {}
        self._elf_discovery_cooldown_until: float = 0.0
        self._defmt_prompt_shown: Dict[str, bool] = {}
        
        # Setup UI
        self._setup_window()
        self._create_menu_bar()
        self._create_ui()
        self._setup_timers()
        
    def _setup_window(self):
        """Configure window properties."""
        self.setWindowTitle(f'mrxrinc | Serial Port Monitor')
        screen = QApplication.desktop().screenGeometry()
        self.resize(
            int(screen.width() // WINDOW_WIDTH_RATIO), 
            int(screen.height() // WINDOW_HEIGHT_RATIO)
        )
    
    def _create_menu_bar(self):
        """Create the menu bar with a Help menu."""
        menubar = QMenuBar(self)
        menubar.setGeometry(0, 0, self.width(), 30)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        # About action
        about_action = QAction('About Port Monitor', self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _create_ui(self):
        """Create the user interface."""
        main_layout = QHBoxLayout(self)
        
        # Left panel
        left_layout = self._create_left_panel()
        main_layout.addLayout(left_layout)
        
        # Right panel
        right_layout = self._create_right_panel()
        main_layout.addLayout(right_layout)
        
        # Initial port population
        self._populate_serial_ports()
    
    def _create_left_panel(self) -> QVBoxLayout:
        """Create the left control panel."""
        layout = QVBoxLayout()
        
        # Port list
        layout.addWidget(QLabel('Serial Ports:'))
        self.port_list = self._create_port_list()
        layout.addWidget(self.port_list)
        
        # Baud rate selector
        layout.addWidget(QLabel('Baud Rate:'))
        self.baud_combo = self._create_baud_combo()
        layout.addWidget(self.baud_combo)
        
        # Control buttons
        layout.addWidget(QLabel(' '))
        layout.addWidget(self._create_button('Clear Logs', self._clear_logs))
        layout.addWidget(self._create_button('Save Logs', self._save_logs))
        layout.addWidget(self._create_button('Reconnect All', self._reconnect_all_ports))
        
        # ESP32 section
        layout.addWidget(QLabel(' '))
        layout.addWidget(QLabel('----------------------------------'))
        layout.addWidget(QLabel('ESP32 Reboot:'))
        layout.addWidget(self._create_button('Reboot ESP32', self._reboot_esp32))
        
        layout.addStretch(1)
        
        # CRC Generator section
        layout.addWidget(QLabel('----------------------------------'))
        layout.addWidget(QLabel('CRC Generator:'))
        
        self.crc_button = DropButton(
            'Click or Drop File Here',
            on_file_dropped=self._calculate_crc,
            parent=self
        )
        self.crc_button.setFixedWidth(PORT_LIST_WIDTH)
        self.crc_button.setFixedHeight(80)
        self.crc_button.setStyleSheet("""
            QPushButton {
                border: 2px dashed rgba(0, 0, 0, 0.3);
                border-radius: 5px;
                background-color: rgba(0, 120, 215, 0.05);
                padding: 10px;
            }
            QPushButton:hover {
                background-color: rgba(0, 120, 215, 0.1);
                border: 2px dashed rgba(0, 120, 215, 0.5);
            }
        """)
        self.crc_button.clicked.connect(self._select_file_for_crc)
        layout.addWidget(self.crc_button)
        
        self.crc_result = ClickableLabel('', self)
        self.crc_result.setFixedWidth(PORT_LIST_WIDTH)
        self.crc_result.setFixedHeight(100)
        self.crc_result.setWordWrap(True)
        self.crc_result.setTextFormat(Qt.RichText)
        self.crc_result.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: gray;
                padding: 15px;
                border: 1px solid rgba(0, 0, 0, 0.2);
                border-radius: 5px;
                background-color: rgba(0, 0, 0, 0.02);
            }
            QLabel:hover {
                background-color: rgba(0, 120, 215, 0.05);
                border: 1px solid rgba(0, 120, 215, 0.3);
            }
        """)
        layout.addWidget(self.crc_result)
        
        return layout
    
    def _create_right_panel(self) -> QVBoxLayout:
        """Create the right log display panel."""
        layout = QVBoxLayout()
        
        self.log_label = QLabel('Logs:')
        layout.addWidget(self.log_label)
        
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        font = self.log_text_edit.font()
        font.setPointSize(LOG_FONT_SIZE)
        font.setFamilies(LOG_FONT_FAMILIES)
        self.log_text_edit.setFont(font)
        
        # Connect scrollbar to detect user scrolling
        scrollbar = self.log_text_edit.verticalScrollBar()
        scrollbar.valueChanged.connect(self._on_scroll_changed)
        
        layout.addWidget(self.log_text_edit)
        
        return layout
    
    def _create_port_list(self) -> QListWidget:
        """Create the port list widget."""
        port_list = QListWidget()
        port_list.setFixedWidth(PORT_LIST_WIDTH)
        port_list.setStyleSheet("""
            QListWidget::item {
                border-bottom: 1px solid rgba(0, 0, 0, 0.1);
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: rgba(0, 120, 215, 0.15);
            }
        """)
        port_list.setWordWrap(True)
        port_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        port_list.currentItemChanged.connect(self._on_port_selected)
        return port_list
    
    def _create_baud_combo(self) -> QComboBox:
        """Create the baud rate combo box."""
        combo = QComboBox()
        combo.setFixedWidth(PORT_LIST_WIDTH)
        for rate in COMMON_BAUD_RATES:
            combo.addItem(str(rate))
        combo.setCurrentText(str(DEFAULT_BAUD_RATE))
        combo.currentTextChanged.connect(self._on_baud_rate_changed)
        return combo
    
    def _create_button(self, text: str, callback) -> QPushButton:
        """Create a standard button."""
        button = QPushButton(text)
        button.setFixedWidth(PORT_LIST_WIDTH)
        button.clicked.connect(callback)
        return button
    
    def _setup_timers(self):
        """Setup application timers."""
        # Port refresh timer
        self.port_refresh_timer = QTimer()
        self.port_refresh_timer.timeout.connect(self._populate_serial_ports)
        self.port_refresh_timer.start(PORT_REFRESH_INTERVAL)
        
        # Logger timer
        self.logger_timer = QTimer()
        self.logger_timer.timeout.connect(self._logger)
        self.logger_timer.start(LOGGER_INTERVAL)
    
    # Event handlers
    
    def _show_about(self):
        """Show about dialog."""
        about_text = f"""
        <h2>{APP_NAME}</h2>
        <p><b>Version:</b> {VERSION}</p>
        <p><b>Author:</b> <a href="{AUTHOR_LINK}">@mrxrinc</a></p>
        <br>
        <p>A serial port monitoring tool with CRC generation capabilities.</p>
        <p>Features:</p>
        <ul>
            <li>Multi-port serial monitoring</li>
            <li>ESP32 reboot support</li>
            <li>CRC32 file generator</li>
            <li>Smart auto-scrolling logs</li>
        </ul>
        """
        QMessageBox.about(self, f"About {APP_NAME}", about_text)
    
    def _on_port_selected(self, current, previous):
        """Handle port selection change."""
        if current:
            port_name = current.text()
            self.active_port = port_name
            
            # Display logs for selected port
            if port_name in self.port_logs:
                self.log_text_edit.setHtml(''.join(self.port_logs[port_name]))
                # Scroll to bottom when switching ports
                scrollbar = self.log_text_edit.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
                self.auto_scroll = True
            else:
                self.log_text_edit.clear()
            
            # Update label
            self.log_label.setText(f'Logs for {port_name}:')
    
    def _on_baud_rate_changed(self, value: str):
        """Handle baud rate change."""
        baud_rate = int(value)
        self.serial_service.set_baud_rate(baud_rate)
        self._reconnect_all_ports()
    
    def _on_scroll_changed(self, value: int):
        """Detect if user scrolled away from bottom."""
        scrollbar = self.log_text_edit.verticalScrollBar()
        # Check if we're at the bottom (within 10 pixels tolerance)
        at_bottom = value >= scrollbar.maximum() - 10
        self.auto_scroll = at_bottom
    
    def _populate_serial_ports(self):
        """Update the list of available serial ports."""
        ports = self.serial_service.get_available_usb_ports()
        current_ports = [self.port_list.item(i).text() for i in range(self.port_list.count())]
        current_selection = self.port_list.currentItem()
        current_selection_text = current_selection.text() if current_selection else None

        # Remove ports that are no longer available
        for port in current_ports:
            if port not in ports:
                self.serial_service.close_port(port)
                self.defmt_service.stop(port)
                self.port_probe_buffer.pop(port, None)
                self.port_text_buffer.pop(port, None)
                self._defmt_prompt_shown.pop(port, None)
                
                # Remove from list
                for i in range(self.port_list.count()):
                    if self.port_list.item(i).text() == port:
                        self.port_list.takeItem(i)
                        break

        # Add new ports
        for port in ports:
            if port not in current_ports:
                self.port_list.addItem(port)
                self._start_serial_monitor(port)
                self.port_logs[port] = []

        # Show empty message if no ports
        if len(ports) == 0 and self.port_list.count() == 0:
            self.port_list.addItem("No USB devices connected")
            item = self.port_list.item(0)
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            item.setTextAlignment(Qt.AlignCenter)
            item.setForeground(QApplication.palette().color(self.port_list.foregroundRole()))
            font = item.font()
            font.setItalic(True)
            item.setFont(font)
        # Remove placeholder if ports are found
        elif len(ports) > 0 and self.port_list.count() > 0:
            first_item = self.port_list.item(0)
            if first_item and first_item.text() == "No USB devices connected":
                self.port_list.takeItem(0)

        # Restore selection if still available
        if current_selection_text and current_selection_text in ports:
            for i in range(self.port_list.count()):
                if self.port_list.item(i).text() == current_selection_text:
                    self.port_list.setCurrentRow(i)
                    break
        elif self.port_list.count() > 0 and not current_selection:
            if self.port_list.item(0).text() != "No USB devices connected":
                self.port_list.setCurrentRow(0)
    
    def _start_serial_monitor(self, port: str):
        """Start monitoring a serial port."""
        success = self.serial_service.open_port(port)
        
        # Reset defmt auto-detection state so a fresh connection is re-probed
        self.defmt_service.stop(port)
        self.port_probe_buffer.pop(port, None)
        self.port_text_buffer.pop(port, None)
        self._defmt_prompt_shown.pop(port, None)
        
        if success:
            log_entry = self.log_formatter.create_success_message(
                f'Connected to {port} at {self.serial_service.baud_rate} baud'
            )
        else:
            log_entry = self.log_formatter.create_error_message(
                f'Failed to connect to {port}'
            )
        
        if port not in self.port_logs:
            self.port_logs[port] = []
        self.port_logs[port].append(log_entry)
        
        if self.active_port == port:
            self.log_text_edit.append(log_entry)
    
    def _logger(self):
        """Read and log data from all serial ports, auto-detecting defmt streams."""
        for port_name in list(self.serial_service.connections.keys()):
            if self.defmt_service.is_running(port_name):
                self._pump_defmt_logs(port_name)
                continue
            
            raw_data = self.serial_service.read_raw_bytes(port_name)
            if not raw_data:
                continue
            
            # Keep a rolling window of recent bytes to continuously re-check for a
            # switch to defmt (e.g. a device's plain-text bootloader output is
            # followed by defmt-encoded logs once the application firmware starts).
            probe = (self.port_probe_buffer.get(port_name, b'') + raw_data)[-DEFMT_PROBE_WINDOW_BYTES:]
            self.port_probe_buffer[port_name] = probe
            
            if len(probe) >= DEFMT_PROBE_MIN_BYTES and looks_like_defmt_stream(probe) \
                    and self._try_auto_enable_defmt(port_name):
                self.defmt_service.write(port_name, probe)
                self.port_probe_buffer.pop(port_name, None)
                self.port_text_buffer.pop(port_name, None)
                self._pump_defmt_logs(port_name)
                continue
            
            self._process_text_bytes(port_name, raw_data)
    
    def _process_text_bytes(self, port_name: str, raw_data: bytes):
        """Split buffered raw bytes into text log lines and display them."""
        buffer = self.port_text_buffer.get(port_name, b'') + raw_data
        *complete_lines, remainder = buffer.split(b'\n')
        self.port_text_buffer[port_name] = remainder
        
        for raw_line in complete_lines:
            line = raw_line.decode('utf-8', errors='ignore').strip()
            if line:
                self._append_log(port_name, self.log_formatter.colorize_line(line))
    
    def _try_auto_enable_defmt(self, port_name: str) -> bool:
        """Silently enable defmt decoding for a port using a known or auto-discovered ELF."""
        if not self.defmt_service.is_available():
            return False
        
        # Each port is matched to its own firmware ELF - different boards run different
        # firmware, and a defmt table only decodes the exact build it came from.
        settings_prefix = f'defmt/ports/{port_name}'
        
        pinned_elf = self.settings.value(f'{settings_prefix}/elf_path', '')
        if pinned_elf and is_valid_elf(pinned_elf):
            return self._start_defmt(port_name, pinned_elf)
        
        project_root = self.settings.value(f'{settings_prefix}/project_root', '')
        if project_root and os.path.isdir(project_root):
            now = time.monotonic()
            if now >= self._elf_discovery_cooldown_until:
                self._elf_discovery_cooldown_until = now + DEFMT_DISCOVERY_COOLDOWN_SECONDS
                candidates = find_elf_candidates(project_root)
                if candidates:
                    return self._start_defmt(port_name, candidates[0])
            return False
        
        self._prompt_for_defmt_source(port_name)
        return False
    
    def _start_defmt(self, port_name: str, elf_path: str) -> bool:
        """Start the defmt decoder for a port and log that decoding kicked in."""
        if not self.defmt_service.start(port_name, elf_path):
            return False
        
        self._append_log(
            port_name,
            self.log_formatter.create_info_message(
                f'Detected defmt-encoded log on {port_name}; decoding with {os.path.basename(elf_path)}'
            )
        )
        return True
    
    def _prompt_for_defmt_source(self, port_name: str):
        """
        Ask, once per port, where to find the firmware ELF for defmt decoding.
        
        defmt strips format strings from the log stream entirely - they only exist in the
        compiled ELF used at build time, so decoding is impossible without a copy of it.
        Each port is asked separately since different boards run different firmware.
        """
        if self._defmt_prompt_shown.get(port_name):
            return
        self._defmt_prompt_shown[port_name] = True
        
        box = QMessageBox(self)
        box.setWindowTitle("defmt-encoded log detected")
        box.setText(
            f"{port_name} appears to be sending defmt-encoded logs. These can only be decoded "
            "using the exact compiled ELF file from the firmware build - the format strings "
            "aren't sent over the wire."
        )
        folder_button = box.addButton("Project Folder...", QMessageBox.YesRole)
        file_button = box.addButton("Exact ELF File...", QMessageBox.YesRole)
        box.addButton("Skip", QMessageBox.RejectRole)
        box.exec_()
        clicked = box.clickedButton()
        
        settings_prefix = f'defmt/ports/{port_name}'
        if clicked is folder_button:
            folder = QFileDialog.getExistingDirectory(self, "Select Firmware Project Folder")
            if folder:
                self.settings.setValue(f'{settings_prefix}/project_root', folder)
        elif clicked is file_button:
            elf_path, _ = QFileDialog.getOpenFileName(self, "Select Firmware ELF File", "", "All Files (*)")
            if elf_path and is_valid_elf(elf_path):
                self.settings.setValue(f'{settings_prefix}/elf_path', elf_path)
            elif elf_path:
                QMessageBox.critical(self, "Error", "That file doesn't look like a valid ELF binary")
    
    def _pump_defmt_logs(self, port_name: str):
        """Forward raw bytes to the port's defmt decoder and display decoded lines."""
        raw_data = self.serial_service.read_raw_bytes(port_name)
        if raw_data:
            self.defmt_service.write(port_name, raw_data)
        
        for decoded_line in self.defmt_service.poll_lines(port_name):
            colorized_line = self.log_formatter.colorize_defmt_line(decoded_line)
            self._append_log(port_name, colorized_line)
        
        for error_line in self.defmt_service.poll_errors(port_name):
            self._append_log(port_name, self.log_formatter.create_warning_message(error_line))
    
    def _append_log(self, port_name: str, log_entry: str):
        """Store a log entry for a port and display it if that port is active."""
        if port_name not in self.port_logs:
            self.port_logs[port_name] = []
        self.port_logs[port_name].append(log_entry)
        
        if self.active_port == port_name:
            self.log_text_edit.append(log_entry)
            # Only auto-scroll if user hasn't scrolled up
            if self.auto_scroll:
                scrollbar = self.log_text_edit.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
    
    def _clear_logs(self):
        """Clear logs for active port."""
        if self.active_port:
            self.port_logs[self.active_port] = []
            self.log_text_edit.clear()
            self.log_text_edit.append(self.log_formatter.create_info_message('Logs cleared'))
            self.auto_scroll = True
    
    def _save_logs(self):
        """Save logs for active port."""
        if not self.active_port:
            QMessageBox.warning(self, "Warning", "No port selected")
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"serial_log_{self.active_port.replace('/', '_')}_{timestamp}.txt"
            
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save Logs",
                default_filename,
                "Text Files (*.txt);;All Files (*)"
            )
            
            if filename:
                with open(filename, 'w') as f:
                    plain_text = self.log_text_edit.toPlainText()
                    f.write(plain_text)
                
                QMessageBox.information(self, "Success", f"Logs saved to {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save logs: {str(e)}")
    
    def _reconnect_all_ports(self):
        """Reconnect all ports."""
        for i in range(self.port_list.count()):
            port_name = self.port_list.item(i).text()
            if port_name == "No USB devices connected":
                continue
            
            log_entry = self.log_formatter.create_warning_message(
                f'Reconnecting {port_name}...'
            )
            
            if port_name not in self.port_logs:
                self.port_logs[port_name] = []
            self.port_logs[port_name].append(log_entry)
            
            if self.active_port == port_name:
                self.log_text_edit.append(log_entry)
            
            self._start_serial_monitor(port_name)
    
    def _reboot_esp32(self):
        """Reboot the ESP32 on the active port."""
        if not self.active_port:
            QMessageBox.warning(self, "Warning", "No port selected")
            return
        
        log_entry = self.log_formatter.create_warning_message(
            f'Rebooting ESP32 on {self.active_port}...'
        )
        self.port_logs[self.active_port].append(log_entry)
        self.log_text_edit.append(log_entry)
        
        # Pass callback to handle completion
        success = self.serial_service.reboot_esp32(
            self.active_port, 
            complete_callback=self._handle_reboot_completion
        )
        
        if success:
            # Schedule completion after delay
            complete_callback = self.serial_service.get_complete_reboot_callback()
            if complete_callback:
                QTimer.singleShot(ESP32_REBOOT_DELAY, complete_callback)
        else:
            error_msg = self.log_formatter.create_error_message(
                'Failed to reboot ESP32: Port not connected'
            )
            self.port_logs[self.active_port].append(error_msg)
            self.log_text_edit.append(error_msg)
    
    def _handle_reboot_completion(self, success: bool, error: str = None):
        """Handle ESP32 reboot completion."""
        if success:
            log_entry = self.log_formatter.create_success_message(
                'ESP32 rebooted successfully'
            )
        else:
            log_entry = self.log_formatter.create_error_message(
                f'Reboot completion failed: {error}'
            )
        
        if self.active_port in self.port_logs:
            self.port_logs[self.active_port].append(log_entry)
            self.log_text_edit.append(log_entry)
    
    def _select_file_for_crc(self):
        """Open file dialog to select file for CRC calculation."""
        # Check if result box has content
        if self.crc_result.crc_value is not None:
            # Reset the result box
            self.crc_result.clear_crc_data()
            return
        
        # Open file picker
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select File for CRC",
            "",
            "All Files (*)"
        )
        if filename:
            self._calculate_crc(filename)
    
    def _calculate_crc(self, filename: str):
        """Calculate and display CRC32 for a file."""
        try:
            crc32, file_size, file_name = self.crc_service.calculate_crc32(filename)
            crc_hex = self.crc_service.format_crc32_hex(crc32)
            size_str = self.crc_service.format_file_size(file_size)
            
            self.crc_result.set_crc_data(crc_hex, file_name, size_str)
            
        except Exception as e:
            self.crc_result.set_error(str(e))
    
    def closeEvent(self, event):
        """Clean up when window is closed."""
        if self.logger_timer:
            self.logger_timer.stop()
        if self.port_refresh_timer:
            self.port_refresh_timer.stop()
        
        self.defmt_service.stop_all()
        self.serial_service.close_all_ports()
        event.accept()
