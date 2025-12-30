# Port Monitor

## Description

Port Monitor is a tool that allows you to monitor specific ports on your system.

**build for your OS with:**

recommended:

```bash
python -m PyInstaller \
  --windowed \
  --icon=dometic-logo.icns \
  -n PortMonitor \
  main.py
```

one file (not recommended):

```bash
pyinstaller --windowed --onefile --icon=dometic-logo.icns -n DometicPortMonitor  main.py
```

Author: Mohammad Mirzaei
