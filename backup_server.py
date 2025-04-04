#!/usr/bin/env python3
import os
import sys
import json
import argparse
import datetime
import paramiko
import tabulate
from pathlib import Path
from loguru import logger
from config import REMOTE_CONFIG

class BackupServerManager:
    def __init__(self):
        self.server_ip = REMOTE_CONFIG['server_ip']
        self.server_port = REMOTE_CONFIG['server_port']
        self.server_user = REMOTE_CONFIG['server_user']
        self.server_path = REMOTE_CONFIG['server_path']
        self.ssh_key = REMOTE_CONFIG['ssh_key']
        self.ssh_client = None
        
    def connect(self):
        """Establish SSH connection to remote server"""
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if self.ssh_key:
                key = paramiko.RSAKey.from_private_key_file(self.ssh_key)
                self.ssh_client.connect(
                    self.server_ip,
                    port=self.server_port,
                    username=self.server_user,
                    pkey=key
                )
            else:
                self.ssh_client.connect(
                    self.server_ip,
                    port=self.server_port,
                    username=self.server_user
                )
                
            logger.info(f"Connected to remote server {self.server_ip}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to remote server: {e}")
            return False
            
    def disconnect(self):
        """Close SSH connection"""
        if self.ssh_client:
            self.ssh_client.close()
            logger.info("Disconnected from remote server")
            
    def list_backups(self, sort_by='date', reverse=True, filter_type=None, limit=None):
        """List all backups with sorting and filtering options"""
        try:
            sftp = self.ssh_client.open_sftp()
            
            # Get all backup directories
            backup_dirs = []
            for entry in sftp.listdir_attr(self.server_path):
                if entry.filename.startswith(('full_backup_', 'incremental_backup_')):
                    backup_path = os.path.join(self.server_path, entry.filename)
                    try:
                        # Try to read metadata file
                        metadata_path = os.path.join(backup_path, 'metadata.json')
                        metadata = {}
                        try:
                            with sftp.open(metadata_path, 'r') as f:
                                metadata = json.load(f)
                        except:
                            # If metadata doesn't exist, create basic info
                            metadata = {
                                'type': 'full' if entry.filename.startswith('full_backup_') else 'incremental',
                                'timestamp': entry.filename.split('_')[-1],
                                'status': 'unknown'
                            }
                            
                        # Get directory size
                        size = 0
                        try:
                            stdin, stdout, stderr = self.ssh_client.exec_command(f'du -sb {backup_path}')
                            size = int(stdout.read().decode().strip().split('\t')[0])
                        except:
                            pass
                            
                        backup_dirs.append({
                            'name': entry.filename,
                            'path': backup_path,
                            'type': metadata.get('type', 'unknown'),
                            'timestamp': metadata.get('timestamp', entry.filename.split('_')[-1]),
                            'status': metadata.get('status', 'unknown'),
                            'size': size,
                            'date': datetime.datetime.strptime(metadata.get('timestamp', entry.filename.split('_')[-1]), '%Y%m%d_%H%M%S')
                        })
                    except Exception as e:
                        logger.error(f"Error processing backup {entry.filename}: {e}")
                        
            sftp.close()
            
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
            backup_path = os.path.join(self.server_path, backup_name)
            
            # Check if backup exists
            sftp = self.ssh_client.open_sftp()
            try:
                sftp.stat(backup_path)
            except FileNotFoundError:
                logger.error(f"Backup {backup_name} not found")
                return None
                
            # Get metadata
            metadata = {}
            try:
                with sftp.open(os.path.join(backup_path, 'metadata.json'), 'r') as f:
                    metadata = json.load(f)
            except:
                metadata = {
                    'type': 'full' if backup_name.startswith('full_backup_') else 'incremental',
                    'timestamp': backup_name.split('_')[-1],
                    'status': 'unknown'
                }
                
            # Get directory size
            size = 0
            try:
                stdin, stdout, stderr = self.ssh_client.exec_command(f'du -sb {backup_path}')
                size = int(stdout.read().decode().strip().split('\t')[0])
            except:
                pass
                
            # Get file count
            file_count = 0
            try:
                stdin, stdout, stderr = self.ssh_client.exec_command(f'find {backup_path} -type f | wc -l')
                file_count = int(stdout.read().decode().strip())
            except:
                pass
                
            # Get directory structure
            dir_structure = []
            try:
                stdin, stdout, stderr = self.ssh_client.exec_command(f'find {backup_path} -type d | sort')
                dir_structure = stdout.read().decode().strip().split('\n')
            except:
                pass
                
            sftp.close()
            
            return {
                'name': backup_name,
                'path': backup_path,
                'type': metadata.get('type', 'unknown'),
                'timestamp': metadata.get('timestamp', backup_name.split('_')[-1]),
                'status': metadata.get('status', 'unknown'),
                'size': size,
                'file_count': file_count,
                'dir_structure': dir_structure,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to get backup details: {e}")
            return None
            
    def get_in_progress_backups(self):
        """Get information about currently running backups"""
        try:
            # Check for running backup processes
            stdin, stdout, stderr = self.ssh_client.exec_command('ps aux | grep "lin_win_backup.py" | grep -v grep')
            processes = stdout.read().decode().strip().split('\n')
            
            in_progress = []
            for process in processes:
                if not process:
                    continue
                    
                parts = process.split()
                if len(parts) < 11:
                    continue
                    
                pid = parts[1]
                user = parts[0]
                cmd = ' '.join(parts[10:])
                
                # Extract backup type and destination
                backup_type = None
                if '--type full' in cmd:
                    backup_type = 'full'
                elif '--type incremental' in cmd:
                    backup_type = 'incremental'
                    
                if backup_type:
                    in_progress.append({
                        'pid': pid,
                        'user': user,
                        'type': backup_type,
                        'start_time': datetime.datetime.fromtimestamp(int(parts[8])).strftime('%Y-%m-%d %H:%M:%S'),
                        'cmd': cmd
                    })
                    
            return in_progress
            
        except Exception as e:
            logger.error(f"Failed to get in-progress backups: {e}")
            return []
            
    def delete_backup(self, backup_name):
        """Delete a backup"""
        try:
            backup_path = os.path.join(self.server_path, backup_name)
            
            # Check if backup exists
            sftp = self.ssh_client.open_sftp()
            try:
                sftp.stat(backup_path)
            except FileNotFoundError:
                logger.error(f"Backup {backup_name} not found")
                return False
                
            sftp.close()
            
            # Delete backup
            stdin, stdout, stderr = self.ssh_client.exec_command(f'rm -rf {backup_path}')
            if stderr.read():
                logger.error(f"Failed to delete backup {backup_name}")
                return False
                
            logger.info(f"Deleted backup {backup_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete backup: {e}")
            return False
            
    def get_storage_usage(self):
        """Get storage usage information"""
        try:
            # Get total disk usage
            stdin, stdout, stderr = self.ssh_client.exec_command(f'df -h {self.server_path}')
            disk_info = stdout.read().decode().strip().split('\n')[1].split()
            
            # Get backup directory usage
            stdin, stdout, stderr = self.ssh_client.exec_command(f'du -sh {self.server_path}')
            backup_usage = stdout.read().decode().strip().split('\t')[0]
            
            # Get backup count by type
            stdin, stdout, stderr = self.ssh_client.exec_command(f'ls -d {self.server_path}/full_backup_* 2>/dev/null | wc -l')
            full_count = int(stdout.read().decode().strip() or 0)
            
            stdin, stdout, stderr = self.ssh_client.exec_command(f'ls -d {self.server_path}/incremental_backup_* 2>/dev/null | wc -l')
            incremental_count = int(stdout.read().decode().strip() or 0)
            
            return {
                'total_space': disk_info[1],
                'used_space': disk_info[2],
                'free_space': disk_info[3],
                'usage_percent': disk_info[4],
                'backup_usage': backup_usage,
                'full_backup_count': full_count,
                'incremental_backup_count': incremental_count
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage usage: {e}")
            return None

def format_size(size_bytes):
    """Format size in bytes to human-readable format"""
    if size_bytes == 0:
        return "0 B"
        
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = 0
    while size_bytes >= 1024 and i < len(size_name) - 1:
        size_bytes /= 1024
        i += 1
        
    return f"{size_bytes:.2f} {size_name[i]}"

def main():
    parser = argparse.ArgumentParser(description='Lin-Win-Backup Server Management Tool')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # List backups command
    list_parser = subparsers.add_parser('list', help='List backups')
    list_parser.add_argument('--sort', choices=['date', 'size', 'name'], default='date', help='Sort backups by')
    list_parser.add_argument('--reverse', action='store_true', help='Sort in reverse order')
    list_parser.add_argument('--type', choices=['full', 'incremental'], help='Filter by backup type')
    list_parser.add_argument('--limit', type=int, help='Limit number of backups shown')
    list_parser.add_argument('--format', choices=['table', 'json'], default='table', help='Output format')
    
    # Show backup details command
    details_parser = subparsers.add_parser('details', help='Show backup details')
    details_parser.add_argument('backup_name', help='Name of the backup to show details for')
    
    # Show in-progress backups command
    progress_parser = subparsers.add_parser('progress', help='Show in-progress backups')
    
    # Delete backup command
    delete_parser = subparsers.add_parser('delete', help='Delete a backup')
    delete_parser.add_argument('backup_name', help='Name of the backup to delete')
    delete_parser.add_argument('--force', action='store_true', help='Force deletion without confirmation')
    
    # Show storage usage command
    usage_parser = subparsers.add_parser('usage', help='Show storage usage')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
        
    manager = BackupServerManager()
    if not manager.connect():
        logger.error("Failed to connect to backup server")
        return
        
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
        manager.disconnect()

if __name__ == "__main__":
    main() 