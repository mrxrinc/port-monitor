"""Custom PyQt5 widgets for the application."""

from PyQt5.QtWidgets import QPushButton, QLabel, QApplication
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QCursor
from typing import Optional, Callable


class DropButton(QPushButton):
    """Custom button that accepts file drops for drag-and-drop functionality."""
    
    def __init__(self, text: str, on_file_dropped: Optional[Callable[[str], None]] = None, parent=None):
        """
        Initialize drop button.
        
        Args:
            text: Button text
            on_file_dropped: Callback function when file is dropped
            parent: Parent widget
        """
        super().__init__(text, parent)
        self.setAcceptDrops(True)
        self.on_file_dropped = on_file_dropped
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                QPushButton {
                    background-color: rgba(0, 120, 215, 0.2);
                    border: 2px dashed rgba(0, 120, 215, 0.5);
                }
            """)
    
    def dragLeaveEvent(self, event):
        """Handle drag leave event."""
        self.setStyleSheet("")
    
    def dropEvent(self, event: QDropEvent):
        """Handle file drop event."""
        self.setStyleSheet("")
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files and self.on_file_dropped:
            self.on_file_dropped(files[0])


class ClickableLabel(QLabel):
    """
    Clickable label that copies text to clipboard with press animation.
    Used for displaying CRC values that can be copied.
    """
    
    def __init__(self, text: str = '', parent=None):
        """
        Initialize clickable label.
        
        Args:
            text: Initial label text
            parent: Parent widget
        """
        super().__init__(text, parent)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.crc_value: Optional[str] = None
        self.crc_hex_display: Optional[str] = None
        self.file_info: Optional[str] = None
        self.is_pressed: bool = False
        self.reset_timer: Optional[QTimer] = None
        self.setMouseTracking(True)
        
    def set_crc_data(self, crc_hex: str, file_name: str, file_size_str: str):
        """
        Set CRC data to display.
        
        Args:
            crc_hex: Hexadecimal CRC value
            file_name: Name of the file
            file_size_str: Formatted file size string
        """
        self.crc_value = crc_hex
        self.crc_hex_display = crc_hex
        self.file_info = f"{file_name}<br/>{file_size_str}"
        
        html = self._create_display_html(crc_hex, self.file_info, "[Copy]")
        self.setText(html)
        
        # Apply success styling
        self.setStyleSheet("""
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
    
    def clear_crc_data(self):
        """Clear CRC data and reset label."""
        self.crc_value = None
        self.crc_hex_display = None
        self.file_info = None
        self.setText('')
        
        if self.reset_timer:
            self.reset_timer.stop()
            self.reset_timer = None
        
        # Apply default styling
        self.setStyleSheet("""
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
    
    def set_error(self, error_message: str):
        """
        Display error message.
        
        Args:
            error_message: Error message to display
        """
        self.crc_value = None
        self.setText(f"<div style='color: red; text-align: center;'>❌ Error:<br/>{error_message}</div>")
        self.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: red;
                padding: 15px;
                border: 1px solid rgba(255, 0, 0, 0.3);
                border-radius: 5px;
                background-color: rgba(255, 0, 0, 0.05);
            }
        """)
        
    def mousePressEvent(self, event):
        """Handle mouse press event."""
        if self.crc_value:
            self.is_pressed = True
            # Press animation - darker background
            original_style = self.styleSheet()
            press_style = original_style.replace(
                "background-color: rgba(0, 200, 0, 0.05)", 
                "background-color: rgba(0, 200, 0, 0.15)"
            )
            press_style = press_style.replace("padding: 15px", "padding: 16px 14px 14px 16px")
            self.setStyleSheet(press_style)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release event - copy to clipboard."""
        if self.crc_value and self.is_pressed:
            self.is_pressed = False
            clipboard = QApplication.clipboard()
            clipboard.setText(self.crc_value)
            
            # Update text to show "Copied"
            copied_html = self._create_display_html(
                self.crc_hex_display, 
                self.file_info, 
                "[Copied]"
            )
            self.setText(copied_html)
            
            # Flash green feedback
            original_style = self.styleSheet()
            success_style = original_style.replace(
                "background-color: rgba(0, 200, 0, 0.05)", 
                "background-color: rgba(0, 255, 0, 0.25)"
            )
            success_style = success_style.replace("padding: 16px 14px 14px 16px", "padding: 15px")
            self.setStyleSheet(success_style)
            
            QTimer.singleShot(200, lambda: self.setStyleSheet(original_style))
            
            # Cancel any existing timer
            if self.reset_timer:
                self.reset_timer.stop()
    
    def leaveEvent(self, event):
        """Handle mouse leave event - start timer to reset [Copied] text."""
        if self.crc_value and "[Copied]" in self.text():
            # Start 3 second timer after mouse leaves
            if self.reset_timer:
                self.reset_timer.stop()
            self.reset_timer = QTimer()
            self.reset_timer.setSingleShot(True)
            self.reset_timer.timeout.connect(self.reset_to_copy)
            self.reset_timer.start(3000)
    
    def enterEvent(self, event):
        """Handle mouse enter event - cancel reset timer."""
        if self.reset_timer:
            self.reset_timer.stop()
    
    def reset_to_copy(self):
        """Reset the text back to [Copy]."""
        if self.crc_value and self.file_info:
            original_html = self._create_display_html(
                self.crc_hex_display, 
                self.file_info, 
                "[Copy]"
            )
            self.setText(original_html)
            self.reset_timer = None
    
    @staticmethod
    def _create_display_html(crc_hex: str, file_info: str, action_text: str) -> str:
        """
        Create HTML for displaying CRC information.
        
        Args:
            crc_hex: Hexadecimal CRC value
            file_info: File information HTML
            action_text: Action text to display (e.g., "[Copy]" or "[Copied]")
            
        Returns:
            HTML string for display
        """
        return f"""
        <div style="height: 100%; display: flex; flex-direction: column;">
            <div style="font-size: 11px; color: #888; text-align: left; margin-bottom: 5px;">
                {file_info}
            </div>
            <div style="flex: 1; display: flex; align-items: center; justify-content: center;">
                <span style="font-size: 18px; font-weight: bold; color: #28a745; letter-spacing: 1px;">
                    {crc_hex}
                </span>
                <span style="font-size: 14px; margin-left: 8px; color: #28a745;">
                {action_text}
                </span>
            </div>
        </div>
        """
