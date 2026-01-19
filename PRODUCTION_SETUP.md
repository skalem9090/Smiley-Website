# Production Server Setup Guide

This guide explains how to run Smileys Blog Site using a production-ready WSGI server.

## 🚀 Quick Start

### Windows (Recommended)
```bash
# Option 1: Use the Python script
python start_production.py

# Option 2: Use the batch file
start_production.bat

# Option 3: Use PowerShell
.\start_production.ps1
```

### Linux/Mac
```bash
# The script will automatically use Gunicorn on Unix systems
python start_production.py
```

### Manual Start (Advanced)
```bash
# Windows - using Waitress
waitress-serve --host=0.0.0.0 --port=5000 --threads=4 wsgi:app

# Linux/Mac - using Gunicorn
gunicorn --config gunicorn_config.py wsgi:app
```

## 📋 Prerequisites

1. **Python Environment**: Ensure you have Python 3.8+ installed
2. **Dependencies**: Install required packages
   ```bash
   pip install -r requirements-clean.txt
   ```
3. **Environment File**: Create a `.env` file with your configuration
4. **Database**: Ensure the `instance/` directory exists

## 🔧 WSGI Servers

### Waitress (Windows)
- **Pros**: Cross-platform, pure Python, reliable
- **Cons**: Single-threaded per worker
- **Best for**: Windows development and small-scale production

### Gunicorn (Linux/Mac)
- **Pros**: Multi-worker, battle-tested, highly configurable
- **Cons**: Unix-only (doesn't work on Windows)
- **Best for**: Linux/Mac production deployments

## ⚙️ Configuration

### Waitress Configuration
The production script uses these Waitress settings:
- **Host**: `0.0.0.0` (all interfaces)
- **Port**: `5000`
- **Threads**: `4`
- **Connection Limit**: `1000`
- **Cleanup Interval**: `30` seconds
- **Channel Timeout**: `120` seconds

### Gunicorn Configuration
Settings are defined in `gunicorn_config.py`:
- **Workers**: `4`
- **Worker Class**: `sync`
- **Timeout**: `30` seconds
- **Max Requests**: `1000` (with jitter)
- **Logging**: Stdout/stderr

## 🌐 Accessing Your Site

Once started, your blog will be available at:
- **Local**: http://localhost:5000
- **Network**: http://YOUR_IP_ADDRESS:5000

## 🧪 Testing

Test if the server is working:
```bash
python test_server.py
```

## 📁 File Structure

```
├── wsgi.py                 # WSGI entry point
├── start_production.py     # Cross-platform startup script
├── start_production.bat    # Windows batch file
├── start_production.ps1    # PowerShell script
├── gunicorn_config.py      # Gunicorn configuration
├── test_server.py          # Server testing script
└── app.py                  # Main Flask application
```

## 🔒 Security Considerations

### For Production Deployment:

1. **Environment Variables**: Never commit `.env` files
2. **Secret Key**: Use a strong, random secret key
3. **Database**: Use PostgreSQL or MySQL instead of SQLite
4. **HTTPS**: Configure SSL/TLS certificates
5. **Firewall**: Restrict access to necessary ports only
6. **Reverse Proxy**: Use Nginx or Apache as a reverse proxy

### Example Nginx Configuration:
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 🐛 Troubleshooting

### Common Issues:

1. **Port Already in Use**
   ```bash
   # Find process using port 5000
   netstat -ano | findstr :5000  # Windows
   lsof -i :5000                 # Linux/Mac
   ```

2. **Module Not Found**
   - Ensure virtual environment is activated
   - Install dependencies: `pip install -r requirements-clean.txt`

3. **Database Errors**
   - Check if `instance/` directory exists
   - Verify database path in `.env` file

4. **Permission Errors**
   - Ensure write permissions for `instance/` directory
   - Check file ownership and permissions

### Logs and Debugging:

- **Waitress**: Logs to console by default
- **Gunicorn**: Configured to log to stdout/stderr
- **Flask**: Check application logs in the console output

## 📈 Performance Tuning

### For High Traffic:

1. **Increase Workers/Threads**:
   - Waitress: `--threads=8`
   - Gunicorn: Modify `workers` in `gunicorn_config.py`

2. **Database Connection Pooling**:
   - Configure SQLAlchemy pool settings
   - Consider using connection poolers like PgBouncer

3. **Caching**:
   - Implement Redis for session storage
   - Add caching headers for static content

4. **Load Balancing**:
   - Run multiple instances behind a load balancer
   - Use Docker containers for easy scaling

## 🔄 Process Management

For production, consider using process managers:

### Systemd (Linux)
```ini
[Unit]
Description=Smileys Blog Site
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/your/app
ExecStart=/path/to/venv/bin/python start_production.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### PM2 (Cross-platform)
```bash
pm2 start start_production.py --name "smileys-blog"
pm2 startup
pm2 save
```

## 📞 Support

If you encounter issues:
1. Check the console output for error messages
2. Verify your `.env` configuration
3. Test with `python test_server.py`
4. Check the troubleshooting section above

---

**Happy Blogging!** 🎉