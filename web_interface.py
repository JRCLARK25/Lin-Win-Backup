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
from datetime import datetime
from loguru import logger

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
            self.end_headers()
            
            if self.status_file and self.status_file.exists():
                try:
                    with open(self.status_file, 'r') as f:
                        status_data = json.load(f)
                    self.wfile.write(json.dumps(status_data).encode())
                except Exception as e:
                    self.wfile.write(json.dumps({'error': str(e)}).encode())
            else:
                self.wfile.write(json.dumps({'error': 'Status file not found'}).encode())
        else:
            self.send_response(404)
            self.end_headers()

def run_web_interface(backup_dir=None, port=3000, open_browser=True):
    """Run the web interface server"""
    global backup_directory
    backup_directory = backup_dir or os.path.expanduser("~/Lin-Win-Backup/backups")
    
    # Ensure backup directory exists
    if not os.path.exists(backup_directory):
        os.makedirs(backup_directory, exist_ok=True)
    
    # Set up status handler
    handler = StatusHandler
    
    try:
        # Create the server
        server = socketserver.TCPServer(("", port), handler)
        
        logger.info(f"Starting web interface on port {port}")
        print(f"Starting web interface on port {port}")
        
        # Display the URL with clickable link
        url = f"http://localhost:{port}"
        print(f"\nWeb interface is now running at: {url}")
        print(f"You can access it by clicking this link or copying it to your browser.")
        print(f"Press Ctrl+C to stop the server.\n")
        
        # Open browser if requested
        if open_browser:
            threading.Thread(target=lambda: webbrowser.open(url)).start()
        
        # Start the server
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Web interface stopped by user")
        print("\nWeb interface stopped by user")
    except Exception as e:
        logger.error(f"Failed to start web interface: {e}")
        print(f"Failed to start web interface: {e}")

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