#!/usr/bin/env python3
import os
import sys
import json
import argparse
import http.server
import socketserver
import threading
import webbrowser
import hashlib
import secrets
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger
import socket
import platform
from urllib.parse import parse_qs, urlparse
from encryption_utils import EncryptionManager

# HTML template for the login page
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lin-Win-Backup Server - Login</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .login-container {
            background-color: white;
            padding: 30px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            width: 100%;
            max-width: 400px;
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            color: #666;
        }
        input[type="text"],
        input[type="password"] {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        button {
            width: 100%;
            padding: 10px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #0056b3;
        }
        .error-message {
            color: #dc3545;
            margin-top: 10px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>Lin-Win-Backup Server</h1>
        <form id="login-form" onsubmit="return handleLogin(event)">
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" required>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required>
            </div>
            <button type="submit">Login</button>
            <div id="error-message" class="error-message"></div>
        </form>
    </div>
    <script>
        async function handleLogin(event) {
            event.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ username, password }),
                });
                
                const data = await response.json();
                
                if (data.success) {
                    window.location.href = '/dashboard';
                } else {
                    document.getElementById('error-message').textContent = data.error || 'Invalid credentials';
                }
            } catch (error) {
                document.getElementById('error-message').textContent = 'An error occurred. Please try again.';
            }
            
            return false;
        }
    </script>
</body>
</html>
"""

# HTML template for the dashboard page
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lin-Win-Backup Server Dashboard</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 20px;
            border-bottom: 1px solid #ddd;
        }
        .client-selector {
            margin-bottom: 20px;
        }
        select {
            padding: 8px;
            font-size: 16px;
            border: 1px solid #ddd;
            border-radius: 4px;
            width: 100%;
            max-width: 300px;
        }
        .status-card {
            background-color: #f9f9f9;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 20px;
        }
        .status-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .status-badge {
            padding: 5px 10px;
            border-radius: 3px;
            font-weight: bold;
        }
        .status-running {
            background-color: #d4edda;
            color: #155724;
        }
        .status-stopped {
            background-color: #f8d7da;
            color: #721c24;
        }
        .status-completed {
            background-color: #d4edda;
            color: #155724;
        }
        .status-failed {
            background-color: #f8d7da;
            color: #721c24;
        }
        .status-pending {
            background-color: #fff3cd;
            color: #856404;
        }
        .action-buttons {
            margin-top: 20px;
        }
        .btn {
            padding: 8px 15px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            margin-right: 10px;
        }
        .btn-primary {
            background-color: #007bff;
            color: white;
        }
        .btn-danger {
            background-color: #dc3545;
            color: white;
        }
        .btn-success {
            background-color: #28a745;
            color: white;
        }
        .schedule-form {
            margin-top: 20px;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 5px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            color: #666;
        }
        input[type="text"],
        input[type="datetime-local"],
        select {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        .backup-history {
            margin-top: 20px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #f2f2f2;
        }
        .logout-btn {
            background-color: #6c757d;
            color: white;
            padding: 8px 15px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Lin-Win-Backup Server Dashboard</h1>
            <button class="logout-btn" onclick="handleLogout()">Logout</button>
        </div>
        
        <div class="client-selector">
            <label for="client-select">Select Client:</label>
            <select id="client-select" onchange="loadClientData()">
                <option value="">Select a client...</option>
            </select>
        </div>
        
        <div id="client-data">
            <div class="status-card">
                <h2>Client Status</h2>
                <p><strong>Hostname:</strong> <span id="hostname">-</span></p>
                <p><strong>System:</strong> <span id="system">-</span></p>
                <p><strong>Status:</strong> <span id="client-status" class="status-badge">-</span></p>
                <p><strong>Last Updated:</strong> <span id="last-updated">-</span></p>
            </div>
            
            <div class="status-card">
                <h2>Current Backup</h2>
                <div id="current-backup">
                    <p>No backup in progress</p>
                </div>
            </div>
            
            <div class="status-card">
                <h2>Backup Schedule</h2>
                <div id="schedule-info">
                    <p>No scheduled backups</p>
                </div>
                <div class="action-buttons">
                    <button class="btn btn-primary" onclick="showScheduleForm()">Add Schedule</button>
                </div>
                <div id="schedule-form" class="schedule-form" style="display: none;">
                    <h3>Add Backup Schedule</h3>
                    <form onsubmit="return handleScheduleSubmit(event)">
                        <div class="form-group">
                            <label for="schedule-type">Backup Type:</label>
                            <select id="schedule-type" required>
                                <option value="full">Full Backup</option>
                                <option value="incremental">Incremental Backup</option>
                                <option value="directory">Directory Backup</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="schedule-time">Schedule Time:</label>
                            <input type="datetime-local" id="schedule-time" required>
                        </div>
                        <div class="form-group">
                            <label for="schedule-source">Source Directory:</label>
                            <input type="text" id="schedule-source" required>
                        </div>
                        <button type="submit" class="btn btn-success">Save Schedule</button>
                        <button type="button" class="btn btn-danger" onclick="hideScheduleForm()">Cancel</button>
                    </form>
                </div>
            </div>
            
            <div class="status-card">
                <h2>Backup History</h2>
                <div class="backup-history">
                    <table id="backup-history">
                        <thead>
                            <tr>
                                <th>Type</th>
                                <th>Start Time</th>
                                <th>End Time</th>
                                <th>Status</th>
                                <th>Size</th>
                                <th>Files</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td colspan="6">No backup history available</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let currentClient = null;
        
        function formatBytes(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
        
        function formatDate(dateString) {
            if (!dateString) return '-';
            const date = new Date(dateString);
            return date.toLocaleString();
        }
        
        function updateStatusBadge(element, status) {
            element.textContent = status;
            element.className = 'status-badge status-' + status.toLowerCase();
        }
        
        async function loadClients() {
            try {
                const response = await fetch('/api/clients');
                const clients = await response.json();
                
                const select = document.getElementById('client-select');
                select.innerHTML = '<option value="">Select a client...</option>';
                
                clients.forEach(client => {
                    const option = document.createElement('option');
                    option.value = client.id;
                    option.textContent = client.hostname;
                    select.appendChild(option);
                });
            } catch (error) {
                console.error('Error loading clients:', error);
            }
        }
        
        async function loadClientData() {
            const clientId = document.getElementById('client-select').value;
            if (!clientId) {
                document.getElementById('client-data').style.display = 'none';
                return;
            }
            
            document.getElementById('client-data').style.display = 'block';
            
            try {
                const response = await fetch(`/api/client/${clientId}`);
                const data = await response.json();
                
                document.getElementById('hostname').textContent = data.hostname;
                document.getElementById('system').textContent = data.system;
                updateStatusBadge(document.getElementById('client-status'), data.status);
                document.getElementById('last-updated').textContent = formatDate(new Date());
                
                updateCurrentBackup(data.current_backup);
                updateScheduleInfo(data.schedule);
                updateBackupHistory(data.backup_history);
                
                currentClient = clientId;
            } catch (error) {
                console.error('Error loading client data:', error);
            }
        }
        
        function updateCurrentBackup(currentBackup) {
            const element = document.getElementById('current-backup');
            
            if (!currentBackup) {
                element.innerHTML = '<p>No backup in progress</p>';
                return;
            }
            
            element.innerHTML = `
                <p><strong>Type:</strong> ${currentBackup.type}</p>
                <p><strong>Start Time:</strong> ${formatDate(currentBackup.start_time)}</p>
                <p><strong>Status:</strong> <span class="status-badge status-${currentBackup.status.toLowerCase()}">${currentBackup.status}</span></p>
                <p><strong>Progress:</strong> ${currentBackup.progress}%</p>
                <p><strong>ETA:</strong> ${currentBackup.eta}</p>
                ${currentBackup.error ? `<p><strong>Error:</strong> ${currentBackup.error}</p>` : ''}
            `;
        }
        
        function updateScheduleInfo(schedule) {
            const element = document.getElementById('schedule-info');
            
            if (!schedule || schedule.length === 0) {
                element.innerHTML = '<p>No scheduled backups</p>';
                return;
            }
            
            let html = '<table><thead><tr><th>Type</th><th>Time</th><th>Source</th><th>Actions</th></tr></thead><tbody>';
            
            schedule.forEach(item => {
                html += `
                    <tr>
                        <td>${item.type}</td>
                        <td>${formatDate(item.time)}</td>
                        <td>${item.source}</td>
                        <td>
                            <button class="btn btn-danger" onclick="deleteSchedule('${item.id}')">Delete</button>
                        </td>
                    </tr>
                `;
            });
            
            html += '</tbody></table>';
            element.innerHTML = html;
        }
        
        function updateBackupHistory(history) {
            const tbody = document.querySelector('#backup-history tbody');
            tbody.innerHTML = '';
            
            if (!history || history.length === 0) {
                const row = document.createElement('tr');
                row.innerHTML = '<td colspan="6">No backup history available</td>';
                tbody.appendChild(row);
                return;
            }
            
            for (const backup of history) {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${backup.type}</td>
                    <td>${formatDate(backup.start_time)}</td>
                    <td>${formatDate(backup.end_time)}</td>
                    <td><span class="status-badge status-${backup.status.toLowerCase()}">${backup.status}</span></td>
                    <td>${formatBytes(backup.size)}</td>
                    <td>${backup.files}</td>
                `;
                tbody.appendChild(row);
            }
        }
        
        function showScheduleForm() {
            document.getElementById('schedule-form').style.display = 'block';
        }
        
        function hideScheduleForm() {
            document.getElementById('schedule-form').style.display = 'none';
        }
        
        async function handleScheduleSubmit(event) {
            event.preventDefault();
            
            const scheduleData = {
                type: document.getElementById('schedule-type').value,
                time: document.getElementById('schedule-time').value,
                source: document.getElementById('schedule-source').value
            };
            
            try {
                const response = await fetch(`/api/client/${currentClient}/schedule`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(scheduleData),
                });
                
                if (response.ok) {
                    hideScheduleForm();
                    loadClientData();
                } else {
                    const data = await response.json();
                    alert(data.error || 'Failed to add schedule');
                }
            } catch (error) {
                console.error('Error adding schedule:', error);
                alert('An error occurred while adding the schedule');
            }
            
            return false;
        }
        
        async function deleteSchedule(scheduleId) {
            if (!confirm('Are you sure you want to delete this schedule?')) {
                return;
            }
            
            try {
                const response = await fetch(`/api/client/${currentClient}/schedule/${scheduleId}`, {
                    method: 'DELETE',
                });
                
                if (response.ok) {
                    loadClientData();
                } else {
                    const data = await response.json();
                    alert(data.error || 'Failed to delete schedule');
                }
            } catch (error) {
                console.error('Error deleting schedule:', error);
                alert('An error occurred while deleting the schedule');
            }
        }
        
        async function handleLogout() {
            try {
                const response = await fetch('/logout', {
                    method: 'POST',
                });
                
                if (response.ok) {
                    window.location.href = '/';
                }
            } catch (error) {
                console.error('Error logging out:', error);
            }
        }
        
        // Initial load
        loadClients();
    </script>
</body>
</html>
"""

class ServerAPIHandler(http.server.SimpleHTTPRequestHandler):
    encryption = None  # Class variable to store the encryption manager
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # Serve web interface pages
        if path == '/':
            self._serve_login_page()
        elif path == '/dashboard':
            self._serve_dashboard_page()
        # API endpoints
        elif path == '/api/public_key':
            self._handle_public_key()
        elif path.startswith('/api/client/'):
            client_id = path.split('/')[3]
            if path.endswith('/status'):
                self._handle_client_status(client_id)
            elif path.endswith('/schedule'):
                self._handle_client_schedule(client_id)
            else:
                self._send_error(404, "Not found")
        else:
            # Serve static files
            super().do_GET()
    
    def _serve_login_page(self):
        """Serve the login page"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(LOGIN_TEMPLATE.encode())
    
    def _serve_dashboard_page(self):
        """Serve the dashboard page"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(DASHBOARD_TEMPLATE.encode())
    
    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # Get request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        data = json.loads(body.decode())
        
        # API endpoints
        if path == '/api/register_client':
            self._handle_register_client(data)
        elif path.startswith('/api/client/'):
            client_id = path.split('/')[3]
            if path.endswith('/status'):
                self._handle_client_status_update(client_id, data)
            elif '/backup/' in path and path.endswith('/result'):
                backup_id = path.split('/')[-2]
                self._handle_backup_result(client_id, backup_id, data)
            else:
                self._send_error(404, "Not found")
        else:
            self._send_error(404, "Not found")
    
    def _handle_public_key(self):
        """Handle request for server's public key"""
        try:
            public_key = self.encryption.get_server_public_key()
            self._send_json_response({'public_key': public_key})
        except Exception as e:
            self._send_error(500, str(e))
    
    def _handle_register_client(self, data):
        """Handle client registration"""
        try:
            client_id = data['client_id']
            public_key = data['public_key']
            
            # Register client's public key
            self.encryption.register_client_public_key(client_id, public_key)
            
            # Save client info
            clients_file = os.path.expanduser('~/Lin-Win-Backup/clients/clients.json')
            os.makedirs(os.path.dirname(clients_file), exist_ok=True)
            
            clients = {}
            if os.path.exists(clients_file):
                with open(clients_file, 'r') as f:
                    clients = json.load(f)
            
            clients[client_id] = {
                'hostname': data['hostname'],
                'system': data['system'],
                'version': data['version'],
                'last_seen': datetime.now().isoformat(),
                'current_backup': None,
                'next_scheduled': None,
                'backup_history': []
            }
            
            with open(clients_file, 'w') as f:
                json.dump(clients, f, indent=2)
            
            self._send_json_response({'status': 'success'})
        except Exception as e:
            self._send_error(500, str(e))
    
    def _handle_client_status_update(self, client_id, data):
        """Handle client status update"""
        try:
            # Decrypt the status data
            encrypted_data = data['encrypted_data']
            decrypted_data = self.encryption.decrypt_from_client(encrypted_data)
            
            if decrypted_data is None:
                self._send_error(400, "Failed to decrypt data")
                return
            
            status_data = json.loads(decrypted_data)
            
            # Update client info
            clients_file = os.path.expanduser('~/Lin-Win-Backup/clients/clients.json')
            with open(clients_file, 'r') as f:
                clients = json.load(f)
            
            if client_id not in clients:
                self._send_error(404, "Client not found")
                return
            
            clients[client_id].update({
                'last_seen': datetime.now().isoformat(),
                'current_backup': status_data.get('current_backup'),
                'next_scheduled': status_data.get('next_scheduled'),
                'disk_usage': status_data.get('disk_usage')
            })
            
            # Update backup history
            if 'backup_result' in status_data:
                backup_result = status_data['backup_result']
                clients[client_id]['backup_history'].append(backup_result)
                # Keep only last 10 backups
                clients[client_id]['backup_history'] = clients[client_id]['backup_history'][-10:]
            
            with open(clients_file, 'w') as f:
                json.dump(clients, f, indent=2)
            
            self._send_json_response({'status': 'success'})
        except Exception as e:
            self._send_error(500, str(e))
    
    def _handle_client_schedule(self, client_id):
        """Handle request for client's backup schedule"""
        try:
            clients_file = os.path.expanduser('~/Lin-Win-Backup/clients/clients.json')
            with open(clients_file, 'r') as f:
                clients = json.load(f)
            
            if client_id not in clients:
                self._send_error(404, "Client not found")
                return
            
            schedule = {
                'next_scheduled': clients[client_id].get('next_scheduled')
            }
            
            # Encrypt the schedule data
            encrypted_data = self.encryption.encrypt_for_client(client_id, json.dumps(schedule))
            self._send_json_response({'encrypted_data': encrypted_data})
        except Exception as e:
            self._send_error(500, str(e))
    
    def _handle_backup_result(self, client_id, backup_id, data):
        """Handle backup result report"""
        try:
            # Decrypt the result data
            encrypted_data = data['encrypted_data']
            decrypted_data = self.encryption.decrypt_from_client(encrypted_data)
            
            if decrypted_data is None:
                self._send_error(400, "Failed to decrypt data")
                return
            
            result_data = json.loads(decrypted_data)
            
            # Update client info
            clients_file = os.path.expanduser('~/Lin-Win-Backup/clients/clients.json')
            with open(clients_file, 'r') as f:
                clients = json.load(f)
            
            if client_id not in clients:
                self._send_error(404, "Client not found")
                return
            
            # Add to backup history
            result_data['backup_id'] = backup_id
            result_data['timestamp'] = datetime.now().isoformat()
            clients[client_id]['backup_history'].append(result_data)
            # Keep only last 10 backups
            clients[client_id]['backup_history'] = clients[client_id]['backup_history'][-10:]
            
            # Clear current backup if this was the one in progress
            if (clients[client_id].get('current_backup', {}).get('id') == backup_id):
                clients[client_id]['current_backup'] = None
            
            with open(clients_file, 'w') as f:
                json.dump(clients, f, indent=2)
            
            self._send_json_response({'status': 'success'})
        except Exception as e:
            self._send_error(500, str(e))
    
    def _send_json_response(self, data):
        """Send JSON response"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def _send_error(self, code, message):
        """Send error response"""
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({'error': message}).encode())
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def run_server(port=3000):
    """Run the server"""
    # Create necessary directories
    os.makedirs(os.path.expanduser('~/Lin-Win-Backup/clients'), exist_ok=True)
    os.makedirs(os.path.expanduser('~/Lin-Win-Backup/keys/server'), exist_ok=True)
    
    # Initialize encryption manager
    encryption = EncryptionManager()
    
    # Set the encryption manager as a class variable
    ServerAPIHandler.encryption = encryption
    
    # Start server
    with socketserver.TCPServer(("0.0.0.0", port), ServerAPIHandler) as httpd:
        print(f"Server started on port {port}")
        print("Local access: http://localhost:3000")
        
        # Get all IP addresses
        hostname = socket.gethostname()
        ip_addresses = socket.gethostbyname_ex(hostname)[2]
        for ip in ip_addresses:
            print(f"Network access: http://{ip}:3000")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            httpd.server_close()

def main():
    """Parse arguments and start server web interface"""
    parser = argparse.ArgumentParser(description='Lin-Win-Backup Server Web Interface')
    parser.add_argument('--port', type=int, default=3000, help='Port to run the server on (default: 3000)')
    
    args = parser.parse_args()
    
    # Configure logging
    log_dir = os.path.expanduser("~/Lin-Win-Backup/logs")
    os.makedirs(log_dir, exist_ok=True)
    logger.add(os.path.join(log_dir, "server_web_interface.log"), rotation="1 day", retention="7 days")
    
    # Start server
    run_server(port=args.port)

if __name__ == "__main__":
    main() 