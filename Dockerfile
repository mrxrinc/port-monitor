# Multi-stage Dockerfile for building Port Monitor executables
# Supports Windows .exe generation via Wine

FROM ubuntu:22.04 AS base

# Prevent interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies including Qt libraries
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3-dev \
    wget \
    xvfb \
    libxcb-xinerama0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxkbcommon-x11-0 \
    libdbus-1-3 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip and install build tools
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements and install Python dependencies
# Use pre-built wheels to avoid compilation issues
COPY requirements.txt .
RUN pip3 install --no-cache-dir \
    PyQt5-Qt5>=5.15.2 \
    PyQt5-sip>=12.11.0 \
    PyQt5>=5.15.0 \
    pyserial>=3.5 \
    pyinstaller

# Copy application files
COPY . .

# ============================================
# Stage for Linux Build
# ============================================
FROM base AS linux-build

RUN pyinstaller \
    --windowed \
    --icon=icon.png \
    --name 'Port Monitor' \
    --clean \
    main.py

# ============================================
# Stage for Windows Build (using Wine)
# ============================================
FROM base AS windows-build

# Install Wine for cross-compilation
RUN dpkg --add-architecture i386 && \
    mkdir -pm755 /etc/apt/keyrings && \
    wget -O /etc/apt/keyrings/winehq-archive.key https://dl.winehq.org/wine-builds/winehq.key && \
    wget -NP /etc/apt/sources.list.d/ https://dl.winehq.org/wine-builds/ubuntu/dists/jammy/winehq-jammy.sources && \
    apt-get update && \
    apt-get install -y --install-recommends winehq-stable && \
    rm -rf /var/lib/apt/lists/*

# Set Wine environment
ENV WINEARCH=win64 \
    WINEPREFIX=/root/.wine \
    DISPLAY=:0.0

# Initialize Wine
RUN wine wineboot --init && \
    wineserver -w

# Install Python in Wine
RUN wget https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe && \
    wine python-3.10.11-amd64.exe /quiet InstallAllUsers=1 PrependPath=1 && \
    rm python-3.10.11-amd64.exe

# Install Python packages in Wine
RUN wine pip install pyinstaller pyqt5 pyserial

# Build Windows executable
RUN xvfb-run wine pyinstaller \
    --windowed \
    --onefile \
    --icon=icon.ico \
    --name 'PortMonitor' \
    --clean \
    main.py

# ============================================
# Final stage - collect artifacts
# ============================================
FROM scratch AS artifacts

COPY --from=linux-build /app/dist ./linux/
COPY --from=windows-build /app/dist ./windows/

# ============================================
# Development stage for testing
# ============================================
FROM base AS dev

CMD ["/bin/bash"]