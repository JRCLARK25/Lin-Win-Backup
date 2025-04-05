# Lin-Win-Backup Setup Guide

## Overview
Lin-Win-Backup is a secure backup solution that allows you to back up files from Linux clients to a Windows server. This guide will walk you through the setup process for both the server and client components.

## Server Setup

### 1. Prerequisites
- Windows 10/11 or Windows Server 2019/2022
- Python 3.8 or higher
- Git (optional, for cloning the repository)

### 2. Installation
1. Clone or download the repository:
   ```bash
   git clone https://github.com/yourusername/Lin-Win-Backup.git
   cd Lin-Win-Backup
   ```

2. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

### 3. Server Configuration
1. Start the server:
   ```bash
   python server_web_interface.py
   ```
   The server will start on port 3000 by default.

2. Access the web interface:
   - Open a web browser and navigate to `http://localhost:3000`
   - Default login credentials:
     - Username: `admin`
     - Password: `admin`
   - **Important**: Change the default password after first login

3. Server Security Settings:
   - The server will automatically generate encryption keys on first run
   - Keys are stored in `~/Lin-Win-Backup/keys/server/`
   - Keep these keys secure and backed up

## Client Setup

### 1. Prerequisites
- Linux system (tested on Ubuntu 20.04+, Debian 10+, CentOS 8+)
- Python 3.8 or higher
- Git (optional, for cloning the repository)

### 2. Installation
1. Clone or download the repository:
   ```bash
   git clone https://github.com/yourusername/Lin-Win-Backup.git
   cd Lin-Win-Backup
   ```

2. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

### 3. Client Configuration
1. Use the client configuration tool to set up the client:
   ```bash
   python client_config_tool.py
   ```

2. Basic Setup Steps:
   a. Set the server URL:
      ```bash
      python client_config_tool.py server --url http://your-server-ip:3000
      ```

   b. Add authorized server IP/subnet:
      ```bash
      python client_config_tool.py server --add-authorized 192.168.1.0/24
      ```

   c. Set a friendly name for the client:
      ```bash
      python client_config_tool.py client --name "My Linux Server"
      ```

   d. Add directories to backup:
      ```bash
      python client_config_tool.py client --add-dir /path/to/backup
      ```

   e. Configure backup settings:
      ```bash
      # Set maximum backup size (in MB)
      python client_config_tool.py backup --max-size 1000

      # Set retention days
      python client_config_tool.py backup --retention 30

      # Enable encryption
      python client_config_tool.py backup --encryption on

      # Enable compression
      python client_config_tool.py backup --compression on
      ```

   f. Configure logging:
      ```bash
      # Set log level
      python client_config_tool.py log --level INFO

      # Set log file path
      python client_config_tool.py log --file /var/log/backup.log
      ```

3. Register with the server:
   ```bash
   python client_config_tool.py register
   ```

### 4. Security Considerations
1. Server Authorization:
   - Only add server IPs/subnets that you trust
   - Use specific IPs instead of broad subnets when possible
   - Regularly review and update authorized servers list

2. Encryption:
   - Encryption is enabled by default
   - Keys are stored in `~/Lin-Win-Backup/keys/client/`
   - Keep these keys secure and backed up

3. Network Security:
   - Use HTTPS if exposing the server to the internet
   - Consider using a VPN for remote backups
   - Restrict server access to trusted networks

4. Access Control:
   - Change default admin password immediately
   - Use strong passwords
   - Regularly rotate credentials

## Backup Process

### 1. Manual Backup
1. From the server web interface:
   - Log in to the dashboard
   - Select a client
   - Click "Start Backup"

2. From the client:
   - Use the client API to initiate a backup
   - Monitor progress in the logs

### 2. Scheduled Backups
1. From the server web interface:
   - Log in to the dashboard
   - Select a client
   - Click "Create Schedule"
   - Set backup frequency and time

2. The client will automatically:
   - Check for scheduled backups
   - Execute backups at the specified time
   - Report results to the server

## Monitoring and Maintenance

### 1. Logs
- Server logs: `~/Lin-Win-Backup/logs/server.log`
- Client logs: Configured location (default: `~/Lin-Win-Backup/logs/client.log`)

### 2. Backup History
- View backup history in the server web interface
- Check backup status and details
- Monitor storage usage

### 3. Security Audits
- Regularly review authorized servers
- Check for unauthorized access attempts
- Update security settings as needed

## Troubleshooting

### Common Issues
1. Connection Problems:
   - Verify server URL is correct
   - Check network connectivity
   - Ensure server is authorized

2. Backup Failures:
   - Check disk space
   - Verify file permissions
   - Review logs for errors

3. Security Issues:
   - Verify encryption keys
   - Check authorization settings
   - Review access logs

### Getting Help
- Check the logs for detailed error messages
- Review the documentation
- Submit issues on GitHub

## Best Practices
1. Security:
   - Regularly update passwords
   - Monitor access logs
   - Keep software updated
   - Use encryption for all backups

2. Backup Strategy:
   - Test backups regularly
   - Maintain multiple backup copies
   - Monitor storage usage
   - Set appropriate retention periods

3. Network:
   - Use secure connections
   - Limit server exposure
   - Monitor network traffic
   - Use firewalls appropriately 