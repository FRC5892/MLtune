# Repository Structure

Quick guide to what's where in this repository.

## Top-Level Folders

```
MLTUNE/               ← Repo root 
├── MLtune/           ← Main tuning application (Python)
├── dashboard/        ← Web interface for monitoring
├── java-integration/ ← Files to copy into your robot code
├── scripts/          ← Launch scripts (START.sh, START.bat, etc.)
└── docs/             ← User and developer documentation
```

## Quick Start

**To run the tuner:**
- Windows: `scripts\START.bat`
- Mac/Linux: `scripts/START.sh`

**To integrate with your robot:**
- Copy files from `java-integration/` to your robot project
- See [INTEGRATION.md](INTEGRATION.md)

**To configure tuning:**
- Edit `mltune/config/COEFFICIENT_TUNING.py` (define parameters)
- Edit `mltune/config/TUNER_TOGGLES.ini` (behavior settings)

**For component details:**
- [mltune documentation](mltune/)
- [dashboard documentation](dashboard/)
- [java-integration documentation](java-integration/)
- [scripts documentation](scripts/)

## Detailed Breakdown

### mltune/
Main Python application for tuning.

- `tuner/` - Core tuning logic
  - `tuner.py` - Main coordinator
  - `optimizer.py` - Bayesian optimization algorithm
  - `nt_interface.py` - NetworkTables communication
  - `gui.py` - Desktop GUI window
  - `config.py` - Configuration loading
- `config/` - User configuration files
  - `COEFFICIENT_TUNING.py` - Define what to tune
  - `TUNER_TOGGLES.ini` - Behavior settings

### dashboard/
Web-based monitoring interface (http://localhost:8050).

- `app.py` - Main dashboard application
- `assets/` - CSS and JavaScript

### java-integration/
Files to integrate MLtune with your robot code.

- `TunerInterface.java` - Main interface (copy this)
- `LoggedTunableNumber.java` - Tunable wrapper (copy this)
- `FiringSolutionSolver.java` - Example implementation
- `Constants_Addition.java` - Example constants

### scripts/
Launch and utility scripts.

- `START.sh` / `START.bat` - Main launcher (use this)
- `RUN_TUNER.sh` / `RUN_TUNER.bat` - Alternative launcher
- `CREATE_DESKTOP_SHORTCUT.bat` - Windows shortcut creator
- `activate_venv.*` - Virtual environment auto-activation
- `tuner_daemon.py` - Background daemon mode

### docs/
Documentation.

- `GETTING_STARTED.md` - Installation guide
- `USAGE.md` - How to use the tuner
- `INTEGRATION.md` - Robot code integration
- `CONTRIBUTING.md` - Development guide

## Common Tasks

| Task | Location |
|------|----------|
| Run the tuner | `scripts/START.sh` or `scripts/START.bat` |
| Configure parameters | `mltune/config/COEFFICIENT_TUNING.py` |
| Change behavior | `mltune/config/TUNER_TOGGLES.ini` |
| Integrate with robot | `java-integration/` → copy to robot |
| View documentation | `docs/` |
| Modify tuning algorithm | `mltune/tuner/optimizer.py` |
| Change dashboard | `dashboard/app.py` |