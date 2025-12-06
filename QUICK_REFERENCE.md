# Production Deployment Quick Reference

## TL;DR - 4 Steps to Deploy

### 1. SSH to your DigitalOcean server
```bash
ssh root@your_server_ip
```

### 2. System setup (run once)
```bash
apt update && apt upgrade -y
apt install -y python3 python3-venv python3-dev postgresql postgresql-contrib nginx git certbot python3-certbot-nginx build-essential libpq-dev
```

### 3. Create PostgreSQL database
```bash
sudo -u postgres psql -c "
CREATE DATABASE quiz_global;
CREATE USER quiz_user WITH PASSWORD 'YOUR_PASSWORD';
ALTER ROLE quiz_user SET client_encoding TO 'utf8';
ALTER ROLE quiz_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE quiz_user SET default_transaction_deferrable TO on;
ALTER ROLE quiz_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE quiz_global TO quiz_user;
"
```

### 4. Run deployment script
```bash
cd /srv
git clone https://github.com/chrys/quiz.global.git
cd quiz.global
cp .env.production.template .env
# Edit .env with your production values
nano .env
chmod +x deploy.sh
sudo ./deploy.sh
```

## Required Environment Variables (.env)

```
DEBUG=False
DJANGO_SECRET_KEY=generate_a_strong_key
ALLOWED_HOSTS=www.quiz.global,quiz.global

DATABASE_NAME=quiz_global
DATABASE_USER=quiz_user
DATABASE_PASSWORD=YOUR_STRONG_PASSWORD
DATABASE_HOST=localhost
DATABASE_PORT=5432

GOOGLE_APP_ID=your_google_oauth_client_id
GOOGLE_APP_SECRET=your_google_oauth_secret
GEMINI_API_KEY=your_gemini_api_key
```

## File Structure on VPS

```
/srv/quiz.global/
├── .env                          # Production environment variables (KEEP SECURE!)
├── manage.py
├── venv/                         # Python virtual environment
├── quiz2/
│   ├── settings.py              # Main settings (development)
│   ├── settings_production.py    # Production settings (uses PostgreSQL)
│   └── ...
├── front/
│   ├── models.py
│   ├── views.py
│   ├── templates/
│   └── ...
├── staticfiles/                 # Collected static files
├── media/                       # User uploads
├── logs/                        # Application logs (journalctl)
├── backups/                     # Database backups
├── gunicorn.sock                # Gunicorn socket
├── gunicorn_config.py           # Gunicorn configuration
├── backup_db.sh                 # Database backup script
└── deploy.sh                    # Deployment script
```

## Settings File Selection

**Development** (your local machine):
```bash
# Uses settings.py (SQLite, DEBUG=True)
python manage.py runserver
```

**Production** (VPS, via Gunicorn):
```bash
# Uses settings_production.py (PostgreSQL, DEBUG=False)
# Configured in /etc/systemd/system/quiz-gunicorn.service
DJANGO_SETTINGS_MODULE=quiz2.settings_production gunicorn ...
```

## PostgreSQL vs SQLite Comparison

| Feature | SQLite | PostgreSQL |
|---------|--------|------------|
| File Location | `db.sqlite3` | Network service |
| Multi-user | No | Yes |
| Concurrency | Limited | Excellent |
| Performance | Good for small apps | Great for production |
| Backups | File copy | `pg_dump` |
| Migrations | Works great | Works great |
| Production Ready | No | Yes |

## Key Changes Made to Your Project

### 1. **requirements.txt** - Added production packages
```
gunicorn==21.2.0           # Application server
psycopg2-binary==2.9.9     # PostgreSQL adapter
whitenoise==6.6.0          # Serve static files
django-cors-headers==4.3.1 # CORS handling
```

### 2. **settings_production.py** - New production configuration
- PostgreSQL database configuration
- SSL/HTTPS enforcement
- Security headers (HSTS, CSP, etc.)
- WhiteNoise for static files
- Journalctl logging integration
- Disabled DEBUG mode

### 3. **systemd service files** - Automatic process management
- `quiz-gunicorn.service` - Runs your app with Gunicorn
- `quiz-gunicorn.socket` - Manages Gunicorn socket
- Logs sent to `journalctl` (viewable via `sudo journalctl -u quiz-gunicorn.service`)

### 4. **Nginx configuration** - Reverse proxy
- HTTPS with SSL
- Static file serving
- Request forwarding to Gunicorn
- Security headers
- Gzip compression

## Important Commands

### Deployment/Updates
```bash
cd /srv/quiz.global
git pull                  # Get latest code
python manage.py migrate  # Run migrations
python manage.py collectstatic --noinput  # Update static files
sudo systemctl restart quiz-gunicorn      # Restart app
```

### Monitoring
```bash
# View application logs
sudo journalctl -u quiz-gunicorn.service -f

# Check service status
sudo systemctl status quiz-gunicorn

# View last 100 log lines
sudo journalctl -u quiz-gunicorn.service -n 100

# Only show errors
sudo journalctl -u quiz-gunicorn.service -p err
```

### Database
```bash
# Backup database
/srv/quiz.global/backup_db.sh

# Connect to PostgreSQL
psql -U quiz_user -d quiz_global -h localhost

# List databases
sudo -u postgres psql -l

# List users
sudo -u postgres psql -c "\du"
```

### SSL Certificate
```bash
# Get new certificate
sudo certbot certonly --nginx -d quiz.global -d www.quiz.global

# Check certificate status
sudo certbot certificates

# Renew certificate manually
sudo certbot renew
```

## Verification Checklist

After running `deploy.sh`:

- [ ] Check if app is running: `sudo systemctl status quiz-gunicorn`
- [ ] Check logs: `sudo journalctl -u quiz-gunicorn.service -n 20`
- [ ] Test website: `curl https://www.quiz.global` (should not error)
- [ ] Visit `https://www.quiz.global` in browser
- [ ] Visit `https://www.quiz.global/admin` (should load)
- [ ] Test quiz generation
- [ ] Check static files load (CSS, JS)
- [ ] Database connection works: `psql -U quiz_user -d quiz_global -h localhost`

## Common Issues & Fixes

### "Connection refused" to database
```bash
# PostgreSQL not running?
sudo systemctl restart postgresql

# Wrong password?
# Edit .env and fix DATABASE_PASSWORD
sudo systemctl restart quiz-gunicorn
```

### "Static files not loading" (CSS/JS broken)
```bash
cd /srv/quiz.global
source venv/bin/activate
python manage.py collectstatic --noinput
sudo systemctl restart nginx
```

### "Permission denied" errors
```bash
sudo chown -R www-data:www-data /srv/quiz.global
sudo chmod -R 755 /srv/quiz.global
sudo chmod 644 /srv/quiz.global/.env
```

### "Gunicorn won't start"
```bash
# Check detailed error
sudo journalctl -u quiz-gunicorn.service -n 50

# Verify .env exists and has all required variables
cat /srv/quiz.global/.env

# Test manually (will show errors clearly)
cd /srv/quiz.global
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=quiz2.settings_production
python -c "from django.conf import settings; print(settings.DATABASES)"
```

## Logging with journalctl

```bash
# Real-time logs (follow mode)
sudo journalctl -u quiz-gunicorn.service -f

# Last 50 lines
sudo journalctl -u quiz-gunicorn.service -n 50

# Last 24 hours
sudo journalctl -u quiz-gunicorn.service --since "24 hours ago"

# Errors only
sudo journalctl -u quiz-gunicorn.service -p err

# Search for specific text
sudo journalctl -u quiz-gunicorn.service | grep "ERROR"

# Pretty JSON format
sudo journalctl -u quiz-gunicorn.service -o json-pretty
```

## Database Backup & Restore

### Automatic backups (daily at 2 AM)
```bash
sudo crontab -e
# Add: 0 2 * * * /srv/quiz.global/backup_db.sh
```

### List backups
```bash
ls -lh /srv/quiz.global/backups/
```

### Manual backup
```bash
/srv/quiz.global/backup_db.sh
```

### Restore backup
```bash
# Restore to new database name first for safety
gunzip -c /srv/quiz.global/backups/quiz_global_20240101_020000.sql.gz | \
  sudo -u postgres psql quiz_global
```

## Next Steps After Deployment

1. ✅ Verify app is running at https://www.quiz.global
2. ✅ Test admin login at https://www.quiz.global/admin
3. ✅ Test quiz generation with Gemini API
4. ✅ Create a test quiz and verify scoring works
5. 🔄 Set up monitoring (optional): Uptime Robot, DataDog, New Relic
6. 🔄 Configure email (for password resets)
7. 🔄 Set up CDN (CloudFlare) for better performance
8. 🔄 Enable 2FA for admin user

## Reference Files

| File | Purpose | Location |
|------|---------|----------|
| `settings_production.py` | Production Django config | `quiz2/` |
| `gunicorn_config.py` | Gunicorn app server config | Repository root |
| `quiz-gunicorn.service` | Systemd service unit | Copy to `/etc/systemd/system/` |
| `quiz-gunicorn.socket` | Systemd socket unit | Copy to `/etc/systemd/system/` |
| `nginx-quiz.global.conf` | Nginx reverse proxy config | Copy to `/etc/nginx/sites-available/` |
| `.env.production.template` | Environment variables template | Copy to `.env` on VPS |
| `deploy.sh` | Automated deployment script | Repository root |
| `backup_db.sh` | Database backup script | Repository root |
| `PRODUCTION_SETUP.md` | Detailed setup guide | Repository root |
| `DEPLOYMENT_GUIDE.md` | Comprehensive deployment guide | Repository root |

---

**Questions?** Check the detailed guides:
- `PRODUCTION_SETUP.md` - Step-by-step setup instructions
- `DEPLOYMENT_GUIDE.md` - Complete deployment and troubleshooting guide
