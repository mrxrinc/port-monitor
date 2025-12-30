# Port Monitor

## Description

Port Monitor is a tool that allows you to monitor specific ports on your system.

**build for your OS with:**

recommended:

```bash
source venv/bin/activate

```

```bash
python -m PyInstaller \
  --windowed \
  --icon=icon.icns \
  -n Port Monitor \
  main.py
```

one file (not recommended):

```bash
pyinstaller --windowed --onefile --icon=icon.icns -n 'PortMonitor'  main.py
```

Author: Mohammad Mirzaei
