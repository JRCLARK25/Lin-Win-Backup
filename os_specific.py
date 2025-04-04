import os
import platform
import shutil
from pathlib import Path
import subprocess
from loguru import logger

class OSBackupOperations:
    @staticmethod
    def backup_linux_partition(partition, backup_dir):
        """Backup a Linux partition"""
        try:
            # Use rsync for efficient backup
            cmd = [
                'rsync',
                '-av',
                '--exclude', '/proc',
                '--exclude', '/sys',
                '--exclude', '/dev',
                '--exclude', '/run',
                '--exclude', '/tmp',
                partition.mountpoint,
                str(backup_dir)
            ]
            subprocess.run(cmd, check=True)
            logger.info(f"Successfully backed up partition {partition.mountpoint}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to backup partition {partition.mountpoint}: {e}")
            raise

    @staticmethod
    def backup_windows_partition(partition, backup_dir):
        """Backup a Windows partition"""
        try:
            # Use robocopy for Windows backup
            cmd = [
                'robocopy',
                partition.mountpoint,
                str(backup_dir),
                '/MIR',  # Mirror mode
                '/Z',    # Restart mode
                '/R:3',  # Retry 3 times
                '/W:5',  # Wait 5 seconds between retries
                '/XF',   # Exclude files
                'pagefile.sys',
                'hiberfil.sys',
                'swapfile.sys'
            ]
            subprocess.run(cmd, check=True)
            logger.info(f"Successfully backed up partition {partition.mountpoint}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to backup partition {partition.mountpoint}: {e}")
            raise

    @staticmethod
    def add_linux_boot_files(iso):
        """Add Linux boot files to ISO"""
        # Add bootloader files
        boot_dir = '/boot'
        if os.path.exists(boot_dir):
            for root, dirs, files in os.walk(boot_dir):
                for file in files:
                    if file.endswith(('.img', '.efi', 'vmlinuz')):
                        src_path = os.path.join(root, file)
                        iso_path = f'/boot/{os.path.relpath(src_path, boot_dir)}'
                        iso.add_file(src_path, iso_path=iso_path)

    @staticmethod
    def add_windows_boot_files(iso):
        """Add Windows boot files to ISO"""
        # Add Windows boot files
        boot_files = [
            'bootmgr',
            'bootmgr.efi',
            'boot/bcd',
            'boot/boot.sdi',
            'boot/boot.wim'
        ]
        
        windows_dir = 'C:\\Windows\\Boot'
        for boot_file in boot_files:
            src_path = os.path.join(windows_dir, boot_file)
            if os.path.exists(src_path):
                iso.add_file(src_path, iso_path=f'/boot/{boot_file}')

    @staticmethod
    def get_system_info():
        """Get system information"""
        info = {
            'os': platform.system(),
            'version': platform.version(),
            'architecture': platform.machine(),
            'processor': platform.processor(),
            'hostname': platform.node()
        }
        return info

    @staticmethod
    def verify_backup(source_path, backup_path):
        """Verify backup integrity"""
        if platform.system() == "Linux":
            # Use diff for Linux
            cmd = ['diff', '-r', source_path, backup_path]
        else:
            # Use fc for Windows
            cmd = ['fc', '/b', source_path, backup_path]
            
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False 