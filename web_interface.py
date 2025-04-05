#!/usr/bin/env python3
import os
import sys
import json
import argparse
import http.server
import socketserver
import threading
import webbrowser
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger
import socket

# HTML template for the status page
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lin-Win-Backup Status</title>
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
        h1, h2 {
            color: #333;
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
        .disk-usage {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }
        .disk-card {
            background-color: #f9f9f9;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 10px;
            flex: 1;
            min-width: 200px;
        }
        .progress-bar {
            width: 100%;
            height: 20px;
            background-color: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            margin-top: 5px;
        }
        .progress-fill {
            height: 100%;
            background-color: #007bff;
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
        .refresh-button {
            background-color: #007bff;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
        }
        .refresh-button:hover {
            background-color: #0069d9;
        }
        .auto-refresh {
            margin-left: 10px;
            font-size: 14px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="status-header">
            <h1>Lin-Win-Backup Status</h1>
            <div>
                <button class="refresh-button" onclick="refreshStatus()">Refresh</button>
                <span class="auto-refresh">Auto-refresh: <span id="countdown">30</span>s</span>
            </div>
        </div>
        
        <div class="status-card">
            <h2>Agent Status</h2>
            <p><strong>Hostname:</strong> <span id="hostname">-</span></p>
            <p><strong>System:</strong> <span id="system">-</span></p>
            <p><strong>Status:</strong> <span id="agent-status" class="status-badge">-</span></p>
            <p><strong>Last Updated:</strong> <span id="last-updated">-</span></p>
        </div>
        
        <div class="status-card">
            <h2>Current Backup</h2>
            <div id="current-backup">
                <p>No backup in progress</p>
            </div>
        </div>
        
        <div class="status-card">
            <h2>Next Scheduled Backup</h2>
            <div id="next-scheduled">
                <p>No scheduled backups</p>
            </div>
        </div>
        
        <div class="status-card">
            <h2>Disk Usage</h2>
            <div id="disk-usage" class="disk-usage">
                <p>Loading disk usage information...</p>
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
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td colspan="4">No backup history available</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    
    <script>
        let countdown = 30;
        let countdownInterval;
        
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
        
        function updateDiskUsage(diskUsage) {
            const diskUsageElement = document.getElementById('disk-usage');
            diskUsageElement.innerHTML = '';
            
            for (const [mountpoint, usage] of Object.entries(diskUsage)) {
                const diskCard = document.createElement('div');
                diskCard.className = 'disk-card';
                
                const percent = usage.percent;
                const usedColor = percent > 90 ? '#dc3545' : percent > 70 ? '#ffc107' : '#007bff';
                
                diskCard.innerHTML = `
                    <h3>${mountpoint}</h3>
                    <p>Total: ${formatBytes(usage.total)}</p>
                    <p>Used: ${formatBytes(usage.used)} (${percent}%)</p>
                    <p>Free: ${formatBytes(usage.free)}</p>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${percent}%; background-color: ${usedColor};"></div>
                    </div>
                `;
                
                diskUsageElement.appendChild(diskCard);
            }
        }
        
        function updateBackupHistory(history) {
            const tbody = document.querySelector('#backup-history tbody');
            tbody.innerHTML = '';
            
            if (!history || history.length === 0) {
                const row = document.createElement('tr');
                row.innerHTML = '<td colspan="4">No backup history available</td>';
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
                `;
                tbody.appendChild(row);
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
                ${currentBackup.error ? `<p><strong>Error:</strong> ${currentBackup.error}</p>` : ''}
            `;
        }
        
        function updateNextScheduled(nextScheduled) {
            const element = document.getElementById('next-scheduled');
            
            if (!nextScheduled) {
                element.innerHTML = '<p>No scheduled backups</p>';
                return;
            }
            
            element.innerHTML = `
                <p><strong>Type:</strong> ${nextScheduled.type}</p>
                <p><strong>Time:</strong> ${formatDate(nextScheduled.time)}</p>
            `;
        }
        
        function refreshStatus() {
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('hostname').textContent = data.hostname;
                    document.getElementById('system').textContent = data.system;
                    updateStatusBadge(document.getElementById('agent-status'), data.status);
                    document.getElementById('last-updated').textContent = formatDate(new Date());
                    
                    updateCurrentBackup(data.current_backup);
                    updateNextScheduled(data.next_scheduled);
                    updateDiskUsage(data.disk_usage);
                    
                    if (data.backup_history) {
                        updateBackupHistory(data.backup_history);
                    }
                    
                    // Reset countdown
                    countdown = 30;
                })
                .catch(error => {
                    console.error('Error fetching status:', error);
                });
        }
        
        function startCountdown() {
            countdownInterval = setInterval(() => {
                countdown--;
                document.getElementById('countdown').textContent = countdown;
                
                if (countdown <= 0) {
                    refreshStatus();
                    countdown = 30;
                }
            }, 1000);
        }
        
        // Initial load
        refreshStatus();
        startCountdown();
    </script>
</body>
</html>
"""

class StatusHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.status_file = kwargs.pop('status_file', None)
        super().__init__(*args, **kwargs)
        
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode())
        elif self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')  # Allow cross-origin requests
            self.end_headers()
            
            print(f"\nDebug: Handling /status request")
            print(f"Debug: Status file path: {self.status_file}")
            
            if not self.status_file:
                error_msg = {'error': 'Status file path not configured'}
                print(f"Debug: {error_msg}")
                self.wfile.write(json.dumps(error_msg).encode())
                return
                
            if not self.status_file.exists():
                error_msg = {'error': f'Status file not found at {self.status_file}'}
                print(f"Debug: {error_msg}")
                self.wfile.write(json.dumps(error_msg).encode())
                return
                
            try:
                print(f"Debug: Reading status file")
                with open(self.status_file, 'r') as f:
                    status_data = json.load(f)
                print(f"Debug: Successfully read status data: {json.dumps(status_data, indent=2)}")
                self.wfile.write(json.dumps(status_data).encode())
            except json.JSONDecodeError as e:
                error_msg = {'error': f'Invalid JSON in status file: {str(e)}'}
                print(f"Debug: {error_msg}")
                self.wfile.write(json.dumps(error_msg).encode())
            except Exception as e:
                error_msg = {'error': f'Error reading status file: {str(e)}'}
                print(f"Debug: {error_msg}")
                self.wfile.write(json.dumps(error_msg).encode())
        else:
            self.send_response(404)
            self.end_headers()

def run_web_interface(backup_dir=None, port=3000, open_browser=True):
    """Run the web interface server"""
    global backup_directory
    backup_directory = backup_dir or os.path.expanduser("~/Lin-Win-Backup/backups")
    
    print(f"\nDebug: Using backup directory: {backup_directory}")
    
    # Ensure backup directory exists
    if not os.path.exists(backup_directory):
        try:
            os.makedirs(backup_directory, exist_ok=True)
            print(f"Debug: Created backup directory: {backup_directory}")
        except Exception as e:
            print(f"Error: Failed to create backup directory: {e}")
            return
    
    # Set up status handler
    class CustomStatusHandler(StatusHandler):
        def __init__(self, *args, **kwargs):
            self.status_file = Path(backup_directory) / 'agent_status.json'
            print(f"\nDebug: Initializing CustomStatusHandler")
            print(f"Debug: Status file path: {self.status_file}")
            
            if not self.status_file.exists():
                print(f"Debug: Status file does not exist, creating sample file")
                # Create a sample status file if it doesn't exist
                sample_status = {
                    "hostname": socket.gethostname(),
                    "system": "Linux",
                    "status": "idle",
                    "current_backup": {
                        "type": "directory",
                        "start_time": datetime.now().isoformat(),
                        "status": "in_progress",
                        "progress": 45,
                        "eta": "2 minutes",
                        "source": "/home/puppy/test",
                        "destination": "/home/puppy/Lin-Win-Backup/backups"
                    },
                    "next_scheduled": {
                        "type": "incremental",
                        "time": (datetime.now() + timedelta(hours=1)).isoformat(),
                        "source": "/home/puppy/test",
                        "destination": "/home/puppy/Lin-Win-Backup/backups"
                    },
                    "disk_usage": {
                        "/": {"total": 100000000000, "used": 50000000000, "free": 50000000000, "percent": 50},
                        "/home": {"total": 500000000000, "used": 200000000000, "free": 300000000000, "percent": 40}
                    },
                    "backup_history": [
                        {
                            "type": "full",
                            "start_time": (datetime.now() - timedelta(days=1)).isoformat(),
                            "end_time": (datetime.now() - timedelta(days=1, hours=-1)).isoformat(),
                            "status": "completed",
                            "size": 1500000000,
                            "files": 150
                        },
                        {
                            "type": "incremental",
                            "start_time": (datetime.now() - timedelta(hours=12)).isoformat(),
                            "end_time": (datetime.now() - timedelta(hours=11, minutes=45)).isoformat(),
                            "status": "completed",
                            "size": 500000000,
                            "files": 50
                        },
                        {
                            "type": "directory",
                            "start_time": (datetime.now() - timedelta(hours=6)).isoformat(),
                            "end_time": (datetime.now() - timedelta(hours=5, minutes=30)).isoformat(),
                            "status": "completed",
                            "size": 800000000,
                            "files": 80
                        }
                    ]
                }
                try:
                    with open(self.status_file, 'w') as f:
                        json.dump(sample_status, f, indent=2)
                    print(f"Debug: Created sample status file at {self.status_file}")
                    # Verify the file was created and is readable
                    with open(self.status_file, 'r') as f:
                        json.load(f)
                    print(f"Debug: Verified status file is readable and contains valid JSON")
                except Exception as e:
                    print(f"Error: Failed to create/verify sample status file: {e}")
            else:
                print(f"Debug: Status file exists at {self.status_file}")
                try:
                    with open(self.status_file, 'r') as f:
                        json.load(f)
                    print(f"Debug: Verified existing status file is readable and contains valid JSON")
                except Exception as e:
                    print(f"Error: Existing status file is invalid: {e}")
            
            super().__init__(*args, status_file=self.status_file)
    
    try:
        # Allow connections from any IP address by binding to 0.0.0.0
        server = socketserver.TCPServer(("0.0.0.0", port), CustomStatusHandler)
        server.allow_reuse_address = True  # Add this line to allow port reuse
        
        logger.info(f"Starting web interface on port {port}")
        print(f"\nDebug: Starting web interface on port {port}")
        
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
        print("\nWeb interface is now running at:")
        print(f"Local access:     http://localhost:{port}")
        for ip in ip_addresses:
            print(f"Network access:   http://{ip}:{port}")
        print("\nPress Ctrl+C to stop the server.\n")
        
        # Open browser if requested and running locally
        if open_browser:
            threading.Thread(target=lambda: webbrowser.open(f"http://localhost:{port}")).start()
        
        # Start the server
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Web interface stopped by user")
        print("\nWeb interface stopped by user")
    except Exception as e:
        logger.error(f"Failed to start web interface: {e}")
        print(f"Error: Failed to start web interface: {e}")
        # Try to clean up
        try:
            server.server_close()
        except:
            pass

def main():
    """Parse arguments and start web interface"""
    parser = argparse.ArgumentParser(description='Lin-Win-Backup Web Interface')
    parser.add_argument('--backup-dir', help='Backup directory to monitor')
    parser.add_argument('--port', type=int, default=3000, help='Port to run the web interface on (default: 3000)')
    parser.add_argument('--no-browser', action='store_true', help='Do not open browser automatically')
    
    args = parser.parse_args()
    
    # Configure logging
    log_dir = os.path.expanduser("~/Lin-Win-Backup/logs")
    os.makedirs(log_dir, exist_ok=True)
    logger.add(os.path.join(log_dir, "web_interface.log"), rotation="1 day", retention="7 days")
    
    # Start web interface
    run_web_interface(
        backup_dir=args.backup_dir,
        port=args.port,
        open_browser=not args.no_browser
    )

if __name__ == "__main__":
    main() 