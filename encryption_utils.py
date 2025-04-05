#!/usr/bin/env python3
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization

class EncryptionManager:
    def __init__(self, key_file=None):
        self.key_file = key_file or os.path.expanduser("~/Lin-Win-Backup/keys/server_key.pem")
        self.private_key = None
        self.public_key = None
        self.client_keys = {}  # Store client public keys
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.key_file), exist_ok=True)
        
        # Load or generate keys
        self._load_or_generate_keys()
    
    def _load_or_generate_keys(self):
        """Load existing keys or generate new ones"""
        if os.path.exists(self.key_file):
            # Load existing keys
            with open(self.key_file, 'rb') as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None
                )
            # Load public key
            public_key_file = self.key_file.replace('.pem', '_public.pem')
            with open(public_key_file, 'rb') as f:
                self.public_key = serialization.load_pem_public_key(f.read())
        else:
            # Generate new keys
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            self.public_key = self.private_key.public_key()
            
            # Save private key
            with open(self.key_file, 'wb') as f:
                f.write(self.private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            # Save public key
            public_key_file = self.key_file.replace('.pem', '_public.pem')
            with open(public_key_file, 'wb') as f:
                f.write(self.public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ))
    
    def get_public_key_pem(self):
        """Get the public key in PEM format"""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
    
    def register_client(self, client_id, client_public_key_pem):
        """Register a client's public key"""
        try:
            client_public_key = serialization.load_pem_public_key(client_public_key_pem)
            self.client_keys[client_id] = client_public_key
            return True
        except Exception as e:
            print(f"Error registering client {client_id}: {e}")
            return False
    
    def encrypt_for_client(self, client_id, data):
        """Encrypt data for a specific client"""
        if client_id not in self.client_keys:
            raise ValueError(f"Client {client_id} not registered")
        
        # Convert data to bytes if it's a string
        if isinstance(data, str):
            data = data.encode()
        
        # Encrypt the data
        encrypted_data = self.client_keys[client_id].encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return base64.b64encode(encrypted_data).decode()
    
    def decrypt_from_client(self, encrypted_data):
        """Decrypt data from a client"""
        try:
            # Decode from base64
            encrypted_bytes = base64.b64decode(encrypted_data)
            
            # Decrypt the data
            decrypted_data = self.private_key.decrypt(
                encrypted_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return decrypted_data
        except Exception as e:
            print(f"Error decrypting data: {e}")
            return None
    
    def generate_client_key(self, client_id):
        """Generate a new key pair for a client"""
        # Generate a new key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        public_key = private_key.public_key()
        
        # Save the keys
        keys_dir = os.path.expanduser(f"~/Lin-Win-Backup/keys/clients/{client_id}")
        os.makedirs(keys_dir, exist_ok=True)
        
        # Save private key
        private_key_file = os.path.join(keys_dir, "private_key.pem")
        with open(private_key_file, 'wb') as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # Save public key
        public_key_file = os.path.join(keys_dir, "public_key.pem")
        with open(public_key_file, 'wb') as f:
            f.write(public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))
        
        # Register the client
        self.register_client(client_id, public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))
        
        return {
            'private_key': private_key_file,
            'public_key': public_key_file
        } 