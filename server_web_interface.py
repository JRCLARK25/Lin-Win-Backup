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

class ServerHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.clients_file = kwargs.pop('clients_file', None)
        self.users_file = kwargs.pop('users_file', None)
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(LOGIN_TEMPLATE.encode())
        elif self.path == '/dashboard':
            # Check if user is authenticated
            if not self.check_auth():
                self.redirect_to_login()
                return
                
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(DASHBOARD_TEMPLATE.encode())
        elif self.path.startswith('/api/'):
            if not self.check_auth():
                self.send_error(401, 'Unauthorized')
                return
                
            if self.path == '/api/clients':
                self.handle_get_clients()
            elif self.path.startswith('/api/client/'):
                client_id = self.path.split('/')[3]
                self.handle_get_client(client_id)
            else:
                self.send_error(404, 'Not Found')
        else:
            self.send_error(404, 'Not Found')
    
    def do_POST(self):
        if self.path == '/login':
            self.handle_login()
        elif self.path == '/logout':
            self.handle_logout()
        elif self.path.startswith('/api/client/') and '/schedule' in self.path:
            if not self.check_auth():
                self.send_error(401, 'Unauthorized')
                return
                
            client_id = self.path.split('/')[3]
            self.handle_add_schedule(client_id)
        else:
            self.send_error(404, 'Not Found')
    
    def do_DELETE(self):
        if not self.check_auth():
            self.send_error(401, 'Unauthorized')
            return
            
        if '/api/client/' in self.path and '/schedule/' in self.path:
            parts = self.path.split('/')
            client_id = parts[3]
            schedule_id = parts[5]
            self.handle_delete_schedule(client_id, schedule_id)
        else:
            self.send_error(404, 'Not Found')
    
    def check_auth(self):
        if 'Cookie' not in self.headers:
            return False
            
        auth_cookie = self.headers['Cookie']
        if not auth_cookie.startswith('auth_token='):
            return False
            
        token = auth_cookie.split('=')[1].split(';')[0]
        return self.verify_token(token)
    
    def verify_token(self, token):
        # In a real application, you would verify the token against a database
        # For this example, we'll just check if it exists in the users file
        try:
            with open(self.users_file, 'r') as f:
                users = json.load(f)
                return any(user.get('token') == token for user in users)
        except:
            return False
    
    def redirect_to_login(self):
        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()
    
    def handle_login(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode())
        
        username = data.get('username')
        password = data.get('password')
        
        try:
            with open(self.users_file, 'r') as f:
                users = json.load(f)
                
            user = next((u for u in users if u['username'] == username), None)
            
            if user and self.verify_password(password, user['password']):
                # Generate a new token
                token = secrets.token_urlsafe(32)
                user['token'] = token
                
                # Update the users file
                with open(self.users_file, 'w') as f:
                    json.dump(users, f, indent=2)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Set-Cookie', f'auth_token={token}; Path=/; HttpOnly')
                self.end_headers()
                self.wfile.write(json.dumps({'success': True}).encode())
            else:
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'success': False, 'error': 'Invalid credentials'}).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'error': str(e)}).encode())
    
    def handle_logout(self):
        if 'Cookie' in self.headers:
            auth_cookie = self.headers['Cookie']
            if auth_cookie.startswith('auth_token='):
                token = auth_cookie.split('=')[1].split(';')[0]
                
                try:
                    with open(self.users_file, 'r') as f:
                        users = json.load(f)
                    
                    # Remove the token from the user
                    for user in users:
                        if user.get('token') == token:
                            user.pop('token', None)
                    
                    with open(self.users_file, 'w') as f:
                        json.dump(users, f, indent=2)
                except:
                    pass
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Set-Cookie', 'auth_token=; Path=/; HttpOnly; Max-Age=0')
        self.end_headers()
        self.wfile.write(json.dumps({'success': True}).encode())
    
    def verify_password(self, password, hashed_password):
        # In a real application, you would use a proper password hashing library
        # For this example, we'll use a simple hash
        return hashlib.sha256(password.encode()).hexdigest() == hashed_password
    
    def handle_get_clients(self):
        try:
            with open(self.clients_file, 'r') as f:
                clients = json.load(f)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(clients).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def handle_get_client(self, client_id):
        try:
            with open(self.clients_file, 'r') as f:
                clients = json.load(f)
            
            client = next((c for c in clients if c['id'] == client_id), None)
            
            if client:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(client).encode())
            else:
                self.send_error(404, 'Client not found')
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def handle_add_schedule(self, client_id):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode())
        
        try:
            with open(self.clients_file, 'r') as f:
                clients = json.load(f)
            
            client = next((c for c in clients if c['id'] == client_id), None)
            
            if client:
                if 'schedule' not in client:
                    client['schedule'] = []
                
                schedule_item = {
                    'id': secrets.token_urlsafe(8),
                    'type': data['type'],
                    'time': data['time'],
                    'source': data['source']
                }
                
                client['schedule'].append(schedule_item)
                
                with open(self.clients_file, 'w') as f:
                    json.dump(clients, f, indent=2)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'success': True}).encode())
            else:
                self.send_error(404, 'Client not found')
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def handle_delete_schedule(self, client_id, schedule_id):
        try:
            with open(self.clients_file, 'r') as f:
                clients = json.load(f)
            
            client = next((c for c in clients if c['id'] == client_id), None)
            
            if client and 'schedule' in client:
                client['schedule'] = [s for s in client['schedule'] if s['id'] != schedule_id]
                
                with open(self.clients_file, 'w') as f:
                    json.dump(clients, f, indent=2)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'success': True}).encode())
            else:
                self.send_error(404, 'Client or schedule not found')
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

def run_server_web_interface(clients_dir=None, port=3001, open_browser=True):
    """Run the server web interface"""
    global clients_directory
    clients_directory = clients_dir or os.path.expanduser("~/Lin-Win-Backup/clients")
    
    print(f"\nDebug: Using clients directory: {clients_directory}")
    
    # Ensure clients directory exists
    if not os.path.exists(clients_directory):
        try:
            os.makedirs(clients_directory, exist_ok=True)
            print(f"Debug: Created clients directory: {clients_directory}")
        except Exception as e:
            print(f"Error: Failed to create clients directory: {e}")
            return
    
    # Create sample clients file if it doesn't exist
    clients_file = Path(clients_directory) / 'clients.json'
    if not clients_file.exists():
        sample_clients = [
            {
                "id": "client1",
                "hostname": "puppy-OptiPlex-7000",
                "system": "Linux",
                "status": "idle",
                "current_backup": None,
                "schedule": [],
                "backup_history": []
            }
        ]
        try:
            with open(clients_file, 'w') as f:
                json.dump(sample_clients, f, indent=2)
            print(f"Debug: Created sample clients file at {clients_file}")
        except Exception as e:
            print(f"Error: Failed to create sample clients file: {e}")
            return
    
    # Create users file if it doesn't exist
    users_file = Path(clients_directory) / 'users.json'
    if not users_file.exists():
        # Create a default admin user (username: admin, password: admin)
        default_users = [
            {
                "username": "admin",
                "password": hashlib.sha256("admin".encode()).hexdigest(),
                "role": "admin"
            }
        ]
        try:
            with open(users_file, 'w') as f:
                json.dump(default_users, f, indent=2)
            print(f"Debug: Created users file at {users_file}")
        except Exception as e:
            print(f"Error: Failed to create users file: {e}")
            return
    
    # Set up server handler
    class CustomServerHandler(ServerHandler):
        def __init__(self, *args, **kwargs):
            self.clients_file = clients_file
            self.users_file = users_file
            super().__init__(*args, clients_file=clients_file, users_file=users_file)
    
    try:
        # Allow connections from any IP address by binding to 0.0.0.0
        server = socketserver.TCPServer(("0.0.0.0", port), CustomServerHandler)
        server.allow_reuse_address = True
        
        logger.info(f"Starting server web interface on port {port}")
        print(f"\nDebug: Starting server web interface on port {port}")
        
        # Get the machine's IP addresses
        try:
            ip_addresses = []
            # Get all IP addresses for the machine
            for info in socket.getaddrinfo(socket.gethostname(), None):
                ip = info[4][0]
                if not ip.startswith('127.') and ':' not in ip:  # Skip localhost and IPv6
                    ip_addresses.append(ip)
            print(f"Debug: Found IP addresses: {ip_addresses}")
        except Exception as e:
            ip_addresses = ["Unable to determine IP addresses"]
            print(f"Error: Could not determine IP addresses: {e}")
        
        # Display URLs for all available interfaces
        print("\nServer web interface is now running at:")
        print(f"Local access:     http://localhost:{port}")
        for ip in ip_addresses:
            print(f"Network access:   http://{ip}:{port}")
        print("\nDefault login credentials:")
        print("Username: admin")
        print("Password: admin")
        print("\nPress Ctrl+C to stop the server.\n")
        
        # Start the server
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server web interface stopped by user")
        print("\nServer web interface stopped by user")
    except Exception as e:
        logger.error(f"Failed to start server web interface: {e}")
        print(f"Error: Failed to start server web interface: {e}")
        # Try to clean up
        try:
            server.server_close()
        except:
            pass

def main():
    """Parse arguments and start server web interface"""
    parser = argparse.ArgumentParser(description='Lin-Win-Backup Server Web Interface')
    parser.add_argument('--clients-dir', help='Clients directory to monitor')
    parser.add_argument('--port', type=int, default=3001, help='Port to run the server web interface on (default: 3001)')
    parser.add_argument('--no-browser', action='store_true', help='Do not open browser automatically')
    
    args = parser.parse_args()
    
    # Configure logging
    log_dir = os.path.expanduser("~/Lin-Win-Backup/logs")
    os.makedirs(log_dir, exist_ok=True)
    logger.add(os.path.join(log_dir, "server_web_interface.log"), rotation="1 day", retention="7 days")
    
    # Start server web interface
    run_server_web_interface(
        clients_dir=args.clients_dir,
        port=args.port,
        open_browser=not args.no_browser
    )

if __name__ == "__main__":
    main() 