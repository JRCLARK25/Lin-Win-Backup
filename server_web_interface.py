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
import requests

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
        .add-client-form {
            margin-top: 20px;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 5px;
            display: none;
        }
        .add-client-btn {
            background-color: #28a745;
            color: white;
            padding: 8px 15px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin-bottom: 20px;
        }
        .form-row {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        .form-group {
            flex: 1;
        }
        .backup-control {
            margin-top: 20px;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 5px;
        }
        
        .backup-control h3 {
            margin-top: 0;
            margin-bottom: 15px;
        }
        
        .backup-buttons {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .backup-button {
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            transition: background-color 0.2s;
        }
        
        .backup-button.full {
            background-color: #007bff;
            color: white;
        }
        
        .backup-button.incremental {
            background-color: #28a745;
            color: white;
        }
        
        .backup-button.directory {
            background-color: #17a2b8;
            color: white;
        }
        
        .backup-button:hover {
            opacity: 0.9;
        }
        
        .directory-input {
            display: none;
            margin-top: 10px;
        }
        
        .directory-input input {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin-bottom: 10px;
        }
        
        .directory-input button {
            padding: 8px 15px;
            background-color: #28a745;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        
        .error-message {
            color: #dc3545;
            margin-top: 10px;
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Lin-Win-Backup Server Dashboard</h1>
            <button class="logout-btn" onclick="handleLogout()">Logout</button>
        </div>
        
        <button class="add-client-btn" onclick="showAddClientForm()">Add New Client</button>
        
        <div id="add-client-form" class="add-client-form">
            <h3>Add New Client</h3>
            <form onsubmit="return handleAddClient(event)">
                <div class="form-row">
                    <div class="form-group">
                        <label for="client-ip">Client IP Address:</label>
                        <input type="text" id="client-ip" required pattern="^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$" placeholder="192.168.1.100">
                    </div>
                    <div class="form-group">
                        <label for="client-name">Friendly Name (optional):</label>
                        <input type="text" id="client-name" placeholder="e.g., Office PC">
                    </div>
                </div>
                <button type="submit" class="btn btn-success">Add Client</button>
                <button type="button" class="btn btn-danger" onclick="hideAddClientForm()">Cancel</button>
            </form>
        </div>
        
        <div class="client-selector">
            <label for="client-select">Select Client:</label>
            <select id="client-select" onchange="loadClientData()">
                <option value="">Select a client...</option>
            </select>
        </div>
        
        <div id="client-data" style="display: none;">
            <div class="status-card">
                <h2>Client Status</h2>
                <p><strong>Hostname:</strong> <span id="hostname">-</span></p>
                <p><strong>System:</strong> <span id="system">-</span></p>
                <p><strong>Status:</strong> <span id="status">-</span></p>
                <p><strong>Last Seen:</strong> <span id="last-seen">-</span></p>
            </div>
            
            <div class="backup-control">
                <h3>Backup Control</h3>
                <div class="backup-buttons">
                    <button class="backup-button full" onclick="startBackup('full')">Start Full Backup</button>
                    <button class="backup-button incremental" onclick="startBackup('incremental')">Start Incremental Backup</button>
                    <button class="backup-button directory" onclick="showDirectoryInput()">Start Directory Backup</button>
                </div>
                
                <div id="directory-input" class="directory-input">
                    <input type="text" id="source-dir" placeholder="Enter directory path">
                    <button onclick="startDirectoryBackup()">Start Backup</button>
                </div>
                
                <div id="error-message" class="error-message"></div>
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
                updateStatusBadge(document.getElementById('status'), data.status || 'Unknown');
                document.getElementById('last-seen').textContent = formatDate(data.last_seen);
                
                updateCurrentBackup(data.current_backup);
                updateScheduleInfo(data.next_scheduled);
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
            
            if (!schedule) {
                element.innerHTML = '<p>No scheduled backups</p>';
                return;
            }
            
            element.innerHTML = `
                <p><strong>Type:</strong> ${schedule.type}</p>
                <p><strong>Scheduled Time:</strong> ${formatDate(schedule.time)}</p>
                <p><strong>Source:</strong> ${schedule.source}</p>
                <p><strong>Destination:</strong> ${schedule.destination}</p>
            `;
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
        
        function showAddClientForm() {
            document.getElementById('add-client-form').style.display = 'block';
        }
        
        function hideAddClientForm() {
            document.getElementById('add-client-form').style.display = 'none';
            document.getElementById('client-ip').value = '';
            document.getElementById('client-name').value = '';
        }
        
        async function handleAddClient(event) {
            event.preventDefault();
            
            const ip = document.getElementById('client-ip').value;
            const friendlyName = document.getElementById('client-name').value;
            
            try {
                const response = await fetch('/api/add_client', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        ip: ip,
                        friendly_name: friendlyName
                    }),
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    hideAddClientForm();
                    loadClients(); // Refresh the client list
                    alert('Client added successfully!');
                } else {
                    alert(data.error || 'Failed to add client');
                }
            } catch (error) {
                console.error('Error adding client:', error);
                alert('An error occurred while adding the client');
            }
            
            return false;
        }
        
        function showDirectoryInput() {
            document.getElementById('directory-input').style.display = 'block';
        }
        
        function startBackup(type) {
            const clientId = document.getElementById('client-select').value;
            if (!clientId) {
                showError('Please select a client first');
                return;
            }
            
            fetch(`/api/client/${clientId}/backup/start`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ type: type })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showError(data.error);
                } else {
                    hideError();
                    loadClientData();
                }
            })
            .catch(error => {
                showError('Failed to start backup: ' + error);
            });
        }
        
        function startDirectoryBackup() {
            const clientId = document.getElementById('client-select').value;
            const sourceDir = document.getElementById('source-dir').value;
            
            if (!clientId) {
                showError('Please select a client first');
                return;
            }
            
            if (!sourceDir) {
                showError('Please enter a directory path');
                return;
            }
            
            fetch(`/api/client/${clientId}/backup/start`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    type: 'directory',
                    source_dir: sourceDir
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showError(data.error);
                } else {
                    hideError();
                    document.getElementById('directory-input').style.display = 'none';
                    document.getElementById('source-dir').value = '';
                    loadClientData();
                }
            })
            .catch(error => {
                showError('Failed to start backup: ' + error);
            });
        }
        
        function showError(message) {
            const errorElement = document.getElementById('error-message');
            errorElement.textContent = message;
            errorElement.style.display = 'block';
        }
        
        function hideError() {
            document.getElementById('error-message').style.display = 'none';
        }
        
        // Initial load
        loadClients();
    </script>
</body>
</html>
"""

class ServerAPIHandler(http.server.SimpleHTTPRequestHandler):
    encryption = None  # Class variable to store the encryption manager
    users_file = os.path.expanduser('~/Lin-Win-Backup/clients/users.json')
    
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
            if not self._check_auth():
                self._redirect_to_login()
                return
            self._serve_dashboard_page()
        # API endpoints
        elif path == '/api/public_key':
            self._handle_public_key()
        elif path == '/api/clients':
            if not self._check_auth():
                self._send_error(401, "Unauthorized")
                return
            self._handle_get_clients()
        elif path.startswith('/api/client/'):
            if not self._check_auth():
                self._send_error(401, "Unauthorized")
                return
            client_id = path.split('/')[3]
            if path.endswith('/status'):
                self._handle_client_status(client_id)
            elif path.endswith('/schedule'):
                self._handle_client_schedule(client_id)
            else:
                self._handle_get_client(client_id)
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
        
        # Handle empty request body
        if not body:
            if path == '/logout':
                self._handle_logout()
                return
            self._send_error(400, "Empty request body")
            return
            
        try:
            data = json.loads(body.decode())
        except json.JSONDecodeError:
            self._send_error(400, "Invalid JSON in request body")
            return
        
        # Handle login
        if path == '/login':
            self._handle_login(data)
            return
        
        # API endpoints
        if path == '/api/register_client':
            self._handle_register_client(data)
        elif path == '/api/add_client':
            if not self._check_auth():
                self._send_error(401, "Unauthorized")
                return
            self._handle_add_client(data)
        elif path == '/api/register_client_key':
            if not self._check_auth():
                return
            
            try:
                data = json.loads(body)
                client_id = data.get('client_id')
                public_key = data.get('public_key')
                
                if not client_id or not public_key:
                    self._send_json_response({'error': 'Missing client_id or public_key'}, 400)
                    return
                
                # Store the client's public key
                keys_dir = os.path.expanduser('~/Lin-Win-Backup/keys/clients')
                os.makedirs(keys_dir, exist_ok=True)
                
                key_file = os.path.join(keys_dir, f'{client_id}.pub')
                with open(key_file, 'w') as f:
                    f.write(public_key)
                
                self._send_json_response({'status': 'success'})
                
            except Exception as e:
                self._send_json_response({'error': str(e)}, 500)
                return
        elif path.startswith('/api/client/'):
            if not self._check_auth():
                self._send_error(401, "Unauthorized")
                return
            client_id = path.split('/')[3]
            if path.endswith('/status'):
                self._handle_client_status_update(client_id, data)
            elif path.endswith('/backup/result'):
                self._handle_backup_result(client_id, data)
            elif path.endswith('/backup/start'):
                self._handle_start_backup(client_id, data)
            else:
                self._send_error(404, "Not found")
        else:
            self._send_error(404, "Not found")
    
    def _check_auth(self):
        """Check if user is authenticated"""
        if 'Cookie' not in self.headers:
            return False
        
        auth_cookie = self.headers['Cookie']
        if not auth_cookie.startswith('auth_token='):
            return False
        
        token = auth_cookie.split('=')[1].split(';')[0]
        return self._verify_token(token)
    
    def _verify_token(self, token):
        """Verify authentication token"""
        try:
            with open(self.users_file, 'r') as f:
                users = json.load(f)
                return any(user.get('token') == token for user in users)
        except:
            return False
    
    def _redirect_to_login(self):
        """Redirect to login page"""
        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()
    
    def _handle_login(self, data):
        """Handle login request"""
        username = data.get('username')
        password = data.get('password')
        
        try:
            with open(self.users_file, 'r') as f:
                users = json.load(f)
            
            user = next((u for u in users if u['username'] == username), None)
            
            if user and self._verify_password(password, user['password']):
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
    
    def _handle_logout(self):
        """Handle logout request"""
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
    
    def _verify_password(self, password, hashed_password):
        """Verify password against hash"""
        return hashlib.sha256(password.encode()).hexdigest() == hashed_password
    
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
            # Update client info
            clients_file = os.path.expanduser('~/Lin-Win-Backup/clients/clients.json')
            with open(clients_file, 'r') as f:
                clients = json.load(f)
            
            if client_id not in clients:
                self._send_error(404, "Client not found")
                return
            
            # Update client status
            clients[client_id].update({
                'last_seen': datetime.now().isoformat(),
                'current_backup': data.get('current_backup'),
                'system': data.get('system'),
                'version': data.get('version'),
                'hostname': data.get('hostname')
            })
            
            with open(clients_file, 'w') as f:
                json.dump(clients, f, indent=2)
            
            self._send_json_response({'status': 'success'})
        except Exception as e:
            logger.error(f"Error updating client status: {str(e)}")
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
    
    def _handle_backup_result(self, client_id, data):
        """Handle backup result report"""
        try:
            # Update client info
            clients_file = os.path.expanduser('~/Lin-Win-Backup/clients/clients.json')
            with open(clients_file, 'r') as f:
                clients = json.load(f)
            
            if client_id not in clients:
                self._send_error(404, "Client not found")
                return
            
            # Add to backup history
            backup_result = data.get('backup_result')
            if backup_result:
                if 'backup_history' not in clients[client_id]:
                    clients[client_id]['backup_history'] = []
                clients[client_id]['backup_history'].append(backup_result)
                # Keep only last 10 backups
                clients[client_id]['backup_history'] = clients[client_id]['backup_history'][-10:]
            
            # Clear current backup if this was the one in progress
            if (clients[client_id].get('current_backup', {}).get('start_time') == 
                backup_result.get('start_time')):
                clients[client_id]['current_backup'] = None
            
            with open(clients_file, 'w') as f:
                json.dump(clients, f, indent=2)
            
            self._send_json_response({'status': 'success'})
        except Exception as e:
            logger.error(f"Error handling backup result: {str(e)}")
            self._send_error(500, str(e))
    
    def _handle_start_backup(self, client_id, data):
        """Handle request to start a backup on a client"""
        try:
            # Validate backup type
            backup_type = data.get('type')
            if backup_type not in ['full', 'incremental', 'directory']:
                return self._send_json_response({'error': 'Invalid backup type'}, 400)
            
            # Validate source directory for directory backup
            source_dir = data.get('source_dir')
            if backup_type == 'directory' and not source_dir:
                return self._send_json_response({'error': 'Source directory required for directory backup'}, 400)
            
            # Load client info
            clients_file = os.path.expanduser('~/Lin-Win-Backup/clients/clients.json')
            with open(clients_file, 'r') as f:
                clients = json.load(f)
            
            if client_id not in clients:
                return self._send_json_response({'error': 'Client not found'}, 404)
            
            # Check if client is already running a backup
            if clients[client_id].get('current_backup'):
                return self._send_json_response({'error': 'Client is already running a backup'}, 400)
            
            # Prepare backup request
            backup_request = {
                'type': backup_type,
                'source_dir': source_dir if backup_type == 'directory' else None,
                'start_time': datetime.now().isoformat()
            }
            
            # Update client status
            clients[client_id]['current_backup'] = backup_request
            
            # Save updated client info
            with open(clients_file, 'w') as f:
                json.dump(clients, f, indent=2)
            
            # Send backup request to client
            response = requests.post(
                f"{clients[client_id]['server_url']}/api/backup/start",
                json=backup_request,
                headers={'Authorization': f'Bearer {clients[client_id]["auth_token"]}'}
            )
            
            if response.status_code == 200:
                return self._send_json_response({'status': 'success', 'message': 'Backup started'})
            else:
                # Revert client status if backup start failed
                clients[client_id]['current_backup'] = None
                with open(clients_file, 'w') as f:
                    json.dump(clients, f, indent=2)
                return self._send_json_response({'error': 'Failed to start backup on client'}, 500)
            
        except Exception as e:
            logger.error(f"Error starting backup: {str(e)}")
            return self._send_json_response({'error': str(e)}, 500)
    
    def _send_json_response(self, data, status_code=200):
        """Send JSON response with optional status code"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
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
    
    def _handle_get_clients(self):
        """Handle request to get all clients"""
        try:
            clients_file = os.path.expanduser('~/Lin-Win-Backup/clients/clients.json')
            if not os.path.exists(clients_file):
                self._send_json_response([])
                return
            
            with open(clients_file, 'r') as f:
                clients = json.load(f)
            
            # Ensure clients is a dictionary
            if not isinstance(clients, dict):
                clients = {}
                # Save empty dictionary if file was corrupted
                with open(clients_file, 'w') as f:
                    json.dump(clients, f, indent=2)
            
            # Convert clients dict to list with id field
            clients_list = []
            for client_id, client_data in clients.items():
                client_data['id'] = client_id
                clients_list.append(client_data)
            
            self._send_json_response(clients_list)
        except Exception as e:
            logger.error(f"Error getting clients: {str(e)}")
            self._send_error(500, str(e))
    
    def _handle_get_client(self, client_id):
        """Handle request to get a specific client"""
        try:
            clients_file = os.path.expanduser('~/Lin-Win-Backup/clients/clients.json')
            if not os.path.exists(clients_file):
                self._send_error(404, "Client not found")
                return
            
            with open(clients_file, 'r') as f:
                clients = json.load(f)
            
            # Ensure clients is a dictionary
            if not isinstance(clients, dict):
                clients = {}
                # Save empty dictionary if file was corrupted
                with open(clients_file, 'w') as f:
                    json.dump(clients, f, indent=2)
            
            if client_id not in clients:
                self._send_error(404, "Client not found")
                return
            
            client_data = clients[client_id]
            client_data['id'] = client_id
            self._send_json_response(client_data)
        except Exception as e:
            logger.error(f"Error getting client {client_id}: {str(e)}")
            self._send_error(500, str(e))

    def _handle_add_client(self, data):
        """Handle adding a new client"""
        try:
            ip = data.get('ip')
            friendly_name = data.get('friendly_name')
            
            if not ip:
                return self._send_json_response({'error': 'IP address is required'}, 400)
            
            # Validate IP address
            try:
                socket.inet_aton(ip)
            except socket.error:
                return self._send_json_response({'error': 'Invalid IP address'}, 400)
            
            # Try to resolve hostname
            try:
                hostname = socket.gethostbyaddr(ip)[0]
            except socket.herror:
                hostname = ip
            
            # Generate a unique client ID
            client_id = hashlib.sha256(f"{ip}{hostname}".encode()).hexdigest()[:12]
            
            # Load existing clients
            clients_file = os.path.expanduser('~/Lin-Win-Backup/clients/clients.json')
            os.makedirs(os.path.dirname(clients_file), exist_ok=True)
            
            clients = {}  # Default to empty dictionary
            if os.path.exists(clients_file):
                try:
                    with open(clients_file, 'r') as f:
                        loaded_clients = json.load(f)
                        # Ensure loaded data is a dictionary
                        if isinstance(loaded_clients, dict):
                            clients = loaded_clients
                        else:
                            logger.warning(f"Corrupted clients file found. Resetting to empty dictionary.")
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in clients file. Resetting to empty dictionary.")
            
            # Check if client already exists
            if client_id in clients:
                return self._send_json_response({'error': 'Client already exists'}, 400)
            
            # Add new client
            clients[client_id] = {
                'ip': ip,
                'hostname': hostname,
                'friendly_name': friendly_name,
                'status': 'Unknown',
                'system': 'Unknown',
                'version': 'Unknown',
                'last_seen': None,
                'current_backup': None,
                'schedules': []
            }
            
            # Save updated clients
            with open(clients_file, 'w') as f:
                json.dump(clients, f, indent=2)
            
            # Generate a temporary token for initial key exchange
            temp_token = secrets.token_urlsafe(32)
            temp_token_file = os.path.join(os.path.dirname(clients_file), f'{client_id}.token')
            with open(temp_token_file, 'w') as f:
                f.write(temp_token)
            
            logger.info(f"Added new client: {client_id} ({ip})")
            return self._send_json_response({
                'status': 'success',
                'client_id': client_id,
                'temp_token': temp_token
            })
            
        except Exception as e:
            logger.error(f"Error adding client: {str(e)}")
            return self._send_json_response({'error': str(e)}, 500)

def run_server(port=3000):
    """Run the server"""
    # Create necessary directories
    os.makedirs(os.path.expanduser('~/Lin-Win-Backup/clients'), exist_ok=True)
    os.makedirs(os.path.expanduser('~/Lin-Win-Backup/keys/server'), exist_ok=True)
    
    # Create users file if it doesn't exist
    users_file = os.path.expanduser('~/Lin-Win-Backup/clients/users.json')
    if not os.path.exists(users_file):
        # Create default admin user
        default_users = [
            {
                "username": "admin",
                "password": hashlib.sha256("admin".encode()).hexdigest(),
                "role": "admin"
            }
        ]
        with open(users_file, 'w') as f:
            json.dump(default_users, f, indent=2)
    
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