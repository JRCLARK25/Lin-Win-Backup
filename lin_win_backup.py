#!/usr/bin/env python3
import os
import sys
import argparse
import platform
import shutil
from datetime import datetime
from pathlib import Path
import psutil
from loguru import logger
import pycdlib
from tqdm import tqdm
from cryptography.fernet import Fernet
import schedule
import time
from dotenv import load_dotenv
import json
import hashlib
import tarfile
import gzip
from config import BACKUP_CONFIG, DEFAULT_PATHS, EXCLUDE_PATTERNS
from remote_backup import RemoteBackup

class BackupManager:
    def __init__(self, destination_path):
        self.destination_path = Path(destination_path)
        self.system = platform.system()
        self.backup_metadata = {}
        self.setup_logging()
        
    def setup_logging(self):
        logger.add("backup.log", rotation="1 day", retention="7 days")
        
    def create_backup_directory(self):
        """Create backup directory if it doesn't exist"""
        self.destination_path.mkdir(parents=True, exist_ok=True)
        
    def get_system_partitions(self):
        """Get system partitions based on OS"""
        partitions = []
        if self.system == "Linux":
            for partition in psutil.disk_partitions():
                if partition.mountpoint in ['/', '/home']:
                    partitions.append(partition)
        elif self.system == "Windows":
            for partition in psutil.disk_partitions():
                if partition.mountpoint in ['C:\\']:
                    partitions.append(partition)
        return partitions

    def create_full_backup(self):
        """Create a full system backup"""
        logger.info("Starting full system backup")
        self.create_backup_directory()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.destination_path / f"full_backup_{timestamp}"
        backup_dir.mkdir(exist_ok=True)
        
        partitions = self.get_system_partitions()
        for partition in tqdm(partitions, desc="Backing up partitions"):
            self._backup_partition(partition, backup_dir)
            
        self._save_metadata(backup_dir)
        logger.info("Full backup completed successfully")
        
    def create_incremental_backup(self):
        """Create an incremental backup"""
        logger.info("Starting incremental backup")
        self.create_backup_directory()
        
        # Find the latest backup
        latest_backup = self._get_latest_backup()
        if not latest_backup:
            logger.warning("No previous backup found. Creating full backup instead.")
            return self.create_full_backup()
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.destination_path / f"incremental_backup_{timestamp}"
        backup_dir.mkdir(exist_ok=True)
        
        # Compare and backup only changed files
        self._backup_changed_files(latest_backup, backup_dir)
        self._save_metadata(backup_dir)
        logger.info("Incremental backup completed successfully")

    def create_bootable_iso(self, backup_path, output_path):
        """Create a bootable ISO from backup"""
        logger.info("Creating bootable ISO")
        iso = pycdlib.PyCdlib()
        iso.new()
        
        # Add backup files to ISO
        self._add_files_to_iso(iso, backup_path)
        
        # Add boot files based on OS
        if self.system == "Linux":
            self._add_linux_boot_files(iso)
        else:
            self._add_windows_boot_files(iso)
            
        iso.write(output_path)
        iso.close()
        logger.info(f"Bootable ISO created at {output_path}")

    def _backup_partition(self, partition, backup_dir):
        """Backup a single partition"""
        partition_dir = backup_dir / partition.mountpoint.replace('/', '_').replace('\\', '_')
        partition_dir.mkdir(exist_ok=True)
        
        # Implementation depends on OS
        if self.system == "Linux":
            self._backup_linux_partition(partition, partition_dir)
        else:
            self._backup_windows_partition(partition, partition_dir)

    def _backup_changed_files(self, previous_backup, new_backup_dir):
        """Backup only files that have changed since last backup"""
        # Implementation for incremental backup
        pass

    def _save_metadata(self, backup_dir):
        """Save backup metadata"""
        metadata = {
            'timestamp': datetime.now().isoformat(),
            'system': self.system,
            'version': platform.version(),
            'partitions': [p.mountpoint for p in self.get_system_partitions()]
        }
        
        with open(backup_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=4)

    def _get_latest_backup(self):
        """Get the most recent backup directory"""
        backups = list(self.destination_path.glob('*_backup_*'))
        return max(backups, key=os.path.getctime) if backups else None

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Lin-Win-Backup: Cross-platform backup solution')
    parser.add_argument('--type', choices=['full', 'incremental', 'restore'], required=True,
                        help='Type of backup to perform')
    parser.add_argument('--destination', help='Backup destination directory (defaults to BACKUP_DIR from .env)')
    parser.add_argument('--backup', help='Backup to restore from (for restore type)')
    parser.add_argument('--create-iso', action='store_true', help='Create bootable ISO from backup')
    parser.add_argument('--output-iso', help='Output ISO file path')
    
    args = parser.parse_args()
    
    # Set default destination from .env if not provided
    if not args.destination and args.type != 'restore':
        args.destination = DEFAULT_PATHS['backup_dir']
        logger.info(f"Using default backup directory: {args.destination}")
    
    return args

def create_backup_directory(backup_type, destination):
    """Create a backup directory with timestamp"""
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = os.path.join(destination, f"{backup_type}_backup_{timestamp}")
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir

def get_file_hash(file_path):
    """Calculate SHA-256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def should_exclude(file_path):
    """Check if file should be excluded based on patterns"""
    for pattern in EXCLUDE_PATTERNS:
        if file_path.match(pattern):
            return True
    return False

def create_full_backup(destination):
    """Create a full system backup"""
    backup_dir = create_backup_directory('full', destination)
    logger.info(f"Creating full backup in {backup_dir}")
    
    # Create metadata file
    metadata = {
        'type': 'full',
        'timestamp': datetime.datetime.now().isoformat(),
        'files': []
    }
    
    # Get root directory based on OS
    if sys.platform == 'win32':
        root_dir = 'C:\\'
    else:
        root_dir = '/'
    
    # Create archive
    archive_path = os.path.join(backup_dir, 'backup.tar.gz')
    with tarfile.open(archive_path, 'w:gz') as tar:
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    # Skip excluded files
                    if should_exclude(Path(file_path)):
                        continue
                        
                    # Add file to archive
                    tar.add(file_path, arcname=os.path.relpath(file_path, root_dir))
                    
                    # Add to metadata
                    metadata['files'].append({
                        'path': os.path.relpath(file_path, root_dir),
                        'hash': get_file_hash(file_path)
                    })
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
    
    # Save metadata
    with open(os.path.join(backup_dir, 'metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"Full backup completed: {backup_dir}")
    return backup_dir

def create_incremental_backup(destination):
    """Create an incremental backup based on the last full backup"""
    # Find the last full backup
    backup_dirs = [d for d in os.listdir(destination) 
                   if os.path.isdir(os.path.join(destination, d)) 
                   and d.startswith('full_backup_')]
    
    if not backup_dirs:
        logger.warning("No full backup found. Creating a full backup instead.")
        return create_full_backup(destination)
    
    # Sort by timestamp (newest first)
    backup_dirs.sort(reverse=True)
    last_full_backup = os.path.join(destination, backup_dirs[0])
    
    # Create new backup directory
    backup_dir = create_backup_directory('incremental', destination)
    logger.info(f"Creating incremental backup in {backup_dir}")
    
    # Load last backup metadata
    with open(os.path.join(last_full_backup, 'metadata.json'), 'r') as f:
        last_metadata = json.load(f)
    
    # Create new metadata
    metadata = {
        'type': 'incremental',
        'timestamp': datetime.datetime.now().isoformat(),
        'base_backup': last_full_backup,
        'files': []
    }
    
    # Get root directory based on OS
    if sys.platform == 'win32':
        root_dir = 'C:\\'
    else:
        root_dir = '/'
    
    # Create archive
    archive_path = os.path.join(backup_dir, 'backup.tar.gz')
    with tarfile.open(archive_path, 'w:gz') as tar:
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    # Skip excluded files
                    if should_exclude(Path(file_path)):
                        continue
                    
                    rel_path = os.path.relpath(file_path, root_dir)
                    file_hash = get_file_hash(file_path)
                    
                    # Check if file has changed since last backup
                    file_changed = True
                    for old_file in last_metadata['files']:
                        if old_file['path'] == rel_path and old_file['hash'] == file_hash:
                            file_changed = False
                            break
                    
                    if file_changed:
                        # Add file to archive
                        tar.add(file_path, arcname=rel_path)
                        
                        # Add to metadata
                        metadata['files'].append({
                            'path': rel_path,
                            'hash': file_hash
                        })
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
    
    # Save metadata
    with open(os.path.join(backup_dir, 'metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"Incremental backup completed: {backup_dir}")
    return backup_dir

def restore_from_backup(backup_path):
    """Restore system from a backup"""
    if not os.path.exists(backup_path):
        logger.error(f"Backup not found: {backup_path}")
        return False
    
    # Load metadata
    try:
        with open(os.path.join(backup_path, 'metadata.json'), 'r') as f:
            metadata = json.load(f)
    except Exception as e:
        logger.error(f"Error loading metadata: {e}")
        return False
    
    # Extract archive
    archive_path = os.path.join(backup_path, 'backup.tar.gz')
    if not os.path.exists(archive_path):
        logger.error(f"Archive not found: {archive_path}")
        return False
    
    # Get root directory based on OS
    if sys.platform == 'win32':
        root_dir = 'C:\\'
    else:
        root_dir = '/'
    
    # Extract files
    with tarfile.open(archive_path, 'r:gz') as tar:
        tar.extractall(path=root_dir)
    
    logger.info(f"Restore completed from {backup_path}")
    return True

def create_bootable_iso(backup_path, output_iso):
    """Create a bootable ISO from a backup"""
    # This is a placeholder for ISO creation functionality
    # In a real implementation, this would use tools like mkisofs or similar
    logger.info(f"Creating bootable ISO from {backup_path} to {output_iso}")
    # Implementation would go here
    return True

def main():
    """Main function"""
    args = parse_arguments()
    
    # Configure logging
    log_dir = DEFAULT_PATHS['log_dir']
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    logger.add(log_file, rotation="10 MB")
    
    # Check if we're using remote backup
    if REMOTE_CONFIG['server_ip']:
        remote = RemoteBackup()
        if not remote.connect():
            logger.error("Failed to connect to remote backup server")
            return 1
    
    try:
        if args.type == 'full':
            backup_dir = create_full_backup(args.destination)
            
            if args.create_iso:
                if not args.output_iso:
                    args.output_iso = os.path.join(args.destination, f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.iso")
                create_bootable_iso(backup_dir, args.output_iso)
                
        elif args.type == 'incremental':
            backup_dir = create_incremental_backup(args.destination)
            
        elif args.type == 'restore':
            if not args.backup:
                logger.error("Backup path required for restore")
                return 1
            restore_from_backup(args.backup)
            
        return 0
        
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return 1
        
    finally:
        if REMOTE_CONFIG['server_ip']:
            remote.disconnect()

if __name__ == "__main__":
    sys.exit(main()) 