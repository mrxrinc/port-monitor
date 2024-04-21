# Use the official Ubuntu base image
FROM ubuntu:latest

# Update package lists and install dependencies
RUN dpkg --add-architecture amd64 && \
    apt-get update && apt-get install -y \
    wine64 \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV WINEARCH=win64 \
    WINEPREFIX=/root/.wine \
    DISPLAY=:0.0

# Create a symbolic link for wine to run without errors
# RUN ln -s /usr/bin/wine32 /usr/bin/wine

# Set the working directory
WORKDIR /app

# Copy your application files
COPY . .

# Specify the default command to run when the container starts
CMD ["/bin/bash"]


# Run PyInstaller to create the standalone executable
# RUN wine pyinstaller --windowed --onefile --icon=dometic-logo.icns -n DometicPortMonitor  /src/main.py