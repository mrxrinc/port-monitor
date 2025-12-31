"""Serial port management service."""

import serial
import serial.tools.list_ports
from typing import Dict, List, Optional, Callable
from app.config import TIMEOUT


class SerialPortService:
    """Service for managing serial port connections and communication."""
    
    def __init__(self, baud_rate: int):
        """
        Initialize serial port service.
        
        Args:
            baud_rate: Default baud rate for connections
        """
        self.baud_rate = baud_rate
        self.connections: Dict[str, serial.Serial] = {}
    
    def get_available_usb_ports(self) -> List[str]:
        """
        Get list of available USB serial ports.
        
        Returns:
            List of USB port device names
        """
        all_ports = serial.tools.list_ports.comports()
        return [
            port.device 
            for port in all_ports 
            if 'usb' in port.device.lower() or 'USB' in port.description
        ]
    
    def open_port(self, port_name: str) -> bool:
        """
        Open a serial port connection.
        
        Args:
            port_name: Name of the port to open
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Close existing connection if any
            self.close_port(port_name)
            
            # Open new connection
            serial_port = serial.Serial(
                port_name, 
                baudrate=self.baud_rate, 
                timeout=TIMEOUT / 1000
            )
            self.connections[port_name] = serial_port
            return True
            
        except (serial.SerialException, AttributeError, OSError):
            return False
    
    def close_port(self, port_name: str) -> None:
        """
        Close a serial port connection.
        
        Args:
            port_name: Name of the port to close
        """
        if port_name in self.connections:
            try:
                self.connections[port_name].close()
            except:
                pass
            del self.connections[port_name]
    
    def close_all_ports(self) -> None:
        """Close all open serial port connections."""
        for port_name in list(self.connections.keys()):
            self.close_port(port_name)
    
    def read_line(self, port_name: str) -> Optional[str]:
        """
        Read a line from a serial port.
        
        Args:
            port_name: Name of the port to read from
            
        Returns:
            Decoded line string or None if no data or error
        """
        if port_name not in self.connections:
            return None
        
        serial_port = self.connections[port_name]
        
        try:
            if not serial_port.is_open:
                return None
            
            if serial_port.in_waiting > 0:
                line = serial_port.readline().decode('utf-8', errors='ignore').strip()
                return line if line else None
            
        except (serial.SerialException, AttributeError, OSError):
            # Connection error, remove it
            self.close_port(port_name)
            return None
        
        return None
    
    def set_baud_rate(self, baud_rate: int) -> None:
        """
        Update baud rate for all connections.
        
        Args:
            baud_rate: New baud rate
        """
        self.baud_rate = baud_rate
    
    def reconnect_all_ports(self) -> List[str]:
        """
        Reconnect all currently open ports.
        
        Returns:
            List of port names that were reconnected
        """
        port_names = list(self.connections.keys())
        for port_name in port_names:
            self.open_port(port_name)
        return port_names
    
    def reboot_esp32(self, port_name: str, complete_callback: Optional[Callable] = None) -> bool:
        """
        Reboot ESP32 on the specified port.
        
        Args:
            port_name: Name of the port with ESP32
            complete_callback: Optional callback to complete reboot after delay
            
        Returns:
            True if reboot initiated successfully, False otherwise
        """
        if port_name not in self.connections:
            return False
        
        try:
            serial_port = self.connections[port_name]
            
            # Toggle DTR and RTS to reset ESP32
            serial_port.setDTR(False)
            serial_port.setRTS(True)
            
            # Store callback for completing reboot
            if complete_callback:
                self._complete_reboot_callback = lambda: self._complete_esp32_reboot(
                    serial_port, complete_callback
                )
            
            return True
            
        except Exception:
            return False
    
    def _complete_esp32_reboot(self, serial_port: serial.Serial, callback: Callable) -> None:
        """
        Complete ESP32 reboot sequence.
        
        Args:
            serial_port: Serial port object
            callback: Callback to notify completion
        """
        try:
            serial_port.setRTS(False)
            serial_port.setDTR(True)
            callback(True, None)
        except Exception as e:
            callback(False, str(e))
    
    def get_complete_reboot_callback(self) -> Optional[Callable]:
        """Get the callback for completing ESP32 reboot."""
        return getattr(self, '_complete_reboot_callback', None)
