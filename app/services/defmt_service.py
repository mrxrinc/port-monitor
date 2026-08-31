"""defmt log decoding service.

defmt encodes log messages as compact binary frames (format string index +
arguments); the actual format strings only exist in the compiled ELF binary.
Reimplementing that decoder is error-prone, so this service shells out to the
official `defmt-print` tool (https://crates.io/crates/defmt-print), which
decodes frames using the ELF and prints plain text log lines. A prebuilt
binary is vendored under vendor/defmt-print/<platform>/ so users don't need
to install anything themselves; a PATH lookup is used as a fallback.
"""

import os
import platform
import queue
import shutil
import subprocess
import sys
import threading
import glob
from typing import Dict, List, Optional

DEFMT_PRINT_BINARY = "defmt-print"


def _vendor_dir_name() -> str:
    """Map the current OS/arch to the vendor subdirectory holding its binary."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    arch = 'arm64' if machine in ('arm64', 'aarch64') else 'x86_64'
    
    if system == 'darwin':
        return f'darwin-{arch}'
    if system == 'linux':
        return f'linux-{arch}'
    if system == 'windows':
        return f'windows-{arch}'
    return f'{system}-{arch}'


def _binary_filename() -> str:
    return 'defmt-print.exe' if platform.system().lower() == 'windows' else 'defmt-print'


def _bundled_binary_path() -> Optional[str]:
    """Locate the defmt-print binary vendored alongside the app, if present."""
    if hasattr(sys, '_MEIPASS'):
        base_dir = sys._MEIPASS  # PyInstaller-frozen app: files extracted here
    else:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    
    candidate = os.path.join(base_dir, 'vendor', 'defmt-print', _vendor_dir_name(), _binary_filename())
    if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
        return candidate
    return None


def resolve_defmt_print_path() -> Optional[str]:
    """Resolve the defmt-print executable: bundled binary first, then PATH."""
    bundled = _bundled_binary_path()
    if bundled:
        return bundled
    return shutil.which(DEFMT_PRINT_BINARY)


ELF_MAGIC = b'\x7fELF'


def is_valid_elf(path: str) -> bool:
    """Check whether a file starts with the ELF magic bytes."""
    try:
        with open(path, 'rb') as f:
            return f.read(4) == ELF_MAGIC
    except OSError:
        return False


# Bytes considered "plain text" for the purposes of distinguishing normal serial
# logs from binary defmt frames: printable ASCII plus common whitespace.
_TEXT_BYTES = set(range(0x20, 0x7f)) | {0x09, 0x0a, 0x0d}


def looks_like_defmt_stream(data: bytes) -> bool:
    """
    Heuristically decide whether a chunk of raw serial data looks like binary
    defmt frames rather than plain text log lines.
    
    Args:
        data: Sample of raw bytes read from the serial port
    
    Returns:
        True if the sample looks like binary/non-text data
    """
    if not data:
        return False
    
    non_text = sum(1 for byte in data if byte not in _TEXT_BYTES)
    return (non_text / len(data)) > 0.3


def find_elf_candidates(search_root: str) -> List[str]:
    """
    Look for likely firmware ELF files under common Rust build output directories.
    
    Args:
        search_root: Directory to search under (e.g. the current working directory)
    
    Returns:
        List of candidate ELF paths, most recently modified first
    """
    patterns = [
        'target/*/release/*',
        'target/*/debug/*',
        'target/release/*',
        'target/debug/*',
    ]
    candidates = []
    for pattern in patterns:
        for path in glob.glob(os.path.join(search_root, pattern)):
            if os.path.isfile(path) and is_valid_elf(path):
                candidates.append(path)
    
    candidates.sort(key=os.path.getmtime, reverse=True)
    return candidates


class DefmtSession:
    """Holds the subprocess and output queues for one port's defmt decoder."""

    def __init__(self, process: subprocess.Popen, elf_path: str):
        self.process = process
        self.elf_path = elf_path
        self.line_queue: "queue.Queue[str]" = queue.Queue()
        self.error_queue: "queue.Queue[str]" = queue.Queue()

        self._stdout_thread = threading.Thread(target=self._pump_stdout, daemon=True)
        self._stderr_thread = threading.Thread(target=self._pump_stderr, daemon=True)
        self._stdout_thread.start()
        self._stderr_thread.start()

    def _pump_stdout(self) -> None:
        stdout = self.process.stdout
        if stdout is None:
            return
        for raw_line in iter(stdout.readline, b''):
            line = raw_line.decode('utf-8', errors='replace').rstrip('\n')
            if line:
                self.line_queue.put(line)

    def _pump_stderr(self) -> None:
        stderr = self.process.stderr
        if stderr is None:
            return
        for raw_line in iter(stderr.readline, b''):
            line = raw_line.decode('utf-8', errors='replace').rstrip('\n')
            if line:
                self.error_queue.put(line)


class DefmtDecoderService:
    """Manages per-port `defmt-print` subprocesses that decode defmt-encoded serial data."""

    def __init__(self):
        self.sessions: Dict[str, DefmtSession] = {}

    @staticmethod
    def is_available() -> bool:
        """Check whether a defmt-print binary (bundled or on PATH) can be found."""
        return resolve_defmt_print_path() is not None

    def is_running(self, port_name: str) -> bool:
        """Check whether the port's decoder process is still alive, cleaning up if not."""
        session = self.sessions.get(port_name)
        if not session:
            return False
        
        if session.process.poll() is not None:
            self.stop(port_name)
            return False
        
        return True

    def start(self, port_name: str, elf_path: str) -> bool:
        """
        Start a defmt-print subprocess to decode data received on a port.

        Args:
            port_name: Name of the serial port
            elf_path: Path to the compiled ELF file containing defmt symbols

        Returns:
            True if the decoder process was started successfully
        """
        self.stop(port_name)

        binary_path = resolve_defmt_print_path()
        if not binary_path or not is_valid_elf(elf_path):
            return False
        
        try:
            process = subprocess.Popen(
                [binary_path, '-e', elf_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
            )
        except (OSError, FileNotFoundError):
            return False

        self.sessions[port_name] = DefmtSession(process, elf_path)
        return True

    def write(self, port_name: str, data: bytes) -> bool:
        """
        Feed raw serial bytes into the port's defmt decoder process.

        Args:
            port_name: Name of the port the bytes were read from
            data: Raw bytes read from the serial port

        Returns:
            True if the bytes were written successfully
        """
        if not self.is_running(port_name):
            return False
        
        session = self.sessions[port_name]
        try:
            session.process.stdin.write(data)
            session.process.stdin.flush()
            return True
        except (BrokenPipeError, OSError):
            self.stop(port_name)
            return False

    def poll_lines(self, port_name: str) -> List[str]:
        """Drain and return all decoded log lines currently available for a port."""
        return self._drain(port_name, error=False)

    def poll_errors(self, port_name: str) -> List[str]:
        """Drain and return decoder stderr output (e.g. malformed frame warnings)."""
        return self._drain(port_name, error=True)

    def _drain(self, port_name: str, error: bool) -> List[str]:
        session = self.sessions.get(port_name)
        if not session:
            return []

        target_queue = session.error_queue if error else session.line_queue
        items = []
        while True:
            try:
                items.append(target_queue.get_nowait())
            except queue.Empty:
                break
        return items

    def stop(self, port_name: str) -> None:
        """Stop and clean up the defmt decoder process for a port."""
        session = self.sessions.pop(port_name, None)
        if not session:
            return

        try:
            if session.process.stdin:
                session.process.stdin.close()
            session.process.terminate()
            session.process.wait(timeout=2)
        except Exception:
            try:
                session.process.kill()
            except Exception:
                pass

    def stop_all(self) -> None:
        """Stop all active defmt decoder processes."""
        for port_name in list(self.sessions.keys()):
            self.stop(port_name)
