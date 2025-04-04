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
            import json
            json.dump(metadata, f, indent=4)

    def _get_latest_backup(self):
        """Get the most recent backup directory"""
        backups = list(self.destination_path.glob('*_backup_*'))
        return max(backups, key=os.path.getctime) if backups else None

def main():
    parser = argparse.ArgumentParser(description='Lin-Win-Backup: Cross-platform backup solution')
    parser.add_argument('--destination', required=True, help='Backup destination path')
    parser.add_argument('--type', choices=['full', 'incremental'], required=True, help='Backup type')
    parser.add_argument('--create-iso', action='store_true', help='Create bootable ISO after backup')
    parser.add_argument('--output-iso', help='Output path for ISO file')
    
    args = parser.parse_args()
    
    backup_manager = BackupManager(args.destination)
    
    if args.type == 'full':
        backup_manager.create_full_backup()
    else:
        backup_manager.create_incremental_backup()
        
    if args.create_iso:
        if not args.output_iso:
            args.output_iso = os.path.join(args.destination, 'backup.iso')
        backup_manager.create_bootable_iso(args.destination, args.output_iso)

if __name__ == "__main__":
    main() 