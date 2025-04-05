#!/usr/bin/env python3
import os
import json
import ipaddress
from pathlib import Path

class ClientConfig:
    """Client configuration manager"""
    
    def __init__(self, config_dir=None):
        """Initialize the client configuration"""
        if config_dir is None:
            config_dir = os.path.expanduser('~/Lin-Win-Backup/config')
        
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, 'client_config.json')
        self.config = self._load_config()
    
    def _load_config(self):
        """Load the client configuration"""
        os.makedirs(self.config_dir, exist_ok=True)
        
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        
        # Default configuration
        default_config = {
            'authorized_servers': {
                'subnets': [],  # List of authorized subnets (e.g., "192.168.1.0/24")
                'ips': [],      # List of authorized IP addresses
                'hostnames': [] # List of authorized hostnames
            },
            'server_url': None,  # Default server URL
            'client_name': None, # Friendly name for this client
            'backup_dirs': [],   # Directories to backup
            'exclude_patterns': [], # Patterns to exclude from backups
            'max_backup_size': None, # Maximum backup size in bytes
            'retention_days': 30,    # Number of days to keep backups
            'encryption_enabled': True, # Whether to encrypt backups
            'compression_enabled': True, # Whether to compress backups
            'log_level': 'INFO',     # Logging level
            'log_file': os.path.join(self.config_dir, 'client.log')
        }
        
        # Save default configuration
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        return default_config
    
    def save(self):
        """Save the current configuration"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def is_server_authorized(self, server_ip, server_hostname=None):
        """Check if a server is authorized to communicate with this client"""
        # Check IP against authorized IPs
        if server_ip in self.config['authorized_servers']['ips']:
            return True
        
        # Check IP against authorized subnets
        for subnet in self.config['authorized_servers']['subnets']:
            try:
                network = ipaddress.ip_network(subnet)
                if ipaddress.ip_address(server_ip) in network:
                    return True
            except ValueError:
                # Invalid subnet format, skip it
                continue
        
        # Check hostname if provided
        if server_hostname and server_hostname in self.config['authorized_servers']['hostnames']:
            return True
        
        return False
    
    def add_authorized_server(self, server_ip=None, subnet=None, hostname=None):
        """Add an authorized server"""
        if server_ip:
            if server_ip not in self.config['authorized_servers']['ips']:
                self.config['authorized_servers']['ips'].append(server_ip)
        
        if subnet:
            if subnet not in self.config['authorized_servers']['subnets']:
                self.config['authorized_servers']['subnets'].append(subnet)
        
        if hostname:
            if hostname not in self.config['authorized_servers']['hostnames']:
                self.config['authorized_servers']['hostnames'].append(hostname)
        
        self.save()
    
    def remove_authorized_server(self, server_ip=None, subnet=None, hostname=None):
        """Remove an authorized server"""
        if server_ip and server_ip in self.config['authorized_servers']['ips']:
            self.config['authorized_servers']['ips'].remove(server_ip)
        
        if subnet and subnet in self.config['authorized_servers']['subnets']:
            self.config['authorized_servers']['subnets'].remove(subnet)
        
        if hostname and hostname in self.config['authorized_servers']['hostnames']:
            self.config['authorized_servers']['hostnames'].remove(hostname)
        
        self.save()
    
    def set_server_url(self, url):
        """Set the server URL"""
        self.config['server_url'] = url
        self.save()
    
    def get_server_url(self):
        """Get the server URL"""
        return self.config['server_url']
    
    def set_client_name(self, name):
        """Set the client name"""
        self.config['client_name'] = name
        self.save()
    
    def get_client_name(self):
        """Get the client name"""
        return self.config['client_name']
    
    def add_backup_dir(self, directory):
        """Add a directory to backup"""
        if directory not in self.config['backup_dirs']:
            self.config['backup_dirs'].append(directory)
            self.save()
    
    def remove_backup_dir(self, directory):
        """Remove a directory from backup"""
        if directory in self.config['backup_dirs']:
            self.config['backup_dirs'].remove(directory)
            self.save()
    
    def add_exclude_pattern(self, pattern):
        """Add an exclude pattern"""
        if pattern not in self.config['exclude_patterns']:
            self.config['exclude_patterns'].append(pattern)
            self.save()
    
    def remove_exclude_pattern(self, pattern):
        """Remove an exclude pattern"""
        if pattern in self.config['exclude_patterns']:
            self.config['exclude_patterns'].remove(pattern)
            self.save()
    
    def set_max_backup_size(self, size_bytes):
        """Set the maximum backup size in bytes"""
        self.config['max_backup_size'] = size_bytes
        self.save()
    
    def get_max_backup_size(self):
        """Get the maximum backup size in bytes"""
        return self.config['max_backup_size']
    
    def set_retention_days(self, days):
        """Set the number of days to keep backups"""
        self.config['retention_days'] = days
        self.save()
    
    def get_retention_days(self):
        """Get the number of days to keep backups"""
        return self.config['retention_days']
    
    def set_encryption_enabled(self, enabled):
        """Set whether encryption is enabled"""
        self.config['encryption_enabled'] = enabled
        self.save()
    
    def is_encryption_enabled(self):
        """Get whether encryption is enabled"""
        return self.config['encryption_enabled']
    
    def set_compression_enabled(self, enabled):
        """Set whether compression is enabled"""
        self.config['compression_enabled'] = enabled
        self.save()
    
    def is_compression_enabled(self):
        """Get whether compression is enabled"""
        return self.config['compression_enabled']
    
    def set_log_level(self, level):
        """Set the logging level"""
        self.config['log_level'] = level
        self.save()
    
    def get_log_level(self):
        """Get the logging level"""
        return self.config['log_level']
    
    def set_log_file(self, log_file):
        """Set the log file path"""
        self.config['log_file'] = log_file
        self.save()
    
    def get_log_file(self):
        """Get the log file path"""
        return self.config['log_file']
    
    def get_all_config(self):
        """Get the entire configuration"""
        return self.config
    
    def update_config(self, new_config):
        """Update the configuration with new values"""
        for key, value in new_config.items():
            if key in self.config:
                self.config[key] = value
        
        self.save() 