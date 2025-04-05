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
        self.system = "Linux" if sys.platform != "win32" else "Windows"
        self.remote_backup_enabled = bool(REMOTE_CONFIG.get('server_ip'))
        self.remote_backup_successful = False
        
        # Initialize remote backup if enabled
        if self.remote_backup_enabled:
            try:
                self.remote_backup = RemoteBackup()
                if self.remote_backup.connect():
                    print("Successfully connected to remote backup server")
                else:
                    print("Could not connect to remote server - will create local backup only")
                    self.remote_backup = None
            except Exception as e:
                print(f"Remote backup initialization failed: {e}")
                self.remote_backup = None

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

    def _backup_linux_partition(self, partition, backup_dir, verbose=False):
        """Backup a Linux partition"""
        if verbose:
            print(f"Backing up partition: {partition.mountpoint}")
        
        # Create partition directory
        partition_dir = backup_dir / partition.mountpoint.replace('/', '_').replace(chr(92), '_')
        partition_dir.mkdir(exist_ok=True)
        
        # Create archive
        archive_path = partition_dir / f"{partition.mountpoint.replace('/', '_').replace(chr(92), '_')}.tar.gz"
        
        # Count stats
        files_processed = 0
        files_skipped = 0
        dirs_skipped = 0
        total_size = 0
        start_time = time.time()
        
        # Get total size for progress calculation
        total_files = sum([len(files) for _, _, files in os.walk(partition.mountpoint)])
        processed_files = 0
        
        # Status update interval (seconds)
        status_interval = 5
        last_status_time = time.time()
        
        with tarfile.open(archive_path, 'w:gz') as tar:
            # Walk through the partition directory
            for root, dirs, files in os.walk(partition.mountpoint):
                # Show progress
                if time.time() - last_status_time > status_interval:
                    elapsed_time = time.time() - start_time
                    progress = (processed_files / total_files) * 100 if total_files > 0 else 0
                    if total_files > 0:
                        eta = (elapsed_time / processed_files) * (total_files - processed_files)
                        eta_str = f"{eta/60:.1f} minutes" if eta > 60 else f"{eta:.0f} seconds"
                    else:
                        eta_str = "calculating..."
                    
                    if verbose:
                        print(f"Processing: {root} | Files: {files_processed:,} processed, {files_skipped:,} skipped | Size: {format_size(total_size)}")
                    else:
                        print(f"\rProgress: {progress:.1f}% | ETA: {eta_str}", end='', flush=True)
                    last_status_time = time.time()
                
                # Show progress for directories with many files
                if verbose and len(files) > 100:
                    print(f"Found {len(files):,} files in {root}")
                    file_progress = tqdm(files, desc=f"Processing {os.path.basename(root)}", leave=False)
                else:
                    file_progress = files
                
                for file in file_progress:
                    file_path = os.path.join(root, file)
                    try:
                        # Skip excluded files
                        if should_exclude(Path(file_path)):
                            files_skipped += 1
                            processed_files += 1
                            continue
                        
                        # Add file to archive
                        tar.add(file_path, arcname=os.path.relpath(file_path, partition.mountpoint))
                        
                        # Update stats
                        files_processed += 1
                        processed_files += 1
                        total_size += os.path.getsize(file_path)
                    except PermissionError:
                        files_skipped += 1
                        processed_files += 1
                    except Exception as e:
                        logger.error(f"Error processing {file_path}: {e}")
                        files_skipped += 1
                        processed_files += 1
        
        # Print final summary
        if verbose:
            print(f"\nPartition backup completed: {partition.mountpoint}")
            print(f"  ✓ Files processed: {files_processed:,}")
            print(f"  ✓ Files skipped: {files_skipped:,}")
            print(f"  ✓ Directories skipped: {dirs_skipped:,}")
            print(f"  ✓ Total data backed up: {format_size(total_size)}")
        else:
            print(f"\nPartition {partition.mountpoint} completed: {format_size(total_size)}")
        
        logger.info(f"Completed backing up partition: {partition.mountpoint}")
        logger.info(f"Files processed: {files_processed}, skipped: {files_skipped}, total size: {format_size(total_size)}")

    def _backup_windows_partition(self, partition, backup_dir):
        """Backup a Windows partition"""
        # This method would be implemented for Windows systems
        pass

    def create_full_backup(self, verbose=False):
        """Create a full system backup"""
        logger.info("Starting full system backup")
        self.create_backup_directory()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.destination_path / f"full_backup_{timestamp}"
        backup_dir.mkdir(exist_ok=True)
        
        start_time = time.time()
        total_partitions = len(list(self.get_system_partitions()))
        processed_partitions = 0
        
        partitions = self.get_system_partitions()
        for partition in partitions:
            processed_partitions += 1
            if verbose:
                print(f"\nBacking up partition {processed_partitions}/{total_partitions}: {partition.mountpoint}")
            else:
                progress = (processed_partitions / total_partitions) * 100
                elapsed_time = time.time() - start_time
                eta = (elapsed_time / processed_partitions) * (total_partitions - processed_partitions)
                eta_str = f"{eta/60:.1f} minutes" if eta > 60 else f"{eta:.0f} seconds"
                print(f"\rProgress: {progress:.1f}% | ETA: {eta_str}", end='', flush=True)
            
            if self.system == "Linux":
                self._backup_linux_partition(partition, backup_dir, verbose)
            elif self.system == "Windows":
                self._backup_windows_partition(partition, backup_dir, verbose)
        
        self._save_metadata(backup_dir)
        
        # Try remote backup if enabled
        if self.remote_backup_enabled and self.remote_backup:
            try:
                if verbose:
                    print(f"\nUploading backup to remote server...")
                remote_path = os.path.join(REMOTE_CONFIG['server_path'], os.path.basename(str(backup_dir)))
                self.remote_backup.ensure_remote_directory(REMOTE_CONFIG['server_path'])
                self.remote_backup.upload_directory(str(backup_dir), remote_path)
                if verbose:
                    print(f"✓ Backup successfully uploaded to remote server")
                self.remote_backup_successful = True
            except Exception as e:
                if verbose:
                    print(f"× Failed to upload backup to remote server: {str(e)}")
                self.remote_backup_successful = False
            finally:
                self.remote_backup.disconnect()
        
        if verbose:
            print(f"\nFull backup completed successfully")
        else:
            print(f"\nBackup completed successfully")
        
        logger.info("Full backup completed successfully")
        return str(backup_dir)

    def create_incremental_backup(self, verbose=False):
        """Create an incremental backup"""
        logger.info("Starting incremental backup")
        self.create_backup_directory()
        
        # Find the latest backup
        latest_backup = self._get_latest_backup()
        if not latest_backup:
            if verbose:
                print("No previous backup found. Creating full backup instead.")
            logger.warning("No previous backup found. Creating full backup instead.")
            return self.create_full_backup(verbose)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.destination_path / f"incremental_backup_{timestamp}"
        backup_dir.mkdir(exist_ok=True)
        
        start_time = time.time()
        total_partitions = len(list(self.get_system_partitions()))
        processed_partitions = 0
        
        partitions = self.get_system_partitions()
        for partition in partitions:
            processed_partitions += 1
            if verbose:
                print(f"\nBacking up partition {processed_partitions}/{total_partitions}: {partition.mountpoint}")
            else:
                progress = (processed_partitions / total_partitions) * 100
                elapsed_time = time.time() - start_time
                eta = (elapsed_time / processed_partitions) * (total_partitions - processed_partitions)
                eta_str = f"{eta/60:.1f} minutes" if eta > 60 else f"{eta:.0f} seconds"
                print(f"\rProgress: {progress:.1f}% | ETA: {eta_str}", end='', flush=True)
            
            if self.system == "Linux":
                self._backup_linux_partition(partition, backup_dir, verbose)
            elif self.system == "Windows":
                self._backup_windows_partition(partition, backup_dir, verbose)
        
        self._save_metadata(backup_dir)
        
        # Try remote backup if enabled
        if self.remote_backup_enabled and self.remote_backup:
            try:
                if verbose:
                    print(f"\nUploading backup to remote server...")
                remote_path = os.path.join(REMOTE_CONFIG['server_path'], os.path.basename(str(backup_dir)))
                self.remote_backup.ensure_remote_directory(REMOTE_CONFIG['server_path'])
                self.remote_backup.upload_directory(str(backup_dir), remote_path)
                if verbose:
                    print(f"✓ Backup successfully uploaded to remote server")
                self.remote_backup_successful = True
            except Exception as e:
                if verbose:
                    print(f"× Failed to upload backup to remote server: {str(e)}")
                self.remote_backup_successful = False
            finally:
                self.remote_backup.disconnect()
        
        if verbose:
            print(f"\nIncremental backup completed successfully")
        else:
            print(f"\nBackup completed successfully")
        
        logger.info("Incremental backup completed successfully")
        return str(backup_dir)

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
    parser = argparse.ArgumentParser(description='Lin-Win-Backup Tool')
    parser.add_argument('--type', choices=['full', 'incremental', 'directory', 'restore', 'iso'],
                      help='Type of backup to perform')
    parser.add_argument('--destination', help='Destination directory for backup',
                      default=DEFAULT_PATHS['backup_dir'])
    parser.add_argument('--source-dir', help='Source directory for directory backup')
    parser.add_argument('--backup', help='Backup to restore from')
    parser.add_argument('--output-iso', help='Output path for bootable ISO')
    parser.add_argument('--skip-remote', action='store_true',
                      help='Skip remote backup even if configured')
    parser.add_argument('--verbose', '-v', action='store_true',
                      help='Show detailed progress information')
    
    return parser.parse_args()

def format_size(size_bytes):
    """Format size in bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

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
    
    # First pass: calculate total size and file count for accurate progress
    print("Calculating total size and file count...")
    total_size_bytes = 0
    total_files = 0
    for root, _, files in os.walk(root_dir):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                if not should_exclude(Path(file_path)):
                    total_size_bytes += os.path.getsize(file_path)
                    total_files += 1
            except (PermissionError, OSError):
                pass
    
    processed_size = 0
    processed_files = 0
    
    # Create archive
    archive_path = os.path.join(backup_dir, 'backup.tar.gz')
    start_time = time.time()
    
    # Status update interval (seconds)
    status_interval = 1  # Update more frequently
    last_status_time = time.time()
    
    with tarfile.open(archive_path, 'w:gz') as tar:
        for root, dirs, files in os.walk(root_dir):
            # Show progress
            if time.time() - last_status_time > status_interval:
                elapsed_time = time.time() - start_time
                
                # Calculate progress based on both file count and size
                if total_files > 0 and total_size_bytes > 0:
                    # Weighted average of file count progress and size progress
                    file_progress = (processed_files / total_files) * 100
                    size_progress = (processed_size / total_size_bytes) * 100
                    progress = (file_progress + size_progress) / 2
                    
                    # Calculate ETA based on processed files and size
                    if processed_files > 0 and processed_size > 0:
                        # Average time per file and per byte
                        time_per_file = elapsed_time / processed_files
                        time_per_byte = elapsed_time / processed_size
                        
                        # Remaining files and bytes
                        remaining_files = total_files - processed_files
                        remaining_bytes = total_size_bytes - processed_size
                        
                        # Estimate time based on both metrics
                        eta_files = time_per_file * remaining_files
                        eta_bytes = time_per_byte * remaining_bytes
                        
                        # Use the larger estimate for a more conservative ETA
                        eta = max(eta_files, eta_bytes)
                        
                        # Format ETA
                        if eta > 60:
                            eta_str = f"{eta/60:.1f} minutes"
                        else:
                            eta_str = f"{eta:.0f} seconds"
                    else:
                        eta_str = "calculating..."
                else:
                    progress = 0
                    eta_str = "calculating..."
                
                print(f"\rProgress: {progress:.1f}% | ETA: {eta_str} | Files: {processed_files}/{total_files} | Size: {format_size(processed_size)}/{format_size(total_size_bytes)}", end='', flush=True)
                last_status_time = time.time()
            
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    # Skip excluded files
                    if should_exclude(Path(file_path)):
                        continue
                    
                    # Get file size before adding to archive
                    file_size = os.path.getsize(file_path)
                    
                    # Add file to archive
                    tar.add(file_path, arcname=os.path.relpath(file_path, root_dir))
                    
                    # Update stats
                    processed_files += 1
                    processed_size += file_size
                    
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
    
    print(f"\nFull backup completed: {backup_dir}")
    print(f"Total size: {format_size(processed_size)}")
    
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
    
    # First pass: calculate total size and file count for accurate progress
    print("Calculating total size and file count...")
    total_size_bytes = 0
    total_files = 0
    for root, _, files in os.walk(root_dir):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                if not should_exclude(Path(file_path)):
                    total_size_bytes += os.path.getsize(file_path)
                    total_files += 1
            except (PermissionError, OSError):
                pass
    
    processed_size = 0
    processed_files = 0
    changed_files = 0
    
    # Create archive
    archive_path = os.path.join(backup_dir, 'backup.tar.gz')
    start_time = time.time()
    
    # Status update interval (seconds)
    status_interval = 1  # Update more frequently
    last_status_time = time.time()
    
    with tarfile.open(archive_path, 'w:gz') as tar:
        for root, dirs, files in os.walk(root_dir):
            # Show progress
            if time.time() - last_status_time > status_interval:
                elapsed_time = time.time() - start_time
                
                # Calculate progress based on both file count and size
                if total_files > 0 and total_size_bytes > 0:
                    # Weighted average of file count progress and size progress
                    file_progress = (processed_files / total_files) * 100
                    size_progress = (processed_size / total_size_bytes) * 100
                    progress = (file_progress + size_progress) / 2
                    
                    # Calculate ETA based on processed files and size
                    if processed_files > 0 and processed_size > 0:
                        # Average time per file and per byte
                        time_per_file = elapsed_time / processed_files
                        time_per_byte = elapsed_time / processed_size
                        
                        # Remaining files and bytes
                        remaining_files = total_files - processed_files
                        remaining_bytes = total_size_bytes - processed_size
                        
                        # Estimate time based on both metrics
                        eta_files = time_per_file * remaining_files
                        eta_bytes = time_per_byte * remaining_bytes
                        
                        # Use the larger estimate for a more conservative ETA
                        eta = max(eta_files, eta_bytes)
                        
                        # Format ETA
                        if eta > 60:
                            eta_str = f"{eta/60:.1f} minutes"
                        else:
                            eta_str = f"{eta:.0f} seconds"
                    else:
                        eta_str = "calculating..."
                else:
                    progress = 0
                    eta_str = "calculating..."
                
                print(f"\rProgress: {progress:.1f}% | ETA: {eta_str} | Files: {processed_files}/{total_files} | Changed: {changed_files} | Size: {format_size(processed_size)}/{format_size(total_size_bytes)}", end='', flush=True)
                last_status_time = time.time()
            
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
                    
                    # Get file size before adding to archive
                    file_size = os.path.getsize(file_path)
                    
                    if file_changed:
                        # Add file to archive
                        tar.add(file_path, arcname=rel_path)
                        
                        # Add to metadata
                        metadata['files'].append({
                            'path': rel_path,
                            'hash': file_hash
                        })
                        changed_files += 1
                    
                    # Update stats
                    processed_files += 1
                    processed_size += file_size
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
    
    # Save metadata
    with open(os.path.join(backup_dir, 'metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\nIncremental backup completed: {backup_dir}")
    print(f"Total size: {format_size(processed_size)}")
    print(f"Changed files: {changed_files}")
    
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

def backup_single_directory(source_dir, destination, verbose=False):
    """Backup a single directory"""
    logger.info(f"Backing up directory: {source_dir}")
    if verbose:
        print(f"Starting backup of directory: {source_dir}")
    
    # Create backup directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(destination, f"dir_backup_{os.path.basename(source_dir)}_{timestamp}")
    os.makedirs(backup_dir, exist_ok=True)
    
    # Create archive path
    archive_path = os.path.join(backup_dir, f"{os.path.basename(source_dir)}.tar.gz")
    
    # Count stats
    files_processed = 0
    files_skipped = 0
    dirs_skipped = 0
    total_size = 0
    start_time = time.time()
    
    # First pass: calculate total size and file count for accurate progress
    print("Calculating total size and file count...")
    total_size_bytes = 0
    total_files = 0
    for root, _, files in os.walk(source_dir):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                if not should_exclude(Path(file_path)):
                    total_size_bytes += os.path.getsize(file_path)
                    total_files += 1
            except (PermissionError, OSError):
                pass
    
    processed_size = 0
    processed_files = 0
    
    # Status update interval (seconds)
    status_interval = 1  # Update more frequently
    last_status_time = time.time()
    
    # Metadata for this backup
    metadata = {
        'type': 'directory',
        'source': source_dir,
        'timestamp': datetime.now().isoformat(),
        'files': {}
    }
    
    with tarfile.open(archive_path, 'w:gz') as tar:
        # Walk through the source directory
        for root, dirs, files in os.walk(source_dir):
            # Show progress
            if time.time() - last_status_time > status_interval:
                elapsed_time = time.time() - start_time
                
                # Calculate progress based on both file count and size
                if total_files > 0 and total_size_bytes > 0:
                    # Weighted average of file count progress and size progress
                    file_progress = (processed_files / total_files) * 100
                    size_progress = (processed_size / total_size_bytes) * 100
                    progress = (file_progress + size_progress) / 2
                    
                    # Calculate ETA based on processed files and size
                    if processed_files > 0 and processed_size > 0:
                        # Average time per file and per byte
                        time_per_file = elapsed_time / processed_files
                        time_per_byte = elapsed_time / processed_size
                        
                        # Remaining files and bytes
                        remaining_files = total_files - processed_files
                        remaining_bytes = total_size_bytes - processed_size
                        
                        # Estimate time based on both metrics
                        eta_files = time_per_file * remaining_files
                        eta_bytes = time_per_byte * remaining_bytes
                        
                        # Use the larger estimate for a more conservative ETA
                        eta = max(eta_files, eta_bytes)
                        
                        # Format ETA
                        if eta > 60:
                            eta_str = f"{eta/60:.1f} minutes"
                        else:
                            eta_str = f"{eta:.0f} seconds"
                    else:
                        eta_str = "calculating..."
                else:
                    progress = 0
                    eta_str = "calculating..."
                
                if verbose:
                    print(f"Processing: {root} | Files: {files_processed:,} processed, {files_skipped:,} skipped | Size: {format_size(total_size)}")
                else:
                    print(f"\rProgress: {progress:.1f}% | ETA: {eta_str} | Files: {processed_files}/{total_files} | Size: {format_size(processed_size)}/{format_size(total_size_bytes)}", end='', flush=True)
                last_status_time = time.time()
            
            # Show progress for directories with many files
            if verbose and len(files) > 100:
                print(f"Found {len(files):,} files in {root}")
                file_progress = tqdm(files, desc=f"Processing {os.path.basename(root)}", leave=False)
            else:
                file_progress = files
            
            for file in file_progress:
                file_path = os.path.join(root, file)
                try:
                    # Skip excluded files
                    if should_exclude(Path(file_path)):
                        files_skipped += 1
                        continue
                    
                    # Get file size before adding to archive
                    file_size = os.path.getsize(file_path)
                    
                    # Add file to archive
                    tar.add(file_path, arcname=os.path.relpath(file_path, source_dir))
                    
                    # Update stats
                    files_processed += 1
                    processed_files += 1
                    processed_size += file_size
                    total_size += file_size
                    
                    # Add to metadata
                    metadata['files'][os.path.relpath(file_path, source_dir)] = {
                        'size': file_size,
                        'hash': get_file_hash(file_path)
                    }
                except PermissionError:
                    files_skipped += 1
                    processed_files += 1
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    files_skipped += 1
                    processed_files += 1
    
    # Save metadata
    with open(os.path.join(backup_dir, 'metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # Print final summary
    if verbose:
        print(f"\nBackup completed: {backup_dir}")
        print(f"  ✓ Files processed: {files_processed:,}")
        print(f"  ✓ Files skipped: {files_skipped:,}")
        print(f"  ✓ Directories skipped: {dirs_skipped:,}")
        print(f"  ✓ Total data backed up: {format_size(total_size)}")
    else:
        print(f"\nBackup completed: {backup_dir}")
        print(f"Total size: {format_size(total_size)}")
    
    logger.info(f"Files processed: {files_processed}, skipped: {files_skipped}, total size: {format_size(total_size)}")
    
    # Try remote backup if enabled
    remote_backup_successful = False
    if REMOTE_CONFIG.get('server_ip'):
        try:
            if verbose:
                print(f"\nUploading backup to remote server...")
            remote_backup = RemoteBackup()
            if remote_backup.connect():
                remote_path = os.path.join(REMOTE_CONFIG['server_path'], os.path.basename(backup_dir))
                remote_backup.ensure_remote_directory(REMOTE_CONFIG['server_path'])
                remote_backup.upload_directory(backup_dir, remote_path)
                if verbose:
                    print(f"✓ Backup successfully uploaded to remote server")
                remote_backup_successful = True
            else:
                if verbose:
                    print(f"× Failed to connect to remote server")
        except Exception as e:
            if verbose:
                print(f"× Failed to upload backup to remote server: {str(e)}")
        finally:
            if 'remote_backup' in locals():
                remote_backup.disconnect()
    
    # Return both the backup directory and remote backup status
    return backup_dir, remote_backup_successful

def prompt_delete_local_backup(backup_path):
    """Prompt user to delete local backup after successful remote backup"""
    if not os.path.exists(backup_path):
        return
        
    backup_size = sum(os.path.getsize(os.path.join(dirpath, filename))
                      for dirpath, _, filenames in os.walk(backup_path)
                      for filename in filenames)
    backup_size_gb = backup_size / (1024 * 1024 * 1024)
    
    print(f"\nRemote backup completed successfully!")
    print(f"Local backup size: {backup_size_gb:.2f} GB")
    response = input("Would you like to delete the local backup? (y/N): ").lower()
    
    if response == 'y':
        try:
            shutil.rmtree(backup_path)
            print(f"Local backup deleted successfully: {backup_path}")
        except Exception as e:
            print(f"Error deleting local backup: {e}")

def main():
    """Main function to handle backup operations"""
    args = parse_arguments()
    
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="INFO" if args.verbose else "WARNING")
    logger.add("backup.log", rotation="1 day", retention="7 days")
    
    # Create backup manager
    backup_manager = BackupManager(args.destination)
    
    try:
        # Handle different backup types
        if args.type == 'full':
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = str(backup_manager.destination_path / f"full_backup_{timestamp}")
            backup_manager.create_full_backup(args.verbose)
            
            # If remote backup is enabled and successful, prompt to delete local backup
            if not args.skip_remote and backup_manager.remote_backup_enabled:
                if backup_manager.remote_backup_successful:
                    prompt_delete_local_backup(backup_path)
                    
        elif args.type == 'incremental':
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = str(backup_manager.destination_path / f"incremental_backup_{timestamp}")
            backup_manager.create_incremental_backup(args.verbose)
            
            # If remote backup is enabled and successful, prompt to delete local backup
            if not args.skip_remote and backup_manager.remote_backup_enabled:
                if backup_manager.remote_backup_successful:
                    prompt_delete_local_backup(backup_path)
                    
        elif args.type == 'directory':
            # Create a directory backup
            source_dir = os.path.abspath(args.source_dir)
            backup_dir, remote_backup_successful = backup_single_directory(source_dir, args.destination, args.verbose)
            
            # If remote backup is enabled and successful, prompt to delete local backup
            if not args.skip_remote and REMOTE_CONFIG.get('server_ip'):
                if remote_backup_successful:
                    prompt_delete_local_backup(backup_dir)
                    
        elif args.type == 'restore':
            backup_manager.restore_from_backup(args.backup)
        elif args.type == 'iso':
            backup_manager.create_bootable_iso(args.output_iso)
        else:
            logger.error(f"Unknown backup type: {args.type}")
            return 1
            
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main()) 