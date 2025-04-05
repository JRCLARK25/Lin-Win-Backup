#!/usr/bin/env python3
import os
import sys
import argparse
import json
from client_config import ClientConfig
from client_api import ClientAPI

def main():
    """Client configuration tool"""
    parser = argparse.ArgumentParser(description='Lin-Win-Backup Client Configuration Tool')
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Server configuration
    server_parser = subparsers.add_parser('server', help='Configure server settings')
    server_parser.add_argument('--url', help='Server URL (e.g., http://192.168.1.100:3000)')
    server_parser.add_argument('--add-authorized', help='Add authorized server IP or subnet')
    server_parser.add_argument('--remove-authorized', help='Remove authorized server IP or subnet')
    server_parser.add_argument('--list-authorized', action='store_true', help='List authorized servers')
    
    # Client configuration
    client_parser = subparsers.add_parser('client', help='Configure client settings')
    client_parser.add_argument('--name', help='Set client friendly name')
    client_parser.add_argument('--add-dir', help='Add directory to backup')
    client_parser.add_argument('--remove-dir', help='Remove directory from backup')
    client_parser.add_argument('--list-dirs', action='store_true', help='List backup directories')
    client_parser.add_argument('--add-exclude', help='Add exclude pattern')
    client_parser.add_argument('--remove-exclude', help='Remove exclude pattern')
    client_parser.add_argument('--list-excludes', action='store_true', help='List exclude patterns')
    
    # Backup configuration
    backup_parser = subparsers.add_parser('backup', help='Configure backup settings')
    backup_parser.add_argument('--max-size', type=int, help='Set maximum backup size in MB')
    backup_parser.add_argument('--retention', type=int, help='Set retention days')
    backup_parser.add_argument('--encryption', choices=['on', 'off'], help='Enable or disable encryption')
    backup_parser.add_argument('--compression', choices=['on', 'off'], help='Enable or disable compression')
    
    # Logging configuration
    log_parser = subparsers.add_parser('log', help='Configure logging settings')
    log_parser.add_argument('--level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help='Set log level')
    log_parser.add_argument('--file', help='Set log file path')
    
    # Show configuration
    show_parser = subparsers.add_parser('show', help='Show current configuration')
    
    # Register with server
    register_parser = subparsers.add_parser('register', help='Register with server')
    
    args = parser.parse_args()
    
    # Initialize client configuration
    config = ClientConfig()
    api = ClientAPI()
    
    # Handle commands
    if args.command == 'server':
        if args.url:
            api.set_server_url(args.url)
            print(f"Server URL set to {args.url}")
        
        if args.add_authorized:
            api.add_authorized_server(server_ip=args.add_authorized)
            print(f"Added {args.add_authorized} to authorized servers")
        
        if args.remove_authorized:
            api.remove_authorized_server(server_ip=args.remove_authorized)
            print(f"Removed {args.remove_authorized} from authorized servers")
        
        if args.list_authorized:
            config_data = config.get_all_config()
            print("Authorized servers:")
            print("  IPs:", config_data['authorized_servers']['ips'])
            print("  Subnets:", config_data['authorized_servers']['subnets'])
            print("  Hostnames:", config_data['authorized_servers']['hostnames'])
    
    elif args.command == 'client':
        if args.name:
            api.set_client_name(args.name)
            print(f"Client name set to {args.name}")
        
        if args.add_dir:
            api.add_backup_dir(args.add_dir)
            print(f"Added {args.add_dir} to backup directories")
        
        if args.remove_dir:
            api.remove_backup_dir(args.remove_dir)
            print(f"Removed {args.remove_dir} from backup directories")
        
        if args.list_dirs:
            dirs = api.get_backup_dirs()
            print("Backup directories:")
            for dir in dirs:
                print(f"  {dir}")
        
        if args.add_exclude:
            api.add_exclude_pattern(args.add_exclude)
            print(f"Added {args.add_exclude} to exclude patterns")
        
        if args.remove_exclude:
            api.remove_exclude_pattern(args.remove_exclude)
            print(f"Removed {args.remove_exclude} from exclude patterns")
        
        if args.list_excludes:
            patterns = api.get_exclude_patterns()
            print("Exclude patterns:")
            for pattern in patterns:
                print(f"  {pattern}")
    
    elif args.command == 'backup':
        if args.max_size:
            api.set_max_backup_size(args.max_size * 1024 * 1024)  # Convert MB to bytes
            print(f"Maximum backup size set to {args.max_size} MB")
        
        if args.retention:
            api.set_retention_days(args.retention)
            print(f"Retention days set to {args.retention}")
        
        if args.encryption:
            enabled = args.encryption == 'on'
            api.set_encryption_enabled(enabled)
            print(f"Encryption {'enabled' if enabled else 'disabled'}")
        
        if args.compression:
            enabled = args.compression == 'on'
            api.set_compression_enabled(enabled)
            print(f"Compression {'enabled' if enabled else 'disabled'}")
    
    elif args.command == 'log':
        if args.level:
            api.set_log_level(args.level)
            print(f"Log level set to {args.level}")
        
        if args.file:
            api.set_log_file(args.file)
            print(f"Log file set to {args.file}")
    
    elif args.command == 'show':
        config_data = config.get_all_config()
        print(json.dumps(config_data, indent=2))
    
    elif args.command == 'register':
        if not api.server_url:
            print("Error: Server URL not set. Use 'client_config_tool.py server --url <url>' to set it.")
            sys.exit(1)
        
        print("Registering with server...")
        if api.register_with_server():
            print("Successfully registered with server")
        else:
            print("Failed to register with server")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 