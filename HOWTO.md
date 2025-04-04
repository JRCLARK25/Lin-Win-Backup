# Lin-Win-Backup: Step-by-Step Guide

This guide will walk you through the installation, configuration, and usage of Lin-Win-Backup for both Windows and Linux systems.

## Table of Contents

1. [Installation](#installation)
2. [Basic Configuration](#basic-configuration)
3. [Remote Backup Setup](#remote-backup-setup)
4. [Creating Backups](#creating-backups)
5. [Managing Backups](#managing-backups)
6. [Restoring from Backups](#restoring-from-backups)
7. [Scheduling Backups](#scheduling-backups)
8. [Monitoring Backups](#monitoring-backups)
9. [Troubleshooting](#troubleshooting)

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/Lin-Win-Backup.git
cd Lin-Win-Backup
```

### Step 2: Install Dependencies

#### On Linux:
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-dev

# Install Python packages
pip3 install -r requirements.txt
```

#### On Windows:
```bash
# Install Python if not already installed
# Download from https://www.python.org/downloads/

# Install Python packages
pip install -r requirements.txt
```

## Basic Configuration

### Step 1: Create Configuration File

```bash
cp .env.example .env
```

### Step 2: Edit Configuration File

Open the `.env` file in your preferred text editor and configure the following settings:

```
# Backup Settings
COMPRESSION_LEVEL=6
ENCRYPTION_ENABLED=false
ENCRYPTION_KEY=
RETENTION_DAYS=30

# Paths
BACKUP_DIR=/path/to/backup/directory
TEMP_DIR=/path/to/temp/directory
LOG_DIR=/path/to/log/directory

# Exclusions
EXCLUDE_PATTERNS=*.tmp,*.log,*.cache
```

Replace the paths with your preferred locations. For Windows, use backslashes or escaped forward slashes:
```
BACKUP_DIR=C:\\Users\\YourUsername\\Backups
```

## Remote Backup Setup

### Step 1: Generate SSH Key (if you don't have one)

```bash
ssh-keygen -t rsa -b 4096
# Press Enter to save in default location
# Enter a passphrase or press Enter for no passphrase
```

### Step 2: Copy SSH Key to Backup Server

```bash
ssh-copy-id backup_user@backup_server_ip
# Enter your password when prompted
```

### Step 3: Configure Remote Backup Settings

Edit the `.env` file to add remote backup configuration:

```
# Remote Backup Settings
BACKUP_SERVER_IP=192.168.1.100
BACKUP_SERVER_PORT=22
BACKUP_SERVER_USER=backup_user
BACKUP_SERVER_PATH=/backup/storage
BACKUP_SERVER_SSH_KEY=/path/to/ssh/private/key
```

Replace the values with your actual server information.

## Creating Backups

### Step 1: Create a Full Backup

```bash
# On Linux
python3 lin_win_backup.py --type full --destination /path/to/backup

# On Windows
python lin_win_backup.py --type full --destination C:\path\to\backup
```

### Step 2: Create an Incremental Backup

```bash
# On Linux
python3 lin_win_backup.py --type incremental --destination /path/to/backup

# On Windows
python lin_win_backup.py --type incremental --destination C:\path\to\backup
```

### Step 3: Create a Bootable ISO from a Backup

```bash
# On Linux
python3 lin_win_backup.py --type full --destination /path/to/backup --create-iso --output-iso /path/to/output.iso

# On Windows
python lin_win_backup.py --type full --destination C:\path\to\backup --create-iso --output-iso C:\path\to\output.iso
```

## Managing Backups

### Step 1: List All Backups

```bash
# List local backups
python linwin.py list

# List remote backups
python linwin.py list --remote
```

### Step 2: View Backup Details

```bash
# View local backup details
python linwin.py details full_backup_20240315_020000

# View remote backup details
python linwin.py details full_backup_20240315_020000 --remote
```

### Step 3: Monitor In-Progress Backups

```bash
# Check local in-progress backups
python linwin.py progress

# Check remote in-progress backups
python linwin.py progress --remote
```

### Step 4: Delete a Backup

```bash
# Delete a local backup
python linwin.py delete full_backup_20240315_020000

# Delete a remote backup
python linwin.py delete full_backup_20240315_020000 --remote

# Force delete without confirmation
python linwin.py delete full_backup_20240315_020000 --force
```

### Step 5: Check Storage Usage

```bash
# Check local storage usage
python linwin.py usage

# Check remote storage usage
python linwin.py usage --remote
```

## Restoring from Backups

### Step 1: List Available Backups

```bash
python linwin.py list
```

### Step 2: Restore from a Backup

```bash
# On Linux
python3 lin_win_backup.py --type restore --backup /path/to/backup

# On Windows
python lin_win_backup.py --type restore --backup C:\path\to\backup
```

## Scheduling Backups

### Step 1: Install the Agent as a Service

#### On Linux:
```bash
sudo python3 install_service.py --backup-dir /path/to/backup
```

#### On Windows:
```bash
python install_service.py --backup-dir C:\path\to\backup
```

### Step 2: Configure Backup Schedule

Edit the `.env` file to add scheduling configuration:

```
# Scheduling
SCHEDULE_FULL_BACKUP=0 0 * * 0  # Every Sunday at midnight
SCHEDULE_INCREMENTAL_BACKUP=0 0 * * 1-6  # Every day except Sunday at midnight
```

### Step 3: Start the Agent

```bash
# On Linux
sudo systemctl start linwin-backup-agent

# On Windows
net start LinWinBackupAgent
```

## Monitoring Backups

### Step 1: Start the Web Interface

```bash
# On Linux
python3 web_interface.py --backup-dir /path/to/backup

# On Windows
python web_interface.py --backup-dir C:\path\to\backup
```

### Step 2: Access the Web Interface

Open your web browser and navigate to:
```
http://localhost:8080
```

The web interface provides real-time monitoring of:
- Agent status
- Current backup progress
- Next scheduled backup
- Disk usage
- Backup history

## Troubleshooting

### Common Issues and Solutions

#### Issue: Permission Denied
**Solution:** Run the command with administrative privileges (sudo on Linux, Run as Administrator on Windows)

#### Issue: SSH Connection Failed
**Solution:** 
1. Verify the server IP and port are correct
2. Check that your SSH key is properly set up
3. Ensure the backup server is running and accessible

#### Issue: Backup Process Hangs
**Solution:**
1. Check the logs in the LOG_DIR
2. Verify there's enough disk space
3. Check for network connectivity issues

#### Issue: Agent Service Not Starting
**Solution:**
1. Check the service logs
2. Verify the configuration file is correct
3. Ensure the backup directory exists and is accessible

### Getting Help

If you encounter issues not covered in this guide:
1. Check the logs in the LOG_DIR
2. Review the README.md file for additional information
3. Submit an issue on the GitHub repository

---

This guide covers the basic setup and usage of Lin-Win-Backup. For advanced features and options, refer to the README.md file. 