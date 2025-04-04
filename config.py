import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Backup Configuration
BACKUP_CONFIG = {
    'compression_level': int(os.getenv('COMPRESSION_LEVEL', '6')),
    'encryption_enabled': os.getenv('ENCRYPTION_ENABLED', 'false').lower() == 'true',
    'encryption_key': os.getenv('ENCRYPTION_KEY', ''),
    'retention_days': int(os.getenv('RETENTION_DAYS', '30')),
    'max_backup_size': int(os.getenv('MAX_BACKUP_SIZE_GB', '100')),
    'exclude_patterns': [
        '/proc',
        '/sys',
        '/dev',
        '/run',
        '/tmp',
        '*.tmp',
        '*.log',
        '*.cache',
        'pagefile.sys',
        'hiberfil.sys',
        'swapfile.sys'
    ]
}

# Schedule Configuration
SCHEDULE_CONFIG = {
    'full_backup_day': os.getenv('FULL_BACKUP_DAY', 'Sunday'),
    'full_backup_time': os.getenv('FULL_BACKUP_TIME', '02:00'),
    'incremental_backup_times': os.getenv('INCREMENTAL_BACKUP_TIMES', '10:00,14:00,18:00').split(',')
}

# Logging Configuration
LOG_CONFIG = {
    'log_file': 'backup.log',
    'log_level': os.getenv('LOG_LEVEL', 'INFO'),
    'log_rotation': '1 day',
    'log_retention': '7 days'
}

# ISO Configuration
ISO_CONFIG = {
    'default_iso_name': 'backup.iso',
    'iso_volume_label': 'Lin-Win-Backup',
    'iso_publisher': 'Lin-Win-Backup System',
    'iso_preparer': 'Lin-Win-Backup',
    'iso_application': 'System Backup'
}

# Default paths
DEFAULT_PATHS = {
    'backup_dir': os.path.expanduser('~/Lin-Win-Backup'),
    'temp_dir': os.path.expanduser('~/Lin-Win-Backup/temp'),
    'log_dir': os.path.expanduser('~/Lin-Win-Backup/logs')
}

# Create default directories if they don't exist
for path in DEFAULT_PATHS.values():
    Path(path).mkdir(parents=True, exist_ok=True) 