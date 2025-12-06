# Quiz.Global Production Deployment Guide

## Prerequisites
- Ubuntu VPS on DigitalOcean
- Domain: www.quiz.global (already transferred)
- Nginx configured
- PostgreSQL installed

## 1. PostgreSQL Database Setup

### SSH into your DigitalOcean server:
```bash
ssh root@your_server_ip
```

### Create PostgreSQL database and user:
```bash
# Connect to PostgreSQL
sudo -u postgres psql

# In PostgreSQL shell, run:
CREATE DATABASE quiz_global;
CREATE USER quiz_user WITH PASSWORD 'strong_password_here';
ALTER ROLE quiz_user SET client_encoding TO 'utf8';
ALTER ROLE quiz_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE quiz_user SET default_transaction_deferrable TO on;
ALTER ROLE quiz_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE quiz_global TO quiz_user;
\q
```

### Test the connection:
```bash
psql -U quiz_user -d quiz_global -h localhost
```

## 2. Update Python Dependencies

Add to `requirements.txt`:
```
psycopg2-binary==2.9.9  # PostgreSQL adapter for Python
gunicorn==21.2.0
whitenoise==6.6.0       # Serve static files efficiently
```

Install on your VPS:
```bash
cd /srv/quiz.global
pip install -r requirements.txt
```

## 3. Environment Variables Setup

Create `/srv/quiz.global/.env` on the production server:
```
DEBUG=False
DJANGO_SECRET_KEY=your_new_secret_key_here
ALLOWED_HOSTS=www.quiz.global,quiz.global

# Database
DATABASE_ENGINE=django.db.backends.postgresql
DATABASE_NAME=quiz_global
DATABASE_USER=quiz_user
DATABASE_PASSWORD=strong_password_here
DATABASE_HOST=localhost
DATABASE_PORT=5432

# Google OAuth
GOOGLE_APP_ID=your_google_app_id
GOOGLE_APP_SECRET=your_google_app_secret

# Gemini API
GEMINI_API_KEY=your_gemini_api_key
```

**Important:** Use strong, unique password and keep `.env` secure (644 permissions, owned by www-data user).

## 4. Django Settings Changes

See `settings-production.py` for the updated configuration. Key changes:
- DEBUG = False
- ALLOWED_HOSTS configured
- PostgreSQL database backend
- Static files served via WhiteNoise
- HTTPS enforcement
- CSRF and security settings hardened
- Logging redirected to journalctl via syslog handler

## 5. Gunicorn Configuration

Create `/srv/quiz.global/gunicorn_config.py`:
```python
import multiprocessing

bind = "unix:/srv/quiz.global/gunicorn.sock"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
access_log = "-"
error_log = "-"
capture_output = True
```

## 6. Systemd Service Files

### Create `/etc/systemd/system/quiz-gunicorn.service`:
```ini
[Unit]
Description=Quiz Global Gunicorn Service
After=network.target
Requires=quiz-gunicorn.socket

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/srv/quiz.global
Environment="PATH=/srv/quiz.global/venv/bin"
EnvironmentFile=/srv/quiz.global/.env
ExecStart=/srv/quiz.global/venv/bin/gunicorn \
    --config /srv/quiz.global/gunicorn_config.py \
    --name quiz-gunicorn \
    quiz2.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
KillSignal=SIGTERM
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=quiz-gunicorn

[Install]
WantedBy=multi-user.target
```

### Create `/etc/systemd/system/quiz-gunicorn.socket`:
```ini
[Unit]
Description=Quiz Global Gunicorn Socket
Before=quiz-gunicorn.service

[Socket]
ListenStream=/srv/quiz.global/gunicorn.sock
NoDelay=true

[Install]
WantedBy=sockets.target
```

## 7. Nginx Configuration

Update your existing nginx config at `/etc/nginx/sites-available/quiz.global`:
```nginx
upstream quiz_app {
    server unix:/srv/quiz.global/gunicorn.sock fail_timeout=0;
}

server {
    listen 80;
    server_name www.quiz.global quiz.global;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name www.quiz.global quiz.global;

    # SSL certificates (get from Let's Encrypt via Certbot)
    ssl_certificate /etc/letsencrypt/live/quiz.global/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/quiz.global/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    client_max_body_size 20M;

    location /static/ {
        alias /srv/quiz.global/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /srv/quiz.global/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    location / {
        proxy_pass http://quiz_app;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_buffering off;
    }

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
}
```

## 8. Deployment Steps

### 1. Clone repo and setup on VPS:
```bash
cd /srv
git clone https://github.com/chrys/quiz.global.git
cd quiz.global
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Create .env file with production values
```bash
nano /srv/quiz.global/.env
# Add all environment variables
chmod 644 /srv/quiz.global/.env
```

### 3. Run Django migrations:
```bash
cd /srv/quiz.global
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
```

### 4. Create superuser:
```bash
python manage.py createsuperuser
```

### 5. Set proper permissions:
```bash
sudo chown -R www-data:www-data /srv/quiz.global
sudo chmod -R 755 /srv/quiz.global
sudo chmod 644 /srv/quiz.global/.env
```

### 6. Start services:
```bash
sudo systemctl daemon-reload
sudo systemctl enable quiz-gunicorn.socket
sudo systemctl enable quiz-gunicorn.service
sudo systemctl start quiz-gunicorn.socket
sudo systemctl start quiz-gunicorn.service
sudo systemctl enable nginx
sudo systemctl restart nginx
```

### 7. Verify services:
```bash
sudo systemctl status quiz-gunicorn.service
sudo systemctl status quiz-gunicorn.socket
sudo systemctl status nginx
```

## 9. SSL/TLS with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot certonly --nginx -d quiz.global -d www.quiz.global
# Choose to redirect HTTP to HTTPS when prompted
```

## 10. Monitoring & Logging

### View Gunicorn logs:
```bash
sudo journalctl -u quiz-gunicorn.service -f  # Follow logs
sudo journalctl -u quiz-gunicorn.service -n 100  # Last 100 lines
```

### View Nginx logs:
```bash
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Filter for errors:
```bash
sudo journalctl -u quiz-gunicorn.service -p err
```

## 11. Database Backups

### Create backup script `/srv/quiz.global/backup_db.sh`:
```bash
#!/bin/bash
BACKUP_DIR="/srv/quiz.global/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/quiz_global_$TIMESTAMP.sql"

mkdir -p $BACKUP_DIR
pg_dump -U quiz_user -h localhost quiz_global > $BACKUP_FILE
gzip $BACKUP_FILE

# Keep only last 7 backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "Backup completed: ${BACKUP_FILE}.gz"
```

### Add to crontab (daily backup at 2 AM):
```bash
sudo crontab -e
# Add: 0 2 * * * /srv/quiz.global/backup_db.sh
```

## 12. Production Checklist

- [ ] PostgreSQL installed and database created
- [ ] `requirements.txt` updated with psycopg2-binary and gunicorn
- [ ] `.env` file created with all production values
- [ ] `settings.py` updated for production (see settings-production.py)
- [ ] Gunicorn config created
- [ ] Systemd service files created
- [ ] Nginx config updated
- [ ] Django migrations run
- [ ] Static files collected
- [ ] Permissions set correctly
- [ ] Services started and enabled
- [ ] SSL certificates obtained from Let's Encrypt
- [ ] Logs verified via journalctl
- [ ] Database backups configured
- [ ] Health check: https://www.quiz.global should load

## Troubleshooting

### Gunicorn won't start:
```bash
sudo journalctl -u quiz-gunicorn.service -n 50
```

### Database connection errors:
```bash
psql -U quiz_user -d quiz_global -h localhost
# Should connect without password errors
```

### Static files not loading:
```bash
python manage.py collectstatic --noinput
sudo chown -R www-data:www-data /srv/quiz.global/staticfiles
```

### Permission denied on gunicorn.sock:
```bash
sudo chown www-data:www-data /srv/quiz.global
sudo chmod 755 /srv/quiz.global
```
