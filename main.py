import usb.core
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTextEdit
from PyQt5.QtCore import QTimer
from serial import Serial
from serial.tools.list_ports_windows import comports

TIMEOUT = 50
BAUD_RATE = 115200

class SerialPortWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Dometic | Serial Port Monitor')
        self.resize(1200, 1400)
        screen = QApplication.desktop().screenGeometry()
        self.resize(int(screen.width() // 2), int(screen.height() // 1.8))

        main_layout = QHBoxLayout(self)

        left_layout = QVBoxLayout()
        self.label = QLabel('Select Serial Port:')
        left_layout.addWidget(self.label)

        self.combo_box = QComboBox()
        self.combo_box.setFixedWidth(200)
        self.combo_box.currentIndexChanged.connect(self.on_combobox_changed)
        left_layout.addWidget(self.combo_box)

        left_layout.addStretch(1)

        main_layout.addLayout(left_layout)

        right_layout = QVBoxLayout()
        self.log_label = QLabel('Logs:')
        right_layout.addWidget(self.log_label)

        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        font = self.log_text_edit.font()
        font.setPointSize(14)
        font.setFamilies(["Menlo", "Consolas", "Courier New"])
        self.log_text_edit.setFont(font)
        right_layout.addWidget(self.log_text_edit)

        main_layout.addLayout(right_layout)

        self.list_usb_devices()

        self.populate_serial_ports()
        

    def on_combobox_changed(self):
        # Call start_serial_monitor with the currently selected port
        self.start_serial_monitor(self.combo_box.currentText())
        self.log_text_edit.clear()
        self.timer = QTimer()
        self.timer.timeout.connect(self.logger)
        self.timer.timeout.connect(self.populate_serial_ports)
        self.timer.start(TIMEOUT)

    def populate_serial_ports(self):
        ports = [port.device for port in comports()]
        current_ports = [self.combo_box.itemText(i) for i in range(self.combo_box.count())]

        # Remove 'No serial ports found.' item if it exists
        if 'No serial ports found.' in current_ports:
            self.combo_box.removeItem(current_ports.index('No serial ports found.'))

        # Add new ports
        for port in ports:
            if port not in current_ports:
                self.combo_box.addItem(port)

        if self.combo_box.count() == 0:
            self.combo_box.addItem('No serial ports found.')

    def start_serial_monitor(self, port):
        try:
            if not port:
                return None
            self.port = port
            self.serial_port = Serial(port, baudrate=BAUD_RATE, timeout=TIMEOUT/1000)
        except (AttributeError, OSError):
            self.serial_port = None

    def list_usb_devices(self): # TODO: This function is not working
        dev = usb.core.find(find_all=True)
        for cfg in dev:
            print('ID_VENDOR_ID=' + hex(cfg.idVendor) + ', ID_PRODUCT_ID=' + hex(cfg.idProduct))

    def logger(self):
        try:
            if not self.serial_port or not self.serial_port.is_open:
                self.timer.stop()
                message = 'Serial port is not open'
                print(message)
                self.log_text_edit.append(message)
                return

            if self.serial_port.in_waiting > 0:
                line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()

                # Skip empty lines
                if line:
                    self.log_text_edit.append(self.colorize_logs(line))

        except ( AttributeError, OSError):
            print('Serial port is not available.')
            self.log_text_edit.append('Serial port is not available.')
            self.serial_port = None

        except KeyboardInterrupt:
            print('\nExiting script')
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()

    def colorize_logs(_, line):
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


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SerialPortWindow()
    window.show()
    sys.exit(app.exec_())
