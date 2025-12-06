# Quiz Global - Production Deployment Guide

## Overview
This guide walks you through deploying the Quiz Global Django application to DigitalOcean with PostgreSQL, Gunicorn, and Nginx.

## Architecture
```
Domain: www.quiz.global (DigitalOcean DNS)
    ↓
Nginx (Reverse Proxy + Static Files)
    ↓
Gunicorn Socket (/srv/quiz.global/gunicorn.sock)
    ↓
Django Application (Python)
    ↓
PostgreSQL Database
```

## Prerequisites
- DigitalOcean Ubuntu VPS (20.04 LTS or newer recommended)
- Domain transferred to DigitalOcean DNS (www.quiz.global)
- SSH access to server
- Root or sudo privileges

## Quick Start (5 Steps)

### Step 1: SSH into your server
```bash
ssh root@your_server_ip
```

### Step 2: Install system dependencies
```bash
apt update
apt upgrade -y
apt install -y python3 python3-venv python3-dev postgresql postgresql-contrib nginx git certbot python3-certbot-nginx build-essential libpq-dev
```

### Step 3: Setup PostgreSQL database
```bash
sudo -u postgres psql

# In PostgreSQL shell:
CREATE DATABASE quiz_global;
CREATE USER quiz_user WITH PASSWORD 'YOUR_STRONG_PASSWORD_HERE';
ALTER ROLE quiz_user SET client_encoding TO 'utf8';
ALTER ROLE quiz_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE quiz_user SET default_transaction_deferrable TO on;
ALTER ROLE quiz_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE quiz_global TO quiz_user;
\q
```

### Step 4: Clone repository and run deployment script
```bash
cd /srv
git clone https://github.com/chrys/quiz.global.git
cd quiz.global
chmod +x deploy.sh

# Create .env file with production values
cp .env.production.template .env
nano .env  # Edit with your actual values

# Run deployment script
sudo ./deploy.sh
```

### Step 5: Verify deployment
```bash
# Check services
sudo systemctl status quiz-gunicorn
sudo systemctl status nginx

# Check logs
sudo journalctl -u quiz-gunicorn.service -n 50

# Test application
curl https://www.quiz.global
```

## Detailed Configuration

### Database Setup

#### Create PostgreSQL user and database:
```bash
sudo -u postgres psql -c "CREATE DATABASE quiz_global;"
sudo -u postgres psql -c "CREATE USER quiz_user WITH PASSWORD 'strong_password_here';"
sudo -u postgres psql -c "ALTER ROLE quiz_user SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE quiz_user SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE quiz_user SET timezone TO 'UTC';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE quiz_global TO quiz_user;"
```

#### Test connection:
```bash
psql -U quiz_user -d quiz_global -h localhost
# Should connect without asking for password if .pgpass is set up
```

### Environment Variables

Create `/srv/quiz.global/.env` with:
```
DEBUG=False
DJANGO_SECRET_KEY=your_new_secret_key_here_use_django_secret_key_generator
ALLOWED_HOSTS=www.quiz.global,quiz.global

# Database
DATABASE_ENGINE=django.db.backends.postgresql
DATABASE_NAME=quiz_global
DATABASE_USER=quiz_user
DATABASE_PASSWORD=your_strong_database_password
DATABASE_HOST=localhost
DATABASE_PORT=5432

# Google OAuth
GOOGLE_APP_ID=your_google_oauth_client_id
GOOGLE_APP_SECRET=your_google_oauth_secret

# Gemini API
GEMINI_API_KEY=your_gemini_api_key

# Email (optional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_specific_password
DEFAULT_FROM_EMAIL=noreply@quiz.global
```

**Security**: Set proper permissions:
```bash
chmod 644 /srv/quiz.global/.env
sudo chown www-data:www-data /srv/quiz.global/.env
```

### Running Django Migrations

```bash
cd /srv/quiz.global
source venv/bin/activate
DJANGO_SETTINGS_MODULE=quiz2.settings_production python manage.py migrate
python manage.py collectstatic --noinput
```

### Creating Superuser

```bash
cd /srv/quiz.global
source venv/bin/activate
DJANGO_SETTINGS_MODULE=quiz2.settings_production python manage.py createsuperuser
```

## SSL/TLS Certificate (Let's Encrypt)

### Request certificate:
```bash
sudo certbot certonly --nginx -d quiz.global -d www.quiz.global
```

### Auto-renewal:
```bash
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
sudo systemctl list-timers
```

### Renewal status:
```bash
sudo certbot certificates
```

## Service Management

### Gunicorn service
```bash
# Status
sudo systemctl status quiz-gunicorn.service

# Restart
sudo systemctl restart quiz-gunicorn.service

# Enable on startup
sudo systemctl enable quiz-gunicorn.service

# View logs
sudo journalctl -u quiz-gunicorn.service -f
```

### Nginx service
```bash
# Status
sudo systemctl status nginx

# Restart
sudo systemctl restart nginx

# Test config
sudo nginx -t

# View access logs
sudo tail -f /var/log/nginx/quiz.global_access.log

# View error logs
sudo tail -f /var/log/nginx/quiz.global_error.log
```

## Logging with journalctl

### View Gunicorn logs:
```bash
# Follow logs in real-time
sudo journalctl -u quiz-gunicorn.service -f

# Show last 100 lines
sudo journalctl -u quiz-gunicorn.service -n 100

# Show logs from last hour
sudo journalctl -u quiz-gunicorn.service --since "1 hour ago"

# Show only errors
sudo journalctl -u quiz-gunicorn.service -p err

# Show logs with timestamps
sudo journalctl -u quiz-gunicorn.service --output=short-full

# Export logs
sudo journalctl -u quiz-gunicorn.service --output=json > /tmp/logs.json
```

### Persistent journalctl storage:
```bash
# Enable persistent storage
sudo mkdir -p /var/log/journal
sudo systemctl restart systemd-journald

# Verify
sudo journalctl --disk-usage

# Clean old logs (keep 1GB)
sudo journalctl --vacuum-size=1G
```

## Database Backups

### Manual backup:
```bash
/srv/quiz.global/backup_db.sh
```

### Automatic backup (cron):
```bash
# Edit crontab
sudo crontab -e

# Add this line for daily backup at 2 AM:
0 2 * * * /srv/quiz.global/backup_db.sh

# View scheduled jobs
sudo crontab -l
```

### Verify backup:
```bash
# List backups
ls -lh /srv/quiz.global/backups/

# Test restore (don't actually restore):
pg_restore --list /srv/quiz.global/backups/quiz_global_*.sql.gz | head -20
```

### Restore backup:
```bash
# Create new database
sudo -u postgres createdb quiz_global_restored

# Restore from backup
gunzip -c /srv/quiz.global/backups/quiz_global_20240101_020000.sql.gz | \
  sudo -u postgres psql quiz_global_restored

# Drop old database and rename new one
sudo -u postgres psql <<EOF
DROP DATABASE quiz_global;
ALTER DATABASE quiz_global_restored RENAME TO quiz_global;
EOF
```

## Monitoring

### Check disk usage:
```bash
df -h
du -sh /srv/quiz.global/*
```

### Check memory:
```bash
free -h
```

### Check active connections:
```bash
# PostgreSQL connections
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"

# System connections
netstat -an | grep ESTABLISHED | wc -l
```

### Monitor Gunicorn workers:
```bash
ps aux | grep gunicorn
```

## Troubleshooting

### Application won't start
```bash
# Check logs
sudo journalctl -u quiz-gunicorn.service -n 50

# Check database connection
sudo -u www-data psql -U quiz_user -d quiz_global -h localhost -c "SELECT 1;"

# Check file permissions
ls -la /srv/quiz.global/.env
ls -la /srv/quiz.global/gunicorn.sock
```

### Static files not loading
```bash
# Collect static files again
cd /srv/quiz.global
source venv/bin/activate
DJANGO_SETTINGS_MODULE=quiz2.settings_production python manage.py collectstatic --noinput

# Check file permissions
sudo chown -R www-data:www-data /srv/quiz.global/staticfiles
sudo chmod -R 755 /srv/quiz.global/staticfiles

# Restart Nginx
sudo systemctl restart nginx
```

### Database connection errors
```bash
# Test PostgreSQL
sudo -u postgres psql -c "SELECT version();"

# Check postgresql.conf
sudo nano /etc/postgresql/*/main/postgresql.conf
# Ensure: listen_addresses = 'localhost'

# Check pg_hba.conf
sudo nano /etc/postgresql/*/main/pg_hba.conf
# Ensure local connection is allowed

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Permission denied errors
```bash
# Fix directory permissions
sudo chown -R www-data:www-data /srv/quiz.global
sudo chmod -R 755 /srv/quiz.global
sudo chmod 644 /srv/quiz.global/.env

# Fix gunicorn socket
sudo chown www-data:www-data /srv/quiz.global/gunicorn.sock
sudo chmod 660 /srv/quiz.global/gunicorn.sock
```

## Performance Optimization

### Enable caching (in .env):
```
CACHES_BACKEND=django.core.cache.backends.redis.RedisCache
CACHES_LOCATION=redis://127.0.0.1:6379/1
```

### Install Redis:
```bash
sudo apt install redis-server
pip install redis
```

### Optimize Nginx:
The nginx config includes gzip compression and browser caching.

### Optimize PostgreSQL:
```bash
# Edit postgresql.conf
sudo nano /etc/postgresql/*/main/postgresql.conf

# Recommended settings for 2GB RAM VPS:
shared_buffers = 512MB
effective_cache_size = 1536MB
work_mem = 32MB
```

## Security Checklist

- [ ] Change default SSH port (optional but recommended)
- [ ] Set up firewall (ufw):
  ```bash
  sudo ufw default deny incoming
  sudo ufw default allow outgoing
  sudo ufw allow 22  # SSH
  sudo ufw allow 80  # HTTP
  sudo ufw allow 443 # HTTPS
  sudo ufw enable
  ```
- [ ] Disable root SSH login
- [ ] Enable SSH key authentication only
- [ ] Regular security updates: `sudo apt update && sudo apt upgrade`
- [ ] Database backups configured and tested
- [ ] SSL certificate auto-renewal working
- [ ] .env file protected (644 permissions)
- [ ] PostgreSQL password-protected
- [ ] DEBUG = False in production
- [ ] ALLOWED_HOSTS configured correctly
- [ ] CSRF protection enabled
- [ ] HTTPS enforced (nginx redirects HTTP to HTTPS)

## Deployment Commands Reference

```bash
# Deploy latest code
cd /srv/quiz.global && git pull && python manage.py migrate

# Restart all services
sudo systemctl restart quiz-gunicorn nginx

# View all logs
sudo journalctl -u quiz-gunicorn.service -f

# Database backup
/srv/quiz.global/backup_db.sh

# Static files
cd /srv/quiz.global && python manage.py collectstatic --noinput

# Create superuser
cd /srv/quiz.global && python manage.py createsuperuser
```

## Getting Help

- **Django logs**: `sudo journalctl -u quiz-gunicorn.service`
- **Nginx errors**: `/var/log/nginx/quiz.global_error.log`
- **PostgreSQL logs**: `sudo journalctl -u postgresql`
- **System logs**: `sudo journalctl` (all system logs)

## Next Steps

1. Test application at https://www.quiz.global
2. Access admin at https://www.quiz.global/admin
3. Test quiz generation with Gemini API
4. Monitor logs for any issues
5. Set up regular backups
6. Configure monitoring/alerting (Uptime Robot, New Relic, etc.)

---

For more information:
- [Django Deployment Checklist](https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/)
- [Gunicorn Documentation](https://gunicorn.org/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
