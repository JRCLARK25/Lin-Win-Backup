#!/usr/bin/env python3
import os
import sys
import time
import json
import signal
import platform
import subprocess
import threading
import schedule
import psutil
from pathlib import Path
from datetime import datetime
from loguru import logger
import socket
import http.server
import socketserver
import webbrowser
from config import SCHEDULE_CONFIG, BACKUP_CONFIG, LOG_CONFIG

class BackupAgent:
    def __init__(self, backup_dir=None):
        self.system = platform.system()
        self.hostname = socket.gethostname()
        self.backup_dir = Path(backup_dir) if backup_dir else Path(BACKUP_CONFIG.get('backup_dir', '~/Lin-Win-Backup'))
        self.status_file = self.backup_dir / 'agent_status.json'
        self.running = True
        self.current_backup = None
        self.backup_history = []
        self.setup_logging()
        self.load_status()
        
    def setup_logging(self):
        """Setup logging for the agent"""
        log_dir = Path(LOG_CONFIG.get('log_dir', '~/Lin-Win-Backup/logs'))
        log_dir.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_dir / "agent.log",
            rotation=LOG_CONFIG.get('log_rotation', '1 day'),
            retention=LOG_CONFIG.get('log_retention', '7 days'),
            level=LOG_CONFIG.get('log_level', 'INFO')
        )
        
    def load_status(self):
        """Load agent status from file"""
        if self.status_file.exists():
            try:
                with open(self.status_file, 'r') as f:
                    data = json.load(f)
                    self.backup_history = data.get('backup_history', [])
            except Exception as e:
                logger.error(f"Failed to load status file: {e}")
                self.backup_history = []
                
    def save_status(self):
        """Save agent status to file"""
        try:
            status_data = {
                'hostname': self.hostname,
                'system': self.system,
                'last_updated': datetime.now().isoformat(),
                'current_backup': self.current_backup,
                'backup_history': self.backup_history[-10:],  # Keep last 10 backups
                'next_scheduled': self.get_next_scheduled()
            }
            
            with open(self.status_file, 'w') as f:
                json.dump(status_data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save status file: {e}")
            
    def schedule_backups(self):
        """Schedule backups based on configuration"""
        # Schedule full backup
        schedule.every().day.at(SCHEDULE_CONFIG['full_backup_time']).do(
            self.run_full_backup
        ).tag('full_backup')
        
        # Schedule incremental backups
        for time_str in SCHEDULE_CONFIG['incremental_backup_times']:
            schedule.every().day.at(time_str).do(
                self.run_incremental_backup
            ).tag('incremental_backup')
            
        logger.info("Backup schedules configured")
        
    def run_full_backup(self):
        """Run a full backup"""
        if self.current_backup:
            logger.warning("Backup already in progress, skipping scheduled full backup")
            return
            
        logger.info("Starting scheduled full backup")
        self.current_backup = {
            'type': 'full',
            'start_time': datetime.now().isoformat(),
            'status': 'running'
        }
        self.save_status()
        
        try:
            # Run the backup process
            cmd = [
                sys.executable, 
                'lin_win_backup.py',
                '--type', 'full',
                '--destination', str(self.backup_dir)
            ]
            
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                self.current_backup['status'] = 'completed'
                self.current_backup['end_time'] = datetime.now().isoformat()
                logger.info("Full backup completed successfully")
            else:
                self.current_backup['status'] = 'failed'
                self.current_backup['error'] = stderr
                logger.error(f"Full backup failed: {stderr}")
                
        except Exception as e:
            self.current_backup['status'] = 'failed'
            self.current_backup['error'] = str(e)
            logger.error(f"Full backup failed with exception: {e}")
            
        finally:
            self.backup_history.append(self.current_backup)
            self.current_backup = None
            self.save_status()
            
    def run_incremental_backup(self):
        """Run an incremental backup"""
        if self.current_backup:
            logger.warning("Backup already in progress, skipping scheduled incremental backup")
            return
            
        logger.info("Starting scheduled incremental backup")
        self.current_backup = {
            'type': 'incremental',
            'start_time': datetime.now().isoformat(),
            'status': 'running'
        }
        self.save_status()
        
        try:
            # Run the backup process
            cmd = [
                sys.executable, 
                'lin_win_backup.py',
                '--type', 'incremental',
                '--destination', str(self.backup_dir)
            ]
            
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                self.current_backup['status'] = 'completed'
                self.current_backup['end_time'] = datetime.now().isoformat()
                logger.info("Incremental backup completed successfully")
            else:
                self.current_backup['status'] = 'failed'
                self.current_backup['error'] = stderr
                logger.error(f"Incremental backup failed: {stderr}")
                
        except Exception as e:
            self.current_backup['status'] = 'failed'
            self.current_backup['error'] = str(e)
            logger.error(f"Incremental backup failed with exception: {e}")
            
        finally:
            self.backup_history.append(self.current_backup)
            self.current_backup = None
            self.save_status()
            
    def get_next_scheduled(self):
        """Get the next scheduled backup"""
        next_jobs = schedule.get_jobs()
        if not next_jobs:
            return None
            
        next_run = min(job.next_run for job in next_jobs)
        return {
            'time': next_run.isoformat(),
            'type': 'full' if 'full_backup' in str(next_run) else 'incremental'
        }
        
    def get_status(self):
        """Get current agent status"""
        return {
            'hostname': self.hostname,
            'system': self.system,
            'status': 'running' if self.running else 'stopped',
            'current_backup': self.current_backup,
            'last_backup': self.backup_history[-1] if self.backup_history else None,
            'next_scheduled': self.get_next_scheduled(),
            'disk_usage': self.get_disk_usage()
        }
        
    def get_disk_usage(self):
        """Get disk usage information"""
        usage = {}
        for partition in psutil.disk_partitions():
            try:
                partition_usage = psutil.disk_usage(partition.mountpoint)
                usage[partition.mountpoint] = {
                    'total': partition_usage.total,
                    'used': partition_usage.used,
                    'free': partition_usage.free,
                    'percent': partition_usage.percent
                }
            except Exception:
                continue
        return usage
        
    def run(self):
        """Run the agent"""
        logger.info(f"Starting backup agent on {self.hostname} ({self.system})")
        self.schedule_backups()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        
        # Start the status server
        status_server = threading.Thread(target=self.run_status_server)
        status_server.daemon = True
        status_server.start()
        
        # Main loop
        while self.running:
            schedule.run_pending()
            time.sleep(1)
            
    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("Shutdown signal received, stopping agent")
        self.running = False
        
    def run_status_server(self, port=8080):
        """Run a simple HTTP server to provide status information"""
        class StatusHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                self.agent = self
                super().__init__(*args, **kwargs)
                
            def do_GET(self):
                if self.path == '/status':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(self.agent.get_status()).encode())
                else:
                    self.send_response(404)
                    self.end_headers()
                    
        try:
            with socketserver.TCPServer(("", port), StatusHandler) as httpd:
                logger.info(f"Status server running on port {port}")
                httpd.serve_forever()
        except Exception as e:
            logger.error(f"Failed to start status server: {e}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Lin-Win-Backup Agent')
    parser.add_argument('--backup-dir', help='Backup directory path')
    parser.add_argument('--port', type=int, default=8080, help='Status server port')
    parser.add_argument('--open-browser', action='store_true', help='Open status page in browser')
    
    args = parser.parse_args()
    
    agent = BackupAgent(args.backup_dir)
    
    if args.open_browser:
        webbrowser.open(f'http://localhost:{args.port}/status')
        
    agent.run()

if __name__ == "__main__":
    main() 