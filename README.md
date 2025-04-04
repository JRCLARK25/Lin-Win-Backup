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
- Agent for scheduled backups
- Web interface for monitoring

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

3. Configure the backup settings:
```bash
cp .env.example .env
# Edit .env with your preferred settings
```

## Usage

### Creating a Full Backup
```bash
python lin_win_backup.py --type full --destination /path/to/backup
```

### Creating an Incremental Backup
```bash
python lin_win_backup.py --type incremental --destination /path/to/backup
```

### Creating a Bootable ISO
```bash
python lin_win_backup.py --type full --destination /path/to/backup --create-iso --output-iso /path/to/output.iso
```

### Restoring from Backup
```bash
python lin_win_backup.py --type restore --backup /path/to/backup
```

## Agent and Monitoring

### Installing the Agent as a Service

#### Linux
```bash
sudo python install_service.py --backup-dir /path/to/backup
```

#### Windows
```bash
python install_service.py --backup-dir C:\path\to\backup
```

### Running the Agent Manually
```bash
python agent.py --backup-dir /path/to/backup
```

### Web Interface
```bash
python web_interface.py --backup-dir /path/to/backup
```

The web interface provides real-time monitoring of:
- Agent status
- Current backup progress
- Next scheduled backup
- Disk usage
- Backup history

## License

This project is licensed under the MIT License - see the LICENSE file for details.
