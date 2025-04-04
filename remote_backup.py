#!/usr/bin/env python3
import os
import paramiko
from pathlib import Path
from loguru import logger
from config import REMOTE_CONFIG

class RemoteBackup:
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
            # Check if we have all required connection parameters
            if not self.server_ip:
                logger.error("Server IP is not configured")
                return False
                
            if not self.server_user:
                logger.error("Server username is not configured")
                return False
                
            # Create SSH client
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect using SSH key if provided
            if self.ssh_key and os.path.exists(self.ssh_key):
                try:
                    key = paramiko.RSAKey.from_private_key_file(self.ssh_key)
                    logger.info(f"Connecting to {self.server_ip}:{self.server_port} as {self.server_user} using key {self.ssh_key}")
                    self.ssh_client.connect(
                        hostname=self.server_ip,
                        port=self.server_port,
                        username=self.server_user,
                        pkey=key,
                        timeout=10
                    )
                except Exception as e:
                    logger.error(f"Failed to connect with SSH key: {e}")
                    logger.info("Falling back to password authentication")
                    # Fall back to password authentication or return False
                    return False
            else:
                # If no key or key doesn't exist, ask for password
                logger.info(f"SSH key not specified or not found at {self.ssh_key}")
                logger.info(f"Connecting to {self.server_ip}:{self.server_port} as {self.server_user} with password authentication")
                
                # In a real application, you'd prompt for password here,
                # but for automated scripts, this should come from environment
                password = os.getenv('BACKUP_SERVER_PASSWORD', '')
                
                if not password:
                    logger.error("No SSH key or password available for authentication")
                    return False
                    
                self.ssh_client.connect(
                    hostname=self.server_ip,
                    port=self.server_port,
                    username=self.server_user,
                    password=password,
                    timeout=10
                )
                
            logger.info(f"Connected to remote server {self.server_ip}")
            return True
            
        except paramiko.AuthenticationException:
            logger.error("Authentication failed. Please check your credentials.")
            return False
        except paramiko.SSHException as e:
            logger.error(f"SSH error: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to remote server: {e}")
            return False
            
    def disconnect(self):
        """Close SSH connection"""
        if self.ssh_client:
            self.ssh_client.close()
            logger.info("Disconnected from remote server")
            
    def ensure_remote_directory(self, remote_path):
        """Ensure remote directory exists"""
        try:
            self.ssh_client.exec_command(f'mkdir -p {remote_path}')
            return True
        except Exception as e:
            logger.error(f"Failed to create remote directory: {e}")
            return False
            
    def upload_file(self, local_path, remote_path):
        """Upload a file to remote server"""
        try:
            sftp = self.ssh_client.open_sftp()
            sftp.put(local_path, remote_path)
            sftp.close()
            logger.info(f"Uploaded {local_path} to {remote_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            return False
            
    def upload_directory(self, local_dir, remote_dir):
        """Upload a directory to remote server"""
        try:
            sftp = self.ssh_client.open_sftp()
            
            # Ensure remote directory exists
            self.ensure_remote_directory(remote_dir)
            
            # Upload all files in directory
            for root, dirs, files in os.walk(local_dir):
                for dir_name in dirs:
                    local_path = os.path.join(root, dir_name)
                    remote_path = os.path.join(
                        remote_dir,
                        os.path.relpath(local_path, local_dir)
                    )
                    self.ensure_remote_directory(remote_path)
                    
                for file_name in files:
                    local_path = os.path.join(root, file_name)
                    remote_path = os.path.join(
                        remote_dir,
                        os.path.relpath(local_path, local_dir)
                    )
                    sftp.put(local_path, remote_path)
                    
            sftp.close()
            logger.info(f"Uploaded directory {local_dir} to {remote_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload directory: {e}")
            return False
            
    def download_file(self, remote_path, local_path):
        """Download a file from remote server"""
        try:
            sftp = self.ssh_client.open_sftp()
            sftp.get(remote_path, local_path)
            sftp.close()
            logger.info(f"Downloaded {remote_path} to {local_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            return False
            
    def download_directory(self, remote_dir, local_dir):
        """Download a directory from remote server"""
        try:
            sftp = self.ssh_client.open_sftp()
            
            # Create local directory if it doesn't exist
            os.makedirs(local_dir, exist_ok=True)
            
            def download_dir(remote_path, local_path):
                try:
                    sftp.stat(remote_path)
                except FileNotFoundError:
                    return
                    
                try:
                    items = sftp.listdir_attr(remote_path)
                    for item in items:
                        remote_item_path = os.path.join(remote_path, item.filename)
                        local_item_path = os.path.join(local_path, item.filename)
                        
                        if item.st_mode & 0o4000:  # Directory
                            os.makedirs(local_item_path, exist_ok=True)
                            download_dir(remote_item_path, local_item_path)
                        else:  # File
                            sftp.get(remote_item_path, local_item_path)
                            
                except Exception as e:
                    logger.error(f"Error processing {remote_path}: {e}")
                    
            download_dir(remote_dir, local_dir)
            sftp.close()
            logger.info(f"Downloaded directory {remote_dir} to {local_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download directory: {e}")
            return False
            
    def list_remote_files(self, remote_path):
        """List files in remote directory"""
        try:
            sftp = self.ssh_client.open_sftp()
            files = sftp.listdir(remote_path)
            sftp.close()
            return files
        except Exception as e:
            logger.error(f"Failed to list remote files: {e}")
            return []
            
    def delete_remote_file(self, remote_path):
        """Delete a file from remote server"""
        try:
            sftp = self.ssh_client.open_sftp()
            sftp.remove(remote_path)
            sftp.close()
            logger.info(f"Deleted {remote_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete remote file: {e}")
            return False
            
    def get_remote_file_size(self, remote_path):
        """Get size of remote file"""
        try:
            sftp = self.ssh_client.open_sftp()
            size = sftp.stat(remote_path).st_size
            sftp.close()
            return size
        except Exception as e:
            logger.error(f"Failed to get remote file size: {e}")
            return 0 