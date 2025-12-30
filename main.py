import sys
from datetime import datetime
import zlib
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QComboBox, QTextEdit, QPushButton, QListWidget, 
                             QFileDialog, QMessageBox, QAction, QMenuBar)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QCursor, QFont
import serial
from serial.tools.list_ports_osx import comports

TIMEOUT = 50
DEFAULT_BAUD_RATE = 115200
COMMON_BAUD_RATES = [300, 1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]
VERSION = "2.0.0"

class DropButton(QPushButton):
    """Custom button that accepts file drops"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setAcceptDrops(True)
        self.parent_window = parent
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                QPushButton {
                    background-color: rgba(0, 120, 215, 0.2);
                    border: 2px dashed rgba(0, 120, 215, 0.5);
                }
            """)
    
    def dragLeaveEvent(self, event):
        self.setStyleSheet("")
    
    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet("")
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files and self.parent_window:
            self.parent_window.calculate_crc(files[0])

class ClickableLabel(QLabel):
    """Clickable label that copies text to clipboard with press animation"""
    def __init__(self, text='', parent=None):
        super().__init__(text, parent)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.crc_value = None
        self.crc_hex_display = None
        self.file_info = None
        self.is_pressed = False
        self.reset_timer = None
        self.setMouseTracking(True)
        
    def mousePressEvent(self, event):
        if self.crc_value:
            self.is_pressed = True
            # Press animation - darker background
            original_style = self.styleSheet()
            press_style = original_style.replace("background-color: rgba(0, 200, 0, 0.05)", 
                                                  "background-color: rgba(0, 200, 0, 0.15)")
            press_style = press_style.replace("padding: 15px", "padding: 16px 14px 14px 16px")
            self.setStyleSheet(press_style)
    
    def mouseReleaseEvent(self, event):
        if self.crc_value and self.is_pressed:
            self.is_pressed = False
            clipboard = QApplication.clipboard()
            clipboard.setText(self.crc_value)
            
            # Update text to show "Copied"
            copied_html = f"""
            <div style="height: 100%; display: flex; flex-direction: column;">
                <div style="font-size: 11px; color: #888; text-align: left; margin-bottom: 5px;">
                    {self.file_info}
                </div>
                <div style="flex: 1; display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 18px; font-weight: bold; color: #28a745; letter-spacing: 1px;">
                        {self.crc_hex_display}
                    </span>
                    <span style="font-size: 14px; margin-left: 8px; color: #28a745;">
                    [Copied]
                    </span>
                </div>
            </div>
            """
            self.setText(copied_html)
            
            # Flash green feedback
            original_style = self.styleSheet()
            success_style = original_style.replace("background-color: rgba(0, 200, 0, 0.05)", 
                                                    "background-color: rgba(0, 255, 0, 0.25)")
            success_style = success_style.replace("padding: 16px 14px 14px 16px", "padding: 15px")
            self.setStyleSheet(success_style)
            
            QTimer.singleShot(200, lambda: self.setStyleSheet(original_style))
            
            # Cancel any existing timer
            if self.reset_timer:
                self.reset_timer.stop()
    
    def leaveEvent(self, event):
        """Called when mouse leaves the widget"""
        if self.crc_value and "[Copied]" in self.text():
            # Start 3 second timer after mouse leaves
            if self.reset_timer:
                self.reset_timer.stop()
            self.reset_timer = QTimer()
            self.reset_timer.setSingleShot(True)
            self.reset_timer.timeout.connect(self.reset_to_copy)
            self.reset_timer.start(3000)
    
    def enterEvent(self, event):
        """Called when mouse enters the widget"""
        # Cancel reset timer if mouse comes back
        if self.reset_timer:
            self.reset_timer.stop()
    
    def reset_to_copy(self):
        """Reset the text back to [Copy]"""
        if self.crc_value and self.file_info:
            original_html = f"""
            <div style="height: 100%; display: flex; flex-direction: column;">
                <div style="font-size: 11px; color: #888; text-align: left; margin-bottom: 5px;">
                    {self.file_info}
                </div>
                <div style="flex: 1; display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 18px; font-weight: bold; color: #28a745; letter-spacing: 1px;">
                        {self.crc_hex_display}
                    </span>
                    <span style="font-size: 14px; margin-left: 8px; color: #28a745;">
                    [Copy]
                    </span>
                </div>
            </div>
            """
            self.setText(original_html)
            self.reset_timer = None

class SerialPortWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('mrxrinc | Serial Port Monitor')
        self.resize(1200, 1400)
        screen = QApplication.desktop().screenGeometry()
        self.resize(int(screen.width() // 1.3), int(screen.height() // 1.2))
        
        self.serial_ports = {}  # Dictionary to store port connections
        self.port_logs = {}  # Dictionary to store logs for each port
        self.current_baud_rate = DEFAULT_BAUD_RATE
        self.active_port = None
        self.auto_scroll = True  # Track if we should auto-scroll

        # Create menu bar
        self.create_menu_bar()

        main_layout = QHBoxLayout(self)

        # Left panel
        left_layout = QVBoxLayout()
        
        self.label = QLabel('Serial Ports:')
        left_layout.addWidget(self.label)

        self.port_list = QListWidget()
        self.port_list.setFixedWidth(220)
        self.port_list.setStyleSheet("""
            QListWidget::item {
                border-bottom: 1px solid rgba(0, 0, 0, 0.1);
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: rgba(0, 120, 215, 0.15);
            }
        """)
        self.port_list.currentItemChanged.connect(self.on_port_selected)
        left_layout.addWidget(self.port_list)
        
        # Baud rate selector
        baud_label = QLabel('Baud Rate:')
        left_layout.addWidget(baud_label)
        
        self.baud_combo = QComboBox()
        self.baud_combo.setFixedWidth(220)
        for rate in COMMON_BAUD_RATES:
            self.baud_combo.addItem(str(rate))
        self.baud_combo.setCurrentText(str(DEFAULT_BAUD_RATE))
        self.baud_combo.currentTextChanged.connect(self.on_baud_rate_changed)
        left_layout.addWidget(self.baud_combo)
        
        # Control buttons

        self.space = QLabel(' ')
        left_layout.addWidget(self.space)
        
        self.clear_button = QPushButton('Clear Logs')
        self.clear_button.setFixedWidth(220)
        self.clear_button.clicked.connect(self.clear_logs)
        left_layout.addWidget(self.clear_button)
        
        self.save_button = QPushButton('Save Logs')
        self.save_button.setFixedWidth(220)
        self.save_button.clicked.connect(self.save_logs)
        left_layout.addWidget(self.save_button)
        
        self.reconnect_button = QPushButton('Reconnect All')
        self.reconnect_button.setFixedWidth(220)
        self.reconnect_button.clicked.connect(self.reconnect_all_ports)
        left_layout.addWidget(self.reconnect_button)

        self.space = QLabel(' ')
        left_layout.addWidget(self.space)

        self.line = QLabel('----------------------------------')
        left_layout.addWidget(self.line)

        self.espTitle = QLabel('ESP32 Reboot:')
        left_layout.addWidget(self.espTitle)

        self.reboot_button = QPushButton('Reboot ESP32')
        self.reboot_button.setFixedWidth(220)
        self.reboot_button.clicked.connect(self.reboot_esp32)
        left_layout.addWidget(self.reboot_button)

        left_layout.addStretch(1)
        
        # CRC Generator section at bottom
        self.line2 = QLabel('----------------------------------')
        left_layout.addWidget(self.line2)
        
        self.crc_title = QLabel('CRC Generator:')
        left_layout.addWidget(self.crc_title)
        
        self.crc_button = DropButton('Click or Drop File Here', self)
        self.crc_button.setFixedWidth(220)
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
        self.crc_button.clicked.connect(self.select_file_for_crc)
        left_layout.addWidget(self.crc_button)
        
        self.crc_result = ClickableLabel('', self)
        self.crc_result.setFixedWidth(220)
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
        left_layout.addWidget(self.crc_result)

        main_layout.addLayout(left_layout)

        # Right panel
        right_layout = QVBoxLayout()
        self.log_label = QLabel('Logs:')
        right_layout.addWidget(self.log_label)

        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        font = self.log_text_edit.font()
        font.setPointSize(14)
        font.setFamilies(["Menlo", "Consolas", "Courier New"])
        self.log_text_edit.setFont(font)
        
        # Connect scrollbar value changed to detect user scrolling
        scrollbar = self.log_text_edit.verticalScrollBar()
        scrollbar.valueChanged.connect(self.on_scroll_changed)
        
        right_layout.addWidget(self.log_text_edit)

        main_layout.addLayout(right_layout)

        self.populate_serial_ports()
        
        # Start port refresh timer
        self.port_refresh_timer = QTimer()
        self.port_refresh_timer.timeout.connect(self.populate_serial_ports)
        self.port_refresh_timer.start(1000)
        
        # Start logger timer
        self.logger_timer = QTimer()
        self.logger_timer.timeout.connect(self.logger)
        self.logger_timer.start(TIMEOUT)

    def create_menu_bar(self):
        """Create the menu bar with About menu"""
        menubar = QMenuBar(self)
        menubar.setGeometry(0, 0, self.width(), 30)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        # About action
        about_action = QAction('About Port Monitor', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def show_about(self):
        """Show about dialog"""
        about_text = f"""
        <h2>Port Monitor</h2>
        <p><b>Version:</b> {VERSION}</p>
        <p><b>Author:</b> <a href="https://github.com/mrxrinc">@mrxrinc</a></p>
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
        
        QMessageBox.about(self, "About Port Monitor", about_text)

    def select_file_for_crc(self):
        """Open file dialog to select file for CRC calculation"""
        # Check if result box has content
        if self.crc_result.crc_value is not None:
            # Reset the result box and don't open file picker
            self.crc_result.setText('')
            self.crc_result.crc_value = None
            self.crc_result.crc_hex_display = None
            self.crc_result.file_info = None
            if self.crc_result.reset_timer:
                self.crc_result.reset_timer.stop()
                self.crc_result.reset_timer = None
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
            return  # Don't open file picker
        
        # Result box is empty, open file picker normally
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select File for CRC",
            "",
            "All Files (*)"
        )
        if filename:
            self.calculate_crc(filename)
    
    def calculate_crc(self, filename):
        """Calculate CRC32 for the given file"""
        try:
            with open(filename, 'rb') as f:
                file_data = f.read()
                crc32 = zlib.crc32(file_data) & 0xffffffff
                
            # Get file size
            file_size = len(file_data)
            size_kb = file_size / 1024
            
            # Display result with better formatting
            file_name = filename.split('/')[-1]
            crc_hex = f"0x{crc32:08X}"
            
            # Store file info for later use
            file_info = f"{file_name}<br/>{size_kb:.2f} KB"
            
            # HTML formatted result with proper alignment and sizing
            result_html = f"""
            <div style="height: 100%; display: flex; flex-direction: column;">
                <div style="font-size: 11px; color: #888; text-align: left; margin-bottom: 5px;">
                    {file_info}
                </div>
                <div style="flex: 1; display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 18px; font-weight: bold; color: #28a745; letter-spacing: 1px;">
                        {crc_hex}
                    </span>
                    <span style="font-size: 14px; margin-left: 8px; color: #28a745;">
                    [Copy]
                    </span>
                </div>
            </div>
            """
            
            self.crc_result.setText(result_html)
            self.crc_result.crc_value = crc_hex
            self.crc_result.crc_hex_display = crc_hex
            self.crc_result.file_info = file_info
            self.crc_result.setStyleSheet("""
                QLabel {
                    font-size: 11px;
                    color: green;
                    padding: 15px;
                    border: 1px solid rgba(0, 200, 0, 0.3);
                    border-radius: 5px;
                    background-color: rgba(0, 200, 0, 0.05);
                }
                QLabel:hover {
                    background-color: rgba(0, 200, 0, 0.1);
                    border: 1px solid rgba(0, 200, 0, 0.5);
                }
            """)
            
        except Exception as e:
            self.crc_result.setText(f"<div style='color: red; text-align: center;'>❌ Error:<br/>{str(e)}</div>")
            self.crc_result.crc_value = None
            self.crc_result.setStyleSheet("""
                QLabel {
                    font-size: 11px;
                    color: red;
                    padding: 15px;
                    border: 1px solid rgba(255, 0, 0, 0.3);
                    border-radius: 5px;
                    background-color: rgba(255, 0, 0, 0.05);
                }
            """) 

    def on_scroll_changed(self, value):
        """Detect if user scrolled away from bottom or back to bottom"""
        scrollbar = self.log_text_edit.verticalScrollBar()
        # Check if we're at the bottom (within 10 pixels tolerance)
        at_bottom = value >= scrollbar.maximum() - 10
        self.auto_scroll = at_bottom

    def on_port_selected(self, current, previous):
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
    
    def on_baud_rate_changed(self, value):
        self.current_baud_rate = int(value)
        # Reconnect all ports with new baud rate
        self.reconnect_all_ports()

    def populate_serial_ports(self):
        # Filter for USB ports only
        all_ports = comports()
        ports = [port.device for port in all_ports if 'usb' in port.device.lower() or 'USB' in port.description]
        
        current_ports = [self.port_list.item(i).text() for i in range(self.port_list.count())]
        current_selection = self.port_list.currentItem()
        current_selection_text = current_selection.text() if current_selection else None

        # Remove ports that are no longer available
        for port in current_ports:
            if port not in ports:
                # Close connection if exists
                if port in self.serial_ports:
                    try:
                        self.serial_ports[port].close()
                    except:
                        pass
                    del self.serial_ports[port]
                
                # Remove from list
                for i in range(self.port_list.count()):
                    if self.port_list.item(i).text() == port:
                        self.port_list.takeItem(i)
                        break

        # Add new ports
        for port in ports:
            if port not in current_ports:
                self.port_list.addItem(port)
                self.start_serial_monitor(port)
                self.port_logs[port] = []

        # Restore selection if still available
        if current_selection_text and current_selection_text in ports:
            for i in range(self.port_list.count()):
                if self.port_list.item(i).text() == current_selection_text:
                    self.port_list.setCurrentRow(i)
                    break
        elif self.port_list.count() > 0 and not current_selection:
            self.port_list.setCurrentRow(0)

    def start_serial_monitor(self, port):
        try:
            if not port:
                return None
            
            # Close existing connection for this port
            if port in self.serial_ports:
                try:
                    self.serial_ports[port].close()
                except:
                    pass
            
            # Open new connection
            serial_port = serial.Serial(port, baudrate=self.current_baud_rate, timeout=TIMEOUT/1000)
            self.serial_ports[port] = serial_port
            
            # Log connection
            log_entry = f'<p style="color:lime;">Connected to {port} at {self.current_baud_rate} baud</p>'
            if port not in self.port_logs:
                self.port_logs[port] = []
            self.port_logs[port].append(log_entry)
            
            # Update display if this is the active port
            if self.active_port == port:
                self.log_text_edit.append(log_entry)
                
        except (serial.SerialException, AttributeError, OSError) as e:
            log_entry = f'<p style="color:red;">Failed to connect to {port}: {str(e)}</p>'
            if port not in self.port_logs:
                self.port_logs[port] = []
            self.port_logs[port].append(log_entry)
            
            if self.active_port == port:
                self.log_text_edit.append(log_entry)

    def logger(self):
        # Read from all connected ports
        for port_name, serial_port in list(self.serial_ports.items()):
            try:
                if not serial_port or not serial_port.is_open:
                    continue

                if serial_port.in_waiting > 0:
                    line = serial_port.readline().decode('utf-8', errors='ignore').strip()

                    if line:
                        colorized_line = self.colorize_logs(line)
                        
                        # Store in background logs
                        if port_name not in self.port_logs:
                            self.port_logs[port_name] = []
                        self.port_logs[port_name].append(colorized_line)
                        
                        # Display if active port
                        if self.active_port == port_name:
                            self.log_text_edit.append(colorized_line)
                            # Only auto-scroll if user hasn't scrolled up
                            if self.auto_scroll:
                                scrollbar = self.log_text_edit.verticalScrollBar()
                                scrollbar.setValue(scrollbar.maximum())

            except (serial.SerialException, AttributeError, OSError) as e:
                log_entry = f'<p style="color:red;">Serial port error on {port_name}: {str(e)}</p>'
                if port_name not in self.port_logs:
                    self.port_logs[port_name] = []
                self.port_logs[port_name].append(log_entry)
                
                if self.active_port == port_name:
                    self.log_text_edit.append(log_entry)
                
                # Close and remove failed port
                try:
                    serial_port.close()
                except:
                    pass
                if port_name in self.serial_ports:
                    del self.serial_ports[port_name]

            except KeyboardInterrupt:
                print('\nExiting script')
                break
    
    def reboot_esp32(self):
        """Reboot the ESP32 on the active port"""
        if not self.active_port:
            QMessageBox.warning(self, "Warning", "No port selected")
            return
        
        try:
            if self.active_port in self.serial_ports:
                serial_port = self.serial_ports[self.active_port]
                
                # Log the reboot attempt
                log_entry = f'<p style="color:orange;">Rebooting ESP32 on {self.active_port}...</p>'
                self.port_logs[self.active_port].append(log_entry)
                self.log_text_edit.append(log_entry)
                
                # Toggle DTR and RTS to reset ESP32
                serial_port.setDTR(False)
                serial_port.setRTS(True)
                QTimer.singleShot(100, lambda: self._complete_reboot(serial_port))
                
        except Exception as e:
            error_msg = f'<p style="color:red;">Failed to reboot ESP32: {str(e)}</p>'
            self.port_logs[self.active_port].append(error_msg)
            self.log_text_edit.append(error_msg)
    
    def _complete_reboot(self, serial_port):
        """Complete the ESP32 reboot sequence"""
        try:
            serial_port.setRTS(False)
            serial_port.setDTR(True)
            
            log_entry = f'<p style="color:lime;">ESP32 rebooted successfully</p>'
            if self.active_port in self.port_logs:
                self.port_logs[self.active_port].append(log_entry)
            self.log_text_edit.append(log_entry)
        except Exception as e:
            error_msg = f'<p style="color:red;">Reboot completion failed: {str(e)}</p>'
            if self.active_port in self.port_logs:
                self.port_logs[self.active_port].append(error_msg)
            self.log_text_edit.append(error_msg)
    
    def reconnect_all_ports(self):
        """Reconnect all ports"""
        for i in range(self.port_list.count()):
            port_name = self.port_list.item(i).text()
            log_entry = f'<p style="color:orange;">Reconnecting {port_name}...</p>'
            
            if port_name not in self.port_logs:
                self.port_logs[port_name] = []
            self.port_logs[port_name].append(log_entry)
            
            if self.active_port == port_name:
                self.log_text_edit.append(log_entry)
            
            self.start_serial_monitor(port_name)
    
    def clear_logs(self):
        """Clear logs for active port"""
        if self.active_port:
            self.port_logs[self.active_port] = []
            self.log_text_edit.clear()
            self.log_text_edit.append('<p style="color:gray;">Logs cleared</p>')
            self.auto_scroll = True
    
    def save_logs(self):
        """Save logs for active port"""
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
                    # Get plain text without HTML tags
                    plain_text = self.log_text_edit.toPlainText()
                    f.write(plain_text)
                
                QMessageBox.information(self, "Success", f"Logs saved to {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save logs: {str(e)}")

    def colorize_logs(self, line):
        if '[0;36mC' in line:
            line = '<p style="color:cyan;">' + line.replace('[0;36mC', '') + '</p>'
        elif '[0;32mI' in line:
            line =  '<p style="color:green;">' + line.replace('[0;32mI', '') + '</p>'
        elif '[0;32mW' in line or '[0;33mW' in line:
            line = '<p style="color:yellow;">' + line.replace('[0;32mW', '').replace('[0;33mW', '') + '</p>'
        elif '[0;31mE' in line:
            line = '<p style="color:red;">' + line.replace('[0;31mE', '') + '</p>'
        elif 'Error:' in line:
            line = '<p style="color:red;">' + line + '</p>'
        else:
            line = line

        return line
    
    def closeEvent(self, event):
        """Clean up when window is closed"""
        if self.logger_timer:
            self.logger_timer.stop()
        if self.port_refresh_timer:
            self.port_refresh_timer.stop()
        
        # Close all serial ports
        for port_name, serial_port in self.serial_ports.items():
            try:
                if serial_port.is_open:
                    serial_port.close()
            except:
                pass
        
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName("Port Monitor")
    window = SerialPortWindow()
    window.show()
    sys.exit(app.exec_())