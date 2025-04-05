#!/usr/bin/env python3
import os
import json
import requests
import base64
import socket
import platform
import uuid
from pathlib import Path
from datetime import datetime
from cryptography.hazmat.primitives import serialization
from encryption_utils import EncryptionManager

class ClientAPI:
    def __init__(self, server_url, client_id=None, keys_dir=None):
        self.server_url = server_url.rstrip('/')
        self.client_id = client_id or self._generate_client_id()
        self.keys_dir = keys_dir or os.path.expanduser(f"~/Lin-Win-Backup/keys/clients/{self.client_id}")
        
        # Create keys directory if it doesn't exist
        os.makedirs(self.keys_dir, exist_ok=True)
        
        # Initialize encryption manager
        self.encryption = EncryptionManager()
        
        # Load or generate client keys
        self._load_or_generate_keys()
    
    def _generate_client_id(self):
        """Generate a unique client ID based on hostname and MAC address"""
        hostname = socket.gethostname()
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0, 2*6, 2)][::-1])
        return f"{hostname}-{mac}"
    
    def _load_or_generate_keys(self):
        """Load existing client keys or generate new ones"""
        private_key_file = os.path.join(self.keys_dir, "private_key.pem")
        public_key_file = os.path.join(self.keys_dir, "public_key.pem")
        
        if os.path.exists(private_key_file) and os.path.exists(public_key_file):
            # Load existing keys
            with open(private_key_file, 'rb') as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None
                )
            with open(public_key_file, 'rb') as f:
                self.public_key = serialization.load_pem_public_key(f.read())
        else:
            # Generate new keys
            keys = self.encryption.generate_client_key(self.client_id)
            with open(keys['private_key'], 'rb') as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None
                )
            with open(keys['public_key'], 'rb') as f:
                self.public_key = serialization.load_pem_public_key(f.read())
    
    def register_with_server(self):
        """Register this client with the server"""
        try:
            # Get server's public key
            response = requests.get(f"{self.server_url}/api/public_key")
            if response.status_code != 200:
                print(f"Error getting server public key: {response.text}")
                return False
            
            server_public_key_pem = response.json()['public_key']
            
            # Register client with server
            client_public_key_pem = self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode()
            
            response = requests.post(
                f"{self.server_url}/api/register_client",
                json={
                    'client_id': self.client_id,
                    'public_key': client_public_key_pem,
                    'hostname': socket.gethostname(),
                    'system': platform.system(),
                    'version': platform.version()
                }
            )
            
            if response.status_code != 200:
                print(f"Error registering with server: {response.text}")
                return False
            
            print(f"Successfully registered with server as {self.client_id}")
            return True
        except Exception as e:
            print(f"Error registering with server: {e}")
            return False
    
    def send_status_update(self, status_data):
        """Send a status update to the server"""
        try:
            # Encrypt the status data
            encrypted_data = self.encryption.encrypt_for_client(self.client_id, json.dumps(status_data))
            
            # Send the encrypted data to the server
            response = requests.post(
                f"{self.server_url}/api/client/{self.client_id}/status",
                json={'encrypted_data': encrypted_data}
            )
            
            if response.status_code != 200:
                print(f"Error sending status update: {response.text}")
                return False
            
            return True
        except Exception as e:
            print(f"Error sending status update: {e}")
            return False
    
    def get_schedule(self):
        """Get the backup schedule from the server"""
        try:
            response = requests.get(f"{self.server_url}/api/client/{self.client_id}/schedule")
            
            if response.status_code != 200:
                print(f"Error getting schedule: {response.text}")
                return None
            
            # Decrypt the schedule data
            encrypted_data = response.json()['encrypted_data']
            decrypted_data = self.encryption.decrypt_from_client(encrypted_data)
            
            if decrypted_data is None:
                print("Error decrypting schedule data")
                return None
            
            return json.loads(decrypted_data)
        except Exception as e:
            print(f"Error getting schedule: {e}")
            return None
    
    def report_backup_result(self, backup_id, result_data):
        """Report the result of a backup to the server"""
        try:
            # Encrypt the result data
            encrypted_data = self.encryption.encrypt_for_client(self.client_id, json.dumps(result_data))
            
            # Send the encrypted data to the server
            response = requests.post(
                f"{self.server_url}/api/client/{self.client_id}/backup/{backup_id}/result",
                json={'encrypted_data': encrypted_data}
            )
            
            if response.status_code != 200:
                print(f"Error reporting backup result: {response.text}")
                return False
            
            return True
        except Exception as e:
            print(f"Error reporting backup result: {e}")
            return False
    
    def get_system_info(self):
        """Get system information for status updates"""
        return {
            'hostname': socket.gethostname(),
            'system': platform.system(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'python_version': platform.python_version()
        }
    
    def get_disk_usage(self, path='/'):
        """Get disk usage information"""
        try:
            import psutil
            usage = psutil.disk_usage(path)
            return {
                'total': usage.total,
                'used': usage.used,
                'free': usage.free,
                'percent': usage.percent
            }
        except ImportError:
            print("psutil module not installed. Install it with: pip install psutil")
            return None
        except Exception as e:
            print(f"Error getting disk usage: {e}")
            return None 