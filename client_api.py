#!/usr/bin/env python3
import os
import json
import socket
import platform
import uuid
import requests
import hashlib
import base64
import time
from datetime import datetime
import psutil
from loguru import logger
from encryption_utils import EncryptionManager
from client_config import ClientConfig

class ClientAPI:
    """Client API for communicating with the backup server"""
    
    def __init__(self, server_url=None, client_id=None, keys_dir=None, config_dir=None):
        """Initialize the client API"""
        # Load client configuration
        self.config = ClientConfig(config_dir)
        
        # Set server URL from config if not provided
        if server_url is None:
            server_url = self.config.get_server_url()
        
        self.server_url = server_url
        self.client_id = client_id or self._generate_client_id()
        self.keys_dir = keys_dir or os.path.expanduser('~/Lin-Win-Backup/keys/client')
        
        # Initialize encryption manager
        self.encryption = self._load_or_generate_keys()
        
        # Set up logging
        log_level = self.config.get_log_level()
        log_file = self.config.get_log_file()
        logger.remove()  # Remove default handler
        logger.add(log_file, level=log_level)
        logger.add(lambda msg: print(msg), level=log_level)  # Also print to console
    
    def _generate_client_id(self):
        """Generate a unique client ID based on hostname and MAC address"""
        hostname = socket.gethostname()
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0, 2 * 6, 2)][::-1])
        return f"client_{hashlib.md5(f"{hostname}_{mac}".encode()).hexdigest()[:8]}"
    
    def _load_or_generate_keys(self):
        """Load existing keys or generate new ones"""
        os.makedirs(self.keys_dir, exist_ok=True)
        
        encryption = EncryptionManager()
        
        # Check if keys already exist
        private_key_path = os.path.join(self.keys_dir, 'private_key.pem')
        public_key_path = os.path.join(self.keys_dir, 'public_key.pem')
        
        if os.path.exists(private_key_path) and os.path.exists(public_key_path):
            # Load existing keys
            encryption.load_keys(private_key_path, public_key_path)
        else:
            # Generate new keys
            encryption.generate_keys()
            encryption.save_keys(private_key_path, public_key_path)
        
        return encryption
    
    def _check_server_authorization(self, server_url):
        """Check if the server is authorized"""
        try:
            # Extract hostname and IP from server URL
            from urllib.parse import urlparse
            parsed_url = urlparse(server_url)
            hostname = parsed_url.hostname
            
            # Try to resolve IP from hostname
            try:
                ip = socket.gethostbyname(hostname)
            except socket.gaierror:
                ip = hostname  # If hostname is already an IP
            
            # Check if server is authorized
            if not self.config.is_server_authorized(ip, hostname):
                logger.warning(f"Server {server_url} is not authorized. Adding to authorized servers.")
                self.config.add_authorized_server(server_ip=ip, hostname=hostname)
                self.config.save()
            
            return True
        except Exception as e:
            logger.error(f"Error checking server authorization: {e}")
            return False
    
    def register_with_server(self):
        """Register this client with the server"""
        if not self.server_url:
            logger.error("Server URL not set")
            return False
        
        if not self._check_server_authorization(self.server_url):
            logger.error("Server is not authorized")
            return False
        
        try:
            # Get server's public key
            response = requests.get(f"{self.server_url}/api/public_key")
            if response.status_code != 200:
                logger.error(f"Failed to get server public key: {response.text}")
                return False
            
            server_public_key = response.json()['public_key']
            
            # Get client's public key
            client_public_key = self.encryption.get_public_key_pem()
            
            # Get system information
            system_info = self.get_system_info()
            
            # Register client
            data = {
                'client_id': self.client_id,
                'public_key': client_public_key,
                'hostname': socket.gethostname(),
                'system': system_info['system'],
                'version': system_info['version']
            }
            
            response = requests.post(f"{self.server_url}/api/register_client", json=data)
            if response.status_code != 200:
                logger.error(f"Failed to register client: {response.text}")
                return False
            
            logger.info("Successfully registered with server")
            return True
        except Exception as e:
            logger.error(f"Error registering with server: {e}")
            return False
    
    def send_status_update(self, status_data):
        """Send status update to server"""
        if not self.server_url:
            logger.error("Server URL not set")
            return False
        
        if not self._check_server_authorization(self.server_url):
            logger.error("Server is not authorized")
            return False
        
        try:
            # Encrypt status data
            encrypted_data = self.encryption.encrypt_for_server(status_data)
            
            # Send to server
            data = {
                'encrypted_data': encrypted_data
            }
            
            response = requests.post(f"{self.server_url}/api/client/{self.client_id}/status", json=data)
            if response.status_code != 200:
                logger.error(f"Failed to send status update: {response.text}")
                return False
            
            logger.info("Successfully sent status update")
            return True
        except Exception as e:
            logger.error(f"Error sending status update: {e}")
            return False
    
    def get_schedule(self):
        """Get backup schedule from server"""
        if not self.server_url:
            logger.error("Server URL not set")
            return None
        
        if not self._check_server_authorization(self.server_url):
            logger.error("Server is not authorized")
            return None
        
        try:
            # Get encrypted schedule
            response = requests.get(f"{self.server_url}/api/client/{this.client_id}/schedule")
            if response.status_code != 200:
                logger.error(f"Failed to get schedule: {response.text}")
                return None
            
            encrypted_data = response.json()['encrypted_data']
            
            # Decrypt schedule
            decrypted_data = self.encryption.decrypt_from_server(encrypted_data)
            if decrypted_data is None:
                logger.error("Failed to decrypt schedule")
                return None
            
            schedule = json.loads(decrypted_data)
            logger.info("Successfully retrieved schedule")
            return schedule
        except Exception as e:
            logger.error(f"Error getting schedule: {e}")
            return None
    
    def report_backup_result(self, backup_id, result_data):
        """Report backup result to server"""
        if not self.server_url:
            logger.error("Server URL not set")
            return False
        
        if not this._check_server_authorization(self.server_url):
            logger.error("Server is not authorized")
            return False
        
        try:
            # Encrypt result data
            encrypted_data = this.encryption.encrypt_for_server(result_data)
            
            # Send to server
            data = {
                'encrypted_data': encrypted_data
            }
            
            response = requests.post(f"{this.server_url}/api/client/{this.client_id}/backup/{backup_id}/result", json=data)
            if response.status_code != 200:
                logger.error(f"Failed to report backup result: {response.text}")
                return False
            
            logger.info("Successfully reported backup result")
            return True
        except Exception as e:
            logger.error(f"Error reporting backup result: {e}")
            return False
    
    def get_system_info(self):
        """Get system information"""
        system = platform.system()
        release = platform.release()
        version = platform.version()
        machine = platform.machine()
        
        return {
            'system': f"{system} {release} ({machine})",
            'version': version,
            'hostname': socket.gethostname(),
            'python_version': platform.python_version(),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_disk_usage(self, path='/'):
        """Get disk usage information"""
        try:
            usage = psutil.disk_usage(path)
            return {
                'total': usage.total,
                'used': usage.used,
                'free': usage.free,
                'percent': usage.percent
            }
        except Exception as e:
            logger.error(f"Error getting disk usage: {e}")
            return None
    
    def get_backup_dirs(self):
        """Get directories to backup from config"""
        return self.config.get_all_config().get('backup_dirs', [])
    
    def get_exclude_patterns(self):
        """Get exclude patterns from config"""
        return self.config.get_all_config().get('exclude_patterns', [])
    
    def is_encryption_enabled(self):
        """Check if encryption is enabled"""
        return self.config.is_encryption_enabled()
    
    def is_compression_enabled(self):
        """Check if compression is enabled"""
        return self.config.is_compression_enabled()
    
    def get_max_backup_size(self):
        """Get maximum backup size"""
        return self.config.get_max_backup_size()
    
    def get_retention_days(self):
        """Get retention days"""
        return self.config.get_retention_days()
    
    def add_authorized_server(self, server_ip=None, subnet=None, hostname=None):
        """Add an authorized server"""
        self.config.add_authorized_server(server_ip, subnet, hostname)
    
    def remove_authorized_server(self, server_ip=None, subnet=None, hostname=None):
        """Remove an authorized server"""
        self.config.remove_authorized_server(server_ip, subnet, hostname)
    
    def set_server_url(self, url):
        """Set the server URL"""
        self.config.set_server_url(url)
        self.server_url = url
    
    def set_client_name(self, name):
        """Set the client name"""
        self.config.set_client_name(name)
    
    def add_backup_dir(self, directory):
        """Add a directory to backup"""
        self.config.add_backup_dir(directory)
    
    def remove_backup_dir(self, directory):
        """Remove a directory from backup"""
        self.config.remove_backup_dir(directory)
    
    def add_exclude_pattern(self, pattern):
        """Add an exclude pattern"""
        self.config.add_exclude_pattern(pattern)
    
    def remove_exclude_pattern(self, pattern):
        """Remove an exclude pattern"""
        self.config.remove_exclude_pattern(pattern)
    
    def set_max_backup_size(self, size_bytes):
        """Set the maximum backup size in bytes"""
        self.config.set_max_backup_size(size_bytes)
    
    def set_retention_days(self, days):
        """Set the number of days to keep backups"""
        self.config.set_retention_days(days)
    
    def set_encryption_enabled(self, enabled):
        """Set whether encryption is enabled"""
        self.config.set_encryption_enabled(enabled)
    
    def set_compression_enabled(self, enabled):
        """Set whether compression is enabled"""
        self.config.set_compression_enabled(enabled)
    
    def set_log_level(self, level):
        """Set the logging level"""
        self.config.set_log_level(level)
        logger.remove()
        logger.add(self.config.get_log_file(), level=level)
        logger.add(lambda msg: print(msg), level=level)
    
    def set_log_file(self, log_file):
        """Set the log file path"""
        self.config.set_log_file(log_file)
        logger.remove()
        logger.add(log_file, level=self.config.get_log_level())
        logger.add(lambda msg: print(msg), level=self.config.get_log_level())
    
    def get_all_config(self):
        """Get the entire configuration"""
        return self.config.get_all_config()
    
    def update_config(self, new_config):
        """Update the configuration with new values"""
        self.config.update_config(new_config) 