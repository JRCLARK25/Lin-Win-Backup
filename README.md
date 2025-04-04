# Lin-Win-Backup

A cross-platform backup solution for Windows and Linux systems that provides full system backups, incremental backups, and bootable ISO creation capabilities.

## Features

- Full system backup
- Incremental backup support
- Bootable ISO creation from backups
- Cross-platform support (Windows and Linux)
- Compression and encryption options
- Backup scheduling
- Backup verification
- Restore capabilities

## Requirements

- Python 3.8 or higher
- Required Python packages (see requirements.txt)
- Administrative privileges for system backup
- Sufficient disk space for backups

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/Lin-Win-Backup.git
cd Lin-Win-Backup
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Creating a Full Backup
```bash
python lin_win_backup.py full-backup --destination /path/to/backup
```

### Creating an Incremental Backup
```bash
python lin_win_backup.py incremental-backup --destination /path/to/backup
```

### Creating a Bootable ISO
```bash
python lin_win_backup.py create-iso --backup /path/to/backup --output /path/to/output.iso
```

### Restoring from Backup
```bash
python lin_win_backup.py restore --backup /path/to/backup
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
