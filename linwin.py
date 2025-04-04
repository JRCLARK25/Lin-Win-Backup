#!/usr/bin/env python3
import os
import sys
import json
import argparse
import datetime
import tabulate
from pathlib import Path
from loguru import logger
from config import REMOTE_CONFIG, DEFAULT_PATHS
from backup_server import BackupServerManager, format_size

class LocalBackupManager:
    def __init__(self, backup_dir=None):
        self.backup_dir = backup_dir or DEFAULT_PATHS['backup_dir']
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir, exist_ok=True)
            
    def list_backups(self, sort_by='date', reverse=True, filter_type=None, limit=None):
        """List all backups with sorting and filtering options"""
        try:
            # Get all backup directories
            backup_dirs = []
            for entry in os.scandir(self.backup_dir):
                if entry.is_dir() and entry.name.startswith(('full_backup_', 'incremental_backup_')):
                    backup_path = entry.path
                    try:
                        # Try to read metadata file
                        metadata_path = os.path.join(backup_path, 'metadata.json')
                        metadata = {}
                        try:
                            with open(metadata_path, 'r') as f:
                                metadata = json.load(f)
                        except:
                            # If metadata doesn't exist, create basic info
                            metadata = {
                                'type': 'full' if entry.name.startswith('full_backup_') else 'incremental',
                                'timestamp': entry.name.split('_')[-1],
                                'status': 'unknown'
                            }
                            
                        # Get directory size
                        size = 0
                        for dirpath, dirnames, filenames in os.walk(backup_path):
                            for f in filenames:
                                fp = os.path.join(dirpath, f)
                                size += os.path.getsize(fp)
                                
                        backup_dirs.append({
                            'name': entry.name,
                            'path': backup_path,
                            'type': metadata.get('type', 'unknown'),
                            'timestamp': metadata.get('timestamp', entry.name.split('_')[-1]),
                            'status': metadata.get('status', 'unknown'),
                            'size': size,
                            'date': datetime.datetime.strptime(metadata.get('timestamp', entry.name.split('_')[-1]), '%Y%m%d_%H%M%S')
                        })
                    except Exception as e:
                        logger.error(f"Error processing backup {entry.name}: {e}")
                        
            # Apply filters
            if filter_type:
                backup_dirs = [b for b in backup_dirs if b['type'] == filter_type]
                
            # Sort backups
            if sort_by == 'date':
                backup_dirs.sort(key=lambda x: x['date'], reverse=reverse)
            elif sort_by == 'size':
                backup_dirs.sort(key=lambda x: x['size'], reverse=reverse)
            elif sort_by == 'name':
                backup_dirs.sort(key=lambda x: x['name'], reverse=reverse)
                
            # Apply limit
            if limit:
                backup_dirs = backup_dirs[:limit]
                
            return backup_dirs
            
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []
            
    def get_backup_details(self, backup_name):
        """Get detailed information about a specific backup"""
        try:
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            # Check if backup exists
            if not os.path.exists(backup_path):
                logger.error(f"Backup {backup_name} not found")
                return None
                
            # Get metadata
            metadata = {}
            try:
                with open(os.path.join(backup_path, 'metadata.json'), 'r') as f:
                    metadata = json.load(f)
            except:
                metadata = {
                    'type': 'full' if backup_name.startswith('full_backup_') else 'incremental',
                    'timestamp': backup_name.split('_')[-1],
                    'status': 'unknown'
                }
                
            # Get directory size
            size = 0
            for dirpath, dirnames, filenames in os.walk(backup_path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    size += os.path.getsize(fp)
                    
            # Get file count
            file_count = 0
            for dirpath, dirnames, filenames in os.walk(backup_path):
                file_count += len(filenames)
                
            # Get directory structure
            dir_structure = []
            for dirpath, dirnames, filenames in os.walk(backup_path):
                dir_structure.append(dirpath)
                
            return {
                'name': backup_name,
                'path': backup_path,
                'type': metadata.get('type', 'unknown'),
                'timestamp': metadata.get('timestamp', backup_name.split('_')[-1]),
                'status': metadata.get('status', 'unknown'),
                'size': size,
                'file_count': file_count,
                'dir_structure': sorted(dir_structure),
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to get backup details: {e}")
            return None
            
    def get_in_progress_backups(self):
        """Get information about currently running backups"""
        try:
            import psutil
            
            in_progress = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cmdline', 'create_time']):
                try:
                    # Check if this is a backup process
                    cmdline = proc.info['cmdline']
                    if not cmdline:
                        continue
                        
                    cmd_str = ' '.join(cmdline)
                    if 'lin_win_backup.py' in cmd_str:
                        # Extract backup type
                        backup_type = None
                        if '--type full' in cmd_str:
                            backup_type = 'full'
                        elif '--type incremental' in cmd_str:
                            backup_type = 'incremental'
                            
                        if backup_type:
                            in_progress.append({
                                'pid': proc.info['pid'],
                                'user': proc.info['username'],
                                'type': backup_type,
                                'start_time': datetime.datetime.fromtimestamp(proc.info['create_time']).strftime('%Y-%m-%d %H:%M:%S'),
                                'cmd': cmd_str
                            })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
                    
            return in_progress
            
        except Exception as e:
            logger.error(f"Failed to get in-progress backups: {e}")
            return []
            
    def delete_backup(self, backup_name):
        """Delete a backup"""
        try:
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            # Check if backup exists
            if not os.path.exists(backup_path):
                logger.error(f"Backup {backup_name} not found")
                return False
                
            # Delete backup
            import shutil
            shutil.rmtree(backup_path)
            logger.info(f"Deleted backup {backup_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete backup: {e}")
            return False
            
    def get_storage_usage(self):
        """Get storage usage information"""
        try:
            import psutil
            
            # Get disk usage
            disk_usage = psutil.disk_usage(self.backup_dir)
            
            # Get backup directory usage
            backup_size = 0
            for dirpath, dirnames, filenames in os.walk(self.backup_dir):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    backup_size += os.path.getsize(fp)
                    
            # Get backup count by type
            full_count = len([d for d in os.listdir(self.backup_dir) 
                             if os.path.isdir(os.path.join(self.backup_dir, d)) 
                             and d.startswith('full_backup_')])
                             
            incremental_count = len([d for d in os.listdir(self.backup_dir) 
                                    if os.path.isdir(os.path.join(self.backup_dir, d)) 
                                    and d.startswith('incremental_backup_')])
                                    
            return {
                'total_space': format_size(disk_usage.total),
                'used_space': format_size(disk_usage.used),
                'free_space': format_size(disk_usage.free),
                'usage_percent': f"{disk_usage.percent}%",
                'backup_usage': format_size(backup_size),
                'full_backup_count': full_count,
                'incremental_backup_count': incremental_count
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage usage: {e}")
            return None

def main():
    parser = argparse.ArgumentParser(description='Lin-Win-Backup Management Tool')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # List backups command
    list_parser = subparsers.add_parser('list', help='List backups')
    list_parser.add_argument('--sort', choices=['date', 'size', 'name'], default='date', help='Sort backups by')
    list_parser.add_argument('--reverse', action='store_true', help='Sort in reverse order')
    list_parser.add_argument('--type', choices=['full', 'incremental'], help='Filter by backup type')
    list_parser.add_argument('--limit', type=int, help='Limit number of backups shown')
    list_parser.add_argument('--format', choices=['table', 'json'], default='table', help='Output format')
    list_parser.add_argument('--backup-dir', help='Local backup directory')
    list_parser.add_argument('--remote', action='store_true', help='Use remote backup server')
    
    # Show backup details command
    details_parser = subparsers.add_parser('details', help='Show backup details')
    details_parser.add_argument('backup_name', help='Name of the backup to show details for')
    details_parser.add_argument('--backup-dir', help='Local backup directory')
    details_parser.add_argument('--remote', action='store_true', help='Use remote backup server')
    
    # Show in-progress backups command
    progress_parser = subparsers.add_parser('progress', help='Show in-progress backups')
    progress_parser.add_argument('--backup-dir', help='Local backup directory')
    progress_parser.add_argument('--remote', action='store_true', help='Use remote backup server')
    
    # Delete backup command
    delete_parser = subparsers.add_parser('delete', help='Delete a backup')
    delete_parser.add_argument('backup_name', help='Name of the backup to delete')
    delete_parser.add_argument('--force', action='store_true', help='Force deletion without confirmation')
    delete_parser.add_argument('--backup-dir', help='Local backup directory')
    delete_parser.add_argument('--remote', action='store_true', help='Use remote backup server')
    
    # Show storage usage command
    usage_parser = subparsers.add_parser('usage', help='Show storage usage')
    usage_parser.add_argument('--backup-dir', help='Local backup directory')
    usage_parser.add_argument('--remote', action='store_true', help='Use remote backup server')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
        
    # Determine if we're using local or remote backup
    if args.remote:
        manager = BackupServerManager()
        if not manager.connect():
            logger.error("Failed to connect to backup server")
            return
    else:
        manager = LocalBackupManager(args.backup_dir)
        
    try:
        if args.command == 'list':
            backups = manager.list_backups(
                sort_by=args.sort,
                reverse=args.reverse,
                filter_type=args.type,
                limit=args.limit
            )
            
            if args.format == 'json':
                print(json.dumps(backups, default=str, indent=2))
            else:
                table_data = []
                for backup in backups:
                    table_data.append([
                        backup['name'],
                        backup['type'],
                        backup['date'].strftime('%Y-%m-%d %H:%M:%S'),
                        format_size(backup['size']),
                        backup['status']
                    ])
                    
                print(tabulate.tabulate(
                    table_data,
                    headers=['Name', 'Type', 'Date', 'Size', 'Status'],
                    tablefmt='grid'
                ))
                
        elif args.command == 'details':
            details = manager.get_backup_details(args.backup_name)
            if details:
                if args.format == 'json':
                    print(json.dumps(details, default=str, indent=2))
                else:
                    print(f"Backup: {details['name']}")
                    print(f"Type: {details['type']}")
                    print(f"Date: {datetime.datetime.strptime(details['timestamp'], '%Y%m%d_%H%M%S').strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"Status: {details['status']}")
                    print(f"Size: {format_size(details['size'])}")
                    print(f"File Count: {details['file_count']}")
                    print("\nDirectory Structure:")
                    for dir_path in details['dir_structure'][:10]:  # Show first 10 directories
                        print(f"  {dir_path}")
                    if len(details['dir_structure']) > 10:
                        print(f"  ... and {len(details['dir_structure']) - 10} more directories")
                        
        elif args.command == 'progress':
            in_progress = manager.get_in_progress_backups()
            if in_progress:
                table_data = []
                for backup in in_progress:
                    table_data.append([
                        backup['pid'],
                        backup['user'],
                        backup['type'],
                        backup['start_time']
                    ])
                    
                print(tabulate.tabulate(
                    table_data,
                    headers=['PID', 'User', 'Type', 'Start Time'],
                    tablefmt='grid'
                ))
            else:
                print("No backups in progress")
                
        elif args.command == 'delete':
            if not args.force:
                confirm = input(f"Are you sure you want to delete backup {args.backup_name}? (y/n): ")
                if confirm.lower() != 'y':
                    print("Deletion cancelled")
                    return
                    
            if manager.delete_backup(args.backup_name):
                print(f"Backup {args.backup_name} deleted successfully")
            else:
                print(f"Failed to delete backup {args.backup_name}")
                
        elif args.command == 'usage':
            usage = manager.get_storage_usage()
            if usage:
                print(f"Total Space: {usage['total_space']}")
                print(f"Used Space: {usage['used_space']} ({usage['usage_percent']})")
                print(f"Free Space: {usage['free_space']}")
                print(f"Backup Usage: {usage['backup_usage']}")
                print(f"Full Backups: {usage['full_backup_count']}")
                print(f"Incremental Backups: {usage['incremental_backup_count']}")
            else:
                print("Failed to get storage usage information")
                
    finally:
        if args.remote and hasattr(manager, 'disconnect'):
            manager.disconnect()

if __name__ == "__main__":
    main() 