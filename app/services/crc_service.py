"""CRC32 calculation service for file integrity checking."""

import zlib
from typing import Tuple, Optional


class CRCService:
    """Service for calculating CRC32 checksums of files."""
    
    @staticmethod
    def calculate_crc32(file_path: str) -> Tuple[int, int, str]:
        """
        Calculate CRC32 checksum for a file.
        
        Args:
            file_path: Path to the file to calculate CRC for
            
        Returns:
            Tuple of (crc32_value, file_size_bytes, file_name)
            
        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If file cannot be read
        """
        with open(file_path, 'rb') as f:
            file_data = f.read()
            crc32 = zlib.crc32(file_data) & 0xffffffff
        
        file_size = len(file_data)
        file_name = file_path.split('/')[-1]
        
        return crc32, file_size, file_name
    
    @staticmethod
    def format_crc32_hex(crc32_value: int) -> str:
        """
        Format CRC32 value as hexadecimal string.
        
        Args:
            crc32_value: CRC32 integer value
            
        Returns:
            Formatted hex string (e.g., "0x12345678")
        """
        return f"0x{crc32_value:08X}"
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        Format file size in human-readable format.
        
        Args:
            size_bytes: File size in bytes
            
        Returns:
            Formatted size string (e.g., "123.45 KB")
        """
        size_kb = size_bytes / 1024
        return f"{size_kb:.2f} KB"
