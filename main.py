import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTextEdit
from PyQt5.QtCore import QTimer
import serial
from serial.tools.list_ports_osx import comports

TIMEOUT = 50

class SerialPortWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Dometic | Serial Port Monitor')
        self.resize(1200, 1400)
        screen = QApplication.desktop().screenGeometry()
        self.resize(int(screen.width() // 1.5), int(screen.height() // 1.2))

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

        self.populate_serial_ports()
        self.start_serial_monitor(self.combo_box.currentText())

    def on_combobox_changed(self):
        # Call start_serial_monitor with the currently selected port
        self.start_serial_monitor(self.combo_box.currentText())
        self.log_text_edit.clear()

    def populate_serial_ports(self):
        ports = [port.device for port in comports()]
        if not ports:
            self.combo_box.addItem('No serial ports found.')
        else:
            self.combo_box.addItems(ports)

    def start_serial_monitor(self, port):
        if not port:
            return None
        self.port = port
        self.serial_port = serial.Serial(port, baudrate=115200, timeout=TIMEOUT/1000)
        self.timer = QTimer()
        self.timer.timeout.connect(self.logger)
        self.timer.start(TIMEOUT)

    def logger(self):
        try:
            if self.serial_port.in_waiting > 0:
                line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()

                # Skip empty lines
                if not line:
                    return
                   
                line = self.colorize_logs(line)
                self.log_text_edit.append(line)
                    
        except serial.SerialException as e:
            print(f'Could not open serial port: {e}')
        except KeyboardInterrupt:
            print('\nExiting script')
            self.serial_port.close()  # Close the serial port  

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
