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
import http.server
import threading

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
        self.keys_dir = keys_dir or os.path.expanduser('~/Lin-Win-Backup/keys')
        
        # Initialize key management
        os.makedirs(self.keys_dir, exist_ok=True)
        self.private_key_path = os.path.join(self.keys_dir, 'id_rsa')
        self.public_key_path = os.path.join(self.keys_dir, 'id_rsa.pub')
        
        # Initialize encryption manager
        self.encryption = self._load_or_generate_keys()
        
        # Set up logging
        log_level = self.config.get_log_level()
        log_file = self.config.get_log_file()
        logger.remove()  # Remove default handler
        logger.add(log_file, level=log_level)
        logger.add(lambda msg: print(msg), level=log_level)  # Also print to console
        
        # Initialize backup status tracking
        self.current_backup = None
        self.backup_history = []
        
        # Start backup control server
        self._start_backup_control_server()
    
    def _generate_client_id(self):
        """Generate a unique client ID based on hostname and MAC address"""
        hostname = socket.gethostname()
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0, 2 * 6, 2)][::-1])
        return f"client_{hashlib.md5(f"{hostname}_{mac}".encode()).hexdigest()[:8]}"
    
    def _load_or_generate_keys(self):
        """Load existing keys or generate new ones"""
        encryption = EncryptionManager()
        
        # Check if keys already exist
        if os.path.exists(self.private_key_path) and os.path.exists(self.public_key_path):
            # Load existing keys
            encryption.load_keys(self.private_key_path, self.public_key_path)
        else:
            # Generate new keys
            encryption.generate_keys()
            encryption.save_keys(self.private_key_path, self.public_key_path)
        
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
    
    def generate_keys(self):
        """Generate new RSA key pair for the client"""
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.backends import default_backend
            
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            
            # Save private key
            with open(self.private_key_path, 'wb') as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            # Save public key
            public_key = private_key.public_key()
            with open(self.public_key_path, 'wb') as f:
                f.write(public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ))
            
            # Set proper permissions
            os.chmod(self.private_key_path, 0o600)
            os.chmod(self.public_key_path, 0o644)
            
            return True
        except Exception as e:
            logger.error(f"Failed to generate keys: {str(e)}")
            return False
    
    def register_with_server(self, temp_token=None):
        """Register client with server and exchange keys"""
        try:
            # Generate new keys if they don't exist
            if not os.path.exists(self.private_key_path) or not os.path.exists(self.public_key_path):
                if not self.generate_keys():
                    return False
            
            # Read public key
            with open(self.public_key_path, 'r') as f:
                public_key = f.read()
            
            # Prepare registration data
            data = {
                'client_id': self.client_id,
                'public_key': public_key,
                'system': platform.system(),
                'version': platform.version(),
                'hostname': socket.gethostname()
            }
            
            # Add temporary token if provided
            if temp_token:
                data['temp_token'] = temp_token
            
            # Send registration request
            response = requests.post(
                f"{self.server_url}/api/register_client_key",
                json=data,
                headers={'Authorization': f'Bearer {self._get_auth_token()}'}
            )
            
            if response.status_code == 200:
                logger.info("Successfully registered with server")
                return True
            else:
                logger.error(f"Failed to register with server: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error during registration: {str(e)}")
            return False
    
    def _get_auth_token(self):
        """Get authentication token for API requests"""
        # First try to get token from environment
        token = os.environ.get('BACKUP_AUTH_TOKEN')
        if token:
            return token
            
        # Then try to read from token file
        token_file = os.path.join(self.config_dir, 'auth.token')
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                return f.read().strip()
        
        return None
    
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
    
    def report_backup_result(self, backup_type, status, size=0, files=0, error=None):
        """Report final backup result to server"""
        try:
            # Create backup result
            backup_result = {
                'type': backup_type,
                'status': status,
                'size': size,
                'files': files,
                'error': error,
                'start_time': self.current_backup['start_time'] if self.current_backup else datetime.now().isoformat(),
                'end_time': datetime.now().isoformat()
            }
            
            # Add to history
            self.backup_history.append(backup_result)
            
            # Prepare result data
            result_data = {
                'client_id': self.client_id,
                'backup_result': backup_result
            }
            
            # Send result to server
            response = requests.post(
                f"{self.server_url}/api/client/{self.client_id}/backup/result",
                json=result_data,
                headers={'Authorization': f'Bearer {self._get_auth_token()}'}
            )
            
            if response.status_code == 200:
                logger.info(f"Backup result reported: {status}")
                # Clear current backup
                self.current_backup = None
                return True
            else:
                logger.error(f"Failed to report backup result: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error reporting backup result: {str(e)}")
            return False
    
    def start_backup(self, backup_type, source_dir=None):
        """Start a backup operation"""
        try:
            # Update status to in-progress
            if not self.update_backup_status(backup_type, 'in_progress', 0):
                return False
            
            # Perform backup operation based on type
            if backup_type == 'full':
                # Implement full backup
                pass
            elif backup_type == 'incremental':
                # Implement incremental backup
                pass
            elif backup_type == 'directory':
                if not source_dir:
                    raise ValueError("Source directory required for directory backup")
                # Implement directory backup
                pass
            
            # Update progress periodically
            for progress in range(0, 101, 10):
                if not self.update_backup_status(backup_type, 'in_progress', progress):
                    return False
                time.sleep(1)  # Simulate backup progress
            
            # Report successful completion
            return self.report_backup_result(backup_type, 'completed', size=1000, files=100)
            
        except Exception as e:
            logger.error(f"Error during backup: {str(e)}")
            self.report_backup_result(backup_type, 'failed', error=str(e))
            return False
    
    def check_schedule(self):
        """Check for scheduled backups"""
        try:
            response = requests.get(
                f"{self.server_url}/api/client/{self.client_id}/schedule",
                headers={'Authorization': f'Bearer {self._get_auth_token()}'}
            )
            
            if response.status_code == 200:
                schedule = response.json()
                if schedule.get('next_scheduled'):
                    # Check if it's time to run the backup
                    scheduled_time = datetime.fromisoformat(schedule['next_scheduled'])
                    if datetime.now() >= scheduled_time:
                        return self.start_backup(
                            schedule.get('type', 'full'),
                            schedule.get('source', '/')
                        )
            return False
            
        except Exception as e:
            logger.error(f"Error checking schedule: {str(e)}")
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
    
    def update_backup_status(self, backup_type, status, progress=0, error=None):
        """Update and report backup status to server"""
        try:
            # Update local status
            self.current_backup = {
                'type': backup_type,
                'status': status,
                'progress': progress,
                'error': error,
                'start_time': datetime.now().isoformat(),
                'end_time': datetime.now().isoformat() if status in ['completed', 'failed'] else None
            }
            
            # Prepare status data
            status_data = {
                'client_id': self.client_id,
                'current_backup': self.current_backup,
                'system': platform.system(),
                'version': platform.version(),
                'hostname': socket.gethostname()
            }
            
            # Send status update to server
            response = requests.post(
                f"{self.server_url}/api/client/{self.client_id}/status",
                json=status_data,
                headers={'Authorization': f'Bearer {self._get_auth_token()}'}
            )
            
            if response.status_code == 200:
                logger.info(f"Backup status updated: {status} ({progress}%)")
                return True
            else:
                logger.error(f"Failed to update backup status: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating backup status: {str(e)}")
            return False
    
    def _start_backup_control_server(self):
        """Start a server to handle backup control requests"""
        class BackupControlHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                self.client_api = self
                super().__init__(*args, **kwargs)
            
            def do_POST(self):
                """Handle POST requests"""
                if self.path == '/api/backup/start':
                    self._handle_backup_start()
                else:
                    self._send_error(404, "Not found")
            
            def _handle_backup_start(self):
                """Handle backup start request"""
                try:
                    # Get request body
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length)
                    
                    if not body:
                        return self._send_error(400, "Empty request body")
                    
                    try:
                        data = json.loads(body.decode())
                    except json.JSONDecodeError:
                        return self._send_error(400, "Invalid JSON in request body")
                    
                    # Validate backup type
                    backup_type = data.get('type')
                    if backup_type not in ['full', 'incremental', 'directory']:
                        return self._send_error(400, "Invalid backup type")
                    
                    # Validate source directory for directory backup
                    source_dir = data.get('source_dir')
                    if backup_type == 'directory' and not source_dir:
                        return self._send_error(400, "Source directory required for directory backup")
                    
                    # Start the backup
                    if self.client_api.start_backup(backup_type, source_dir):
                        self._send_json_response({'status': 'success', 'message': 'Backup started'})
                    else:
                        self._send_error(500, "Failed to start backup")
                    
                except Exception as e:
                    logger.error(f"Error handling backup start request: {str(e)}")
                    self._send_error(500, str(e))
            
            def _send_json_response(self, data, status_code=200):
                """Send JSON response"""
                self.send_response(status_code)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())
            
            def _send_error(self, code, message):
                """Send error response"""
                self.send_response(code)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': message}).encode())
        
        # Start the server in a separate thread
        server = http.server.ThreadingTCPServer(('localhost', 0), BackupControlHandler)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        # Store the server port for the client to use
        self.backup_control_port = server.server_address[1] 