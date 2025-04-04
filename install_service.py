#!/usr/bin/env python3
import os
import sys
import platform
import subprocess
import argparse
from pathlib import Path
from loguru import logger

def install_linux_service(backup_dir=None, port=8080):
    """Install the backup agent as a systemd service on Linux"""
    try:
        # Get the absolute path to the agent script
        script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        agent_script = script_dir / 'agent.py'
        
        # Create service file content
        service_content = f"""[Unit]
Description=Lin-Win-Backup Agent
After=network.target

[Service]
Type=simple
User=root
ExecStart={sys.executable} {agent_script} --backup-dir {backup_dir or '~/Lin-Win-Backup'} --port {port}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
        
        # Write service file
        service_path = Path('/etc/systemd/system/lin-win-backup-agent.service')
        with open(service_path, 'w') as f:
            f.write(service_content)
            
        # Reload systemd
        subprocess.run(['systemctl', 'daemon-reload'], check=True)
        
        # Enable and start the service
        subprocess.run(['systemctl', 'enable', 'lin-win-backup-agent.service'], check=True)
        subprocess.run(['systemctl', 'start', 'lin-win-backup-agent.service'], check=True)
        
        logger.info("Linux service installed and started successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to install Linux service: {e}")
        return False

def install_windows_service(backup_dir=None, port=8080):
    """Install the backup agent as a Windows service"""
    try:
        import win32serviceutil
        import win32service
        import win32event
        import servicemanager
        import socket
        import sys
        
        # Get the absolute path to the agent script
        script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        agent_script = script_dir / 'agent.py'
        
        class BackupAgentService(win32serviceutil.ServiceFramework):
            _svc_name_ = "LinWinBackupAgent"
            _svc_display_name_ = "Lin-Win-Backup Agent"
            _svc_description_ = "Provides backup scheduling and monitoring for Lin-Win-Backup"
            
            def __init__(self, args):
                win32serviceutil.ServiceFramework.__init__(self, args)
                self.stop_event = win32event.CreateEvent(None, 0, 0, None)
                socket.setdefaulttimeout(60)
                
            def SvcStop(self):
                self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
                win32event.SetEvent(self.stop_event)
                
            def SvcDoRun(self):
                try:
                    servicemanager.LogMsg(
                        servicemanager.EVENTLOG_INFORMATION_TYPE,
                        servicemanager.PYS_SERVICE_STARTED,
                        (self._svc_name_, '')
                    )
                    
                    # Run the agent
                    cmd = [
                        sys.executable,
                        str(agent_script),
                        '--backup-dir', backup_dir or '~/Lin-Win-Backup',
                        '--port', str(port)
                    ]
                    
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    
                    # Wait for the stop event
                    while True:
                        rc = win32event.WaitForSingleObject(self.stop_event, 1000)
                        if rc == win32event.WAIT_OBJECT_0:
                            break
                            
                        # Check if process is still running
                        if process.poll() is not None:
                            break
                            
                    # Terminate the process if it's still running
                    if process.poll() is None:
                        process.terminate()
                        process.wait(timeout=5)
                        
                except Exception as e:
                    servicemanager.LogErrorMsg(f"Service error: {e}")
                    
        if len(sys.argv) == 1:
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(BackupAgentService)
            servicemanager.StartServiceCtrlDispatcher()
        else:
            win32serviceutil.HandleCommandLine(BackupAgentService)
            
        logger.info("Windows service installed and started successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to install Windows service: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Install Lin-Win-Backup Agent as a system service')
    parser.add_argument('--backup-dir', help='Backup directory path')
    parser.add_argument('--port', type=int, default=8080, help='Status server port')
    
    args = parser.parse_args()
    
    system = platform.system()
    
    if system == 'Linux':
        # Check if running as root
        if os.geteuid() != 0:
            logger.error("Linux service installation requires root privileges")
            sys.exit(1)
            
        success = install_linux_service(args.backup_dir, args.port)
    elif system == 'Windows':
        success = install_windows_service(args.backup_dir, args.port)
    else:
        logger.error(f"Unsupported operating system: {system}")
        sys.exit(1)
        
    if success:
        logger.info(f"Lin-Win-Backup Agent service installed successfully on {system}")
        sys.exit(0)
    else:
        logger.error(f"Failed to install Lin-Win-Backup Agent service on {system}")
        sys.exit(1)

if __name__ == "__main__":
    main() 