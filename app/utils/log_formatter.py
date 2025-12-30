"""Utility for formatting and colorizing log messages."""

from typing import Dict


class LogFormatter:
    """Formatter for colorizing serial port log messages."""
    
    # ESP-IDF log level color codes
    LOG_COLOR_CODES = {
        '[0;36mC': 'cyan',    # Cyan
        '[0;32mI': 'green',   # Info (Green)
        '[0;32mW': 'yellow',  # Warning (Yellow)
        '[0;33mW': 'yellow',  # Warning (Yellow)
        '[0;31mE': 'red',     # Error (Red)
    }
    
    @staticmethod
    def colorize_line(line: str) -> str:
        """
        Apply HTML color formatting to a log line based on ESP-IDF color codes.
        
        Args:
            line: Raw log line from serial port
            
        Returns:
            HTML formatted line with color styling
        """
        # Check for specific error patterns
        if 'Error:' in line:
            return f'<p style="color:red;">{line}</p>'
        
        # Check for ESP-IDF color codes
        for code, color in LogFormatter.LOG_COLOR_CODES.items():
            if code in line:
                cleaned_line = line.replace(code, '')
                return f'<p style="color:{color};">{cleaned_line}</p>'
        
        # Return plain line if no color code found
        return line
    
    @staticmethod
    def create_success_message(message: str) -> str:
        """
        Create a success message in green color.
        
        Args:
            message: Message text
            
        Returns:
            HTML formatted success message
        """
        return f'<p style="color:lime;">{message}</p>'
    
    @staticmethod
    def create_error_message(message: str) -> str:
        """
        Create an error message in red color.
        
        Args:
            message: Message text
            
        Returns:
            HTML formatted error message
        """
        return f'<p style="color:red;">{message}</p>'
    
    @staticmethod
    def create_warning_message(message: str) -> str:
        """
        Create a warning message in orange color.
        
        Args:
            message: Message text
            
        Returns:
            HTML formatted warning message
        """
        return f'<p style="color:orange;">{message}</p>'
    
    @staticmethod
    def create_info_message(message: str) -> str:
        """
        Create an info message in gray color.
        
        Args:
            message: Message text
            
        Returns:
            HTML formatted info message
        """
        return f'<p style="color:gray;">{message}</p>'
