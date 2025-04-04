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
- Remote backup server support
- Server-side backup management tools
- Unified command-line interface

## Requirements

- Python 3.8 or higher
- Required Python packages (see requirements.txt)
- Administrative privileges for system backup
- Sufficient disk space for backups
- SSH access to remote backup server (for remote backups)

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

## Remote Backup Configuration

To configure remote backup storage:

1. Set up SSH access to your backup server:
   ```bash
   # Generate SSH key if you don't have one
   ssh-keygen -t rsa -b 4096
   
   # Copy your public key to the backup server
   ssh-copy-id backup_user@backup_server_ip
   ```

2. Configure the remote backup settings in `.env`:
   ```
   BACKUP_SERVER_IP=192.168.1.100
   BACKUP_SERVER_PORT=22
   BACKUP_SERVER_USER=backup_user
   BACKUP_SERVER_PATH=/backup/storage
   BACKUP_SERVER_SSH_KEY=/path/to/ssh/private/key
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

## Backup Management

The Lin-Win-Backup management tool provides a unified interface for managing both local and remote backups:

### List Backups
```bash
# List all local backups sorted by date (newest first)
python linwin.py list

# List remote backups
python linwin.py list --remote

# List full backups only
python linwin.py list --type full

# List backups sorted by size
python linwin.py list --sort size

# List last 5 backups
python linwin.py list --limit 5

# Output in JSON format
python linwin.py list --format json

# Specify a custom backup directory
python linwin.py list --backup-dir /custom/path/to/backups
```

### View Backup Details
```bash
# Show detailed information about a specific local backup
python linwin.py details full_backup_20240315_020000

# Show details for a remote backup
python linwin.py details full_backup_20240315_020000 --remote
```

### Monitor In-Progress Backups
```bash
# Show currently running local backups
python linwin.py progress

# Show currently running remote backups
python linwin.py progress --remote
```

### Delete Backups
```bash
# Delete a local backup (with confirmation)
python linwin.py delete full_backup_20240315_020000

# Delete a remote backup
python linwin.py delete full_backup_20240315_020000 --remote

# Force delete without confirmation
python linwin.py delete full_backup_20240315_020000 --force
```

### View Storage Usage
```bash
# Show local storage usage information
python linwin.py usage

# Show remote storage usage information
python linwin.py usage --remote
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
