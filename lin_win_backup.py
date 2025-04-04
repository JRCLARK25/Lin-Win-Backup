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
from config import BACKUP_CONFIG, DEFAULT_PATHS, REMOTE_CONFIG
from remote_backup import RemoteBackup

# Get exclude patterns from BACKUP_CONFIG
EXCLUDE_PATTERNS = BACKUP_CONFIG['exclude_patterns']

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

    def _backup_linux_partition(self, partition, backup_dir):
        """Backup a Linux partition"""
        logger.info(f"Backing up Linux partition: {partition.mountpoint}")
        print(f"Starting backup of partition: {partition.mountpoint}")
        
        # Create a directory for this partition in the backup
        partition_backup_dir = backup_dir / partition.mountpoint.replace('/', '_')
        partition_backup_dir.mkdir(exist_ok=True)
        
        # Create a tar archive of the partition
        archive_path = partition_backup_dir / f"{partition.mountpoint.replace('/', '_')}.tar.gz"
        
        # Additional directories to exclude for Linux
        linux_exclude_dirs = [
            '/proc', 
            '/sys', 
            '/dev', 
            '/run', 
            '/tmp',
            '/var/tmp',
            '/var/cache',
            '/var/log',
            '/lost+found',
            '/mnt',
            '/media',
            '/boot',
            '/swap',
            '/swapfile',
            '~/Lin-Win-Backup/backups/'
        ]
        
        # Additional files to exclude for Linux
        linux_exclude_files = [
            'swapfile',
            '*.swp',
            '*.swap',
            '*.tmp',
            '*.log',
            '*.cache',
            '.cache',
            '.thumbnails'
        ]
        
        # Combine with existing exclude patterns
        all_exclude_dirs = linux_exclude_dirs + [p for p in EXCLUDE_PATTERNS if p.startswith('/')]
        all_exclude_files = linux_exclude_files + [p for p in EXCLUDE_PATTERNS if not p.startswith('/')]
        
        # Count stats
        files_processed = 0
        files_skipped = 0
        dirs_skipped = 0
        total_size = 0
        
        # Status update interval (seconds)
        status_interval = 5
        last_status_time = time.time()
        current_directory = ""
        
        with tarfile.open(archive_path, 'w:gz') as tar:
            # Walk through the partition directory
            for root, dirs, files in os.walk(partition.mountpoint):
                # Show current directory being processed (periodically)
                if time.time() - last_status_time > status_interval:
                    print(f"Processing: {root} | Files: {files_processed:,} processed, {files_skipped:,} skipped | Size: {total_size / (1024*1024):.2f} MB")
                    last_status_time = time.time()
                    
                current_directory = root
                
                # Skip excluded directories - more robust check
                should_skip = False
                for exclude_dir in all_exclude_dirs:
                    if root.startswith(exclude_dir) or exclude_dir in root.split('/'):
                        dirs_skipped += 1
                        should_skip = True
                        break
                
                if should_skip:
                    # Remove this directory from dirs list to prevent further walking
                    dirs.clear()
                    continue
                
                # Show progress for directories with many files
                if len(files) > 100:
                    print(f"Found {len(files):,} files in {root}")
                    file_progress = tqdm(files, desc=f"Processing {os.path.basename(root)}", leave=False)
                else:
                    file_progress = files
                    
                for file in file_progress:
                    file_path = os.path.join(root, file)
                    try:
                        # Skip excluded files based on patterns
                        should_skip_file = False
                        for pattern in all_exclude_files:
                            if pattern.startswith('*') and file.endswith(pattern[1:]):
                                should_skip_file = True
                                break
                            elif file == pattern:
                                should_skip_file = True
                                break
                        
                        if should_skip_file:
                            files_skipped += 1
                            continue
                        
                        # Check if we have read access before attempting to read the file
                        if not os.access(file_path, os.R_OK):
                            files_skipped += 1
                            continue
                            
                        # Skip files larger than 4GB for now
                        file_size = os.path.getsize(file_path)
                        if file_size > 4 * 1024 * 1024 * 1024:
                            print(f"Skipping large file (>4GB): {file_path}")
                            files_skipped += 1
                            continue
                            
                        # Add file to archive
                        arcname = os.path.relpath(file_path, partition.mountpoint)
                        tar.add(file_path, arcname=arcname)
                        
                        # Add to metadata
                        self.backup_metadata[arcname] = {
                            'path': file_path,
                            'size': file_size,
                            'mtime': os.path.getmtime(file_path)
                        }
                        
                        files_processed += 1
                        total_size += file_size
                        
                    except PermissionError:
                        files_skipped += 1
                    except Exception as e:
                        logger.error(f"Error backing up {file_path}: {e}")
                        files_skipped += 1
        
        # Print final summary
        print(f"\nPartition backup completed: {partition.mountpoint}")
        print(f"  ✓ Files processed: {files_processed:,}")
        print(f"  ✓ Files skipped: {files_skipped:,}")
        print(f"  ✓ Directories skipped: {dirs_skipped:,}")
        print(f"  ✓ Total data backed up: {total_size / (1024*1024*1024):.2f} GB\n")
        
        logger.info(f"Completed backing up partition: {partition.mountpoint}")
        logger.info(f"Files processed: {files_processed}, skipped: {files_skipped}, total size: {total_size / (1024*1024):.2f} MB")
        
    def _backup_windows_partition(self, partition, backup_dir):
        """Backup a Windows partition"""
        # This method would be implemented for Windows systems
        pass

    def create_full_backup(self):
        """Create a full system backup"""
        logger.info("Starting full system backup")
        self.create_backup_directory()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.destination_path / f"full_backup_{timestamp}"
        backup_dir.mkdir(exist_ok=True)
        
        partitions = self.get_system_partitions()
        for partition in tqdm(partitions, desc="Backing up partitions"):
            if self.system == "Linux":
                self._backup_linux_partition(partition, backup_dir)
            elif self.system == "Windows":
                self._backup_windows_partition(partition, backup_dir)
            
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
            self._backup_linux_partition(partition, backup_dir)
        else:
            self._backup_windows_partition(partition, backup_dir)

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
    parser.add_argument('--type', choices=['full', 'incremental', 'restore', 'iso'], required=True,
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
    """Main function to handle backup operations"""
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Set up logging
        log_dir = DEFAULT_PATHS['log_dir']
        log_file = os.path.join(log_dir, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        logger.add(log_file, rotation="1 day", retention="7 days")
        
        # Create backup manager
        backup_manager = BackupManager(args.destination)
        
        # Initialize remote backup connection if configured
        remote_backup = None
        if 'server_ip' in REMOTE_CONFIG and REMOTE_CONFIG['server_ip']:
            logger.info(f"Remote backup configured to {REMOTE_CONFIG['server_ip']}")
            print(f"Remote backup configured to {REMOTE_CONFIG['server_ip']}")
            remote_backup = RemoteBackup()
            if not remote_backup.connect():
                logger.error("Failed to connect to remote backup server")
                print("Failed to connect to remote backup server")
                remote_backup = None
        
        backup_path = None
        # Handle different backup types
        if args.type == 'full':
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = str(backup_manager.destination_path / f"full_backup_{timestamp}")
            backup_manager.create_full_backup()
        elif args.type == 'incremental':
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = str(backup_manager.destination_path / f"incremental_backup_{timestamp}")
            backup_manager.create_incremental_backup()
        elif args.type == 'restore':
            backup_manager.restore_from_backup(args.backup)
        elif args.type == 'iso':
            backup_manager.create_bootable_iso(args.output_iso)
        else:
            logger.error(f"Unknown backup type: {args.type}")
            return 1
        
        # Transfer backup to remote server if configured
        if remote_backup and backup_path:
            try:
                print(f"\nUploading backup to remote server at {REMOTE_CONFIG['server_ip']}...")
                logger.info(f"Starting upload of {backup_path} to remote server")
                
                remote_path = os.path.join(REMOTE_CONFIG['server_path'], os.path.basename(backup_path))
                
                # Ensure remote directory exists
                remote_backup.ensure_remote_directory(REMOTE_CONFIG['server_path'])
                
                # Upload the entire backup directory
                remote_backup.upload_directory(backup_path, remote_path)
                
                print(f"✓ Backup successfully uploaded to remote server")
                logger.info(f"Backup successfully uploaded to remote server at {remote_path}")
            except Exception as e:
                print(f"× Failed to upload backup to remote server: {str(e)}")
                logger.error(f"Failed to upload backup to remote server: {str(e)}")
            finally:
                remote_backup.disconnect()
                
        return 0
        
    except Exception as e:
        logger.error(f"Backup failed: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 