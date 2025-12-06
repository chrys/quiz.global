#!/bin/bash
# Production deployment script for Quiz Global
# Run this on your DigitalOcean VPS to deploy the application

set -e  # Exit on any error

echo "======================================"
echo "Quiz Global Production Deployment"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DEPLOY_DIR="/srv/quiz.global"
REPO_URL="https://github.com/chrys/quiz.global.git"
VENV_DIR="$DEPLOY_DIR/venv"
DJANGO_USER="www-data"
DJANGO_GROUP="www-data"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    print_error "This script must be run as root"
    exit 1
fi

# Step 1: Check prerequisites
print_status "Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    exit 1
fi

if ! command -v git &> /dev/null; then
    print_error "Git is not installed"
    exit 1
fi

if ! command -v psql &> /dev/null; then
    print_error "PostgreSQL client is not installed"
    exit 1
fi

print_status "All prerequisites installed"

# Step 2: Create deployment directory
if [ ! -d "$DEPLOY_DIR" ]; then
    print_status "Creating deployment directory: $DEPLOY_DIR"
    mkdir -p "$DEPLOY_DIR"
else
    print_status "Deployment directory already exists"
fi

# Step 3: Clone or pull repository
cd "$DEPLOY_DIR"

if [ -d ".git" ]; then
    print_status "Repository already exists, pulling latest changes..."
    git pull origin main
else
    print_status "Cloning repository..."
    git clone "$REPO_URL" .
fi

print_status "Repository updated to latest version"

# Step 4: Create Python virtual environment
if [ ! -d "$VENV_DIR" ]; then
    print_status "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
else
    print_status "Virtual environment already exists"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"
print_status "Virtual environment activated"

# Step 5: Install Python dependencies
print_status "Installing Python dependencies..."
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
print_status "Python dependencies installed"

# Step 6: Check for .env file
if [ ! -f ".env" ]; then
    print_warning ".env file not found!"
    print_warning "Please create /srv/quiz.global/.env with the following variables:"
    echo ""
    echo "  DEBUG=False"
    echo "  DJANGO_SECRET_KEY=your_secret_key_here"
    echo "  ALLOWED_HOSTS=www.quiz.global,quiz.global"
    echo "  DATABASE_ENGINE=django.db.backends.postgresql"
    echo "  DATABASE_NAME=quiz_global"
    echo "  DATABASE_USER=quiz_user"
    echo "  DATABASE_PASSWORD=your_db_password"
    echo "  DATABASE_HOST=localhost"
    echo "  DATABASE_PORT=5432"
    echo "  GOOGLE_APP_ID=your_google_app_id"
    echo "  GOOGLE_APP_SECRET=your_google_app_secret"
    echo "  GEMINI_API_KEY=your_gemini_api_key"
    echo ""
    print_warning "Deployment paused. Create the .env file and run the script again."
    exit 1
else
    print_status ".env file found"
fi

# Set proper permissions on .env
chmod 644 .env
chown $DJANGO_USER:$DJANGO_GROUP .env
print_status ".env file permissions set correctly"

# Step 7: Create logs directory
if [ ! -d "logs" ]; then
    mkdir -p logs
fi
chown $DJANGO_USER:$DJANGO_GROUP logs
chmod 755 logs
print_status "Logs directory created"

# Step 8: Create media directory
if [ ! -d "media" ]; then
    mkdir -p media
fi
chown $DJANGO_USER:$DJANGO_GROUP media
chmod 755 media
print_status "Media directory created"

# Step 9: Run Django migrations
print_status "Running Django migrations..."
DJANGO_SETTINGS_MODULE=quiz2.settings_production python manage.py migrate --noinput
print_status "Migrations completed"

# Step 10: Collect static files
print_status "Collecting static files..."
DJANGO_SETTINGS_MODULE=quiz2.settings_production python manage.py collectstatic --noinput
print_status "Static files collected"

# Step 11: Set proper permissions
print_status "Setting proper permissions..."
chown -R $DJANGO_USER:$DJANGO_GROUP "$DEPLOY_DIR"
chmod -R 755 "$DEPLOY_DIR"
chmod 644 "$DEPLOY_DIR/.env"
chmod 755 "$DEPLOY_DIR/logs"
chmod 755 "$DEPLOY_DIR/media"
chmod 755 "$DEPLOY_DIR/staticfiles"
print_status "Permissions set correctly"

# Step 12: Setup systemd services
print_status "Setting up systemd services..."

if [ ! -f "/etc/systemd/system/quiz-gunicorn.service" ]; then
    cp quiz-gunicorn.service /etc/systemd/system/
    cp quiz-gunicorn.socket /etc/systemd/system/
    print_status "Systemd service files installed"
else
    cp quiz-gunicorn.service /etc/systemd/system/
    cp quiz-gunicorn.socket /etc/systemd/system/
    print_status "Systemd service files updated"
fi

# Reload systemd daemon
systemctl daemon-reload
print_status "Systemd daemon reloaded"

# Step 13: Enable and start services
print_status "Enabling and starting services..."
systemctl enable quiz-gunicorn.socket
systemctl enable quiz-gunicorn.service
systemctl start quiz-gunicorn.socket
systemctl start quiz-gunicorn.service
print_status "Gunicorn services started"

# Step 14: Verify services
print_status "Verifying services..."
if systemctl is-active --quiet quiz-gunicorn.service; then
    print_status "Gunicorn service is running"
else
    print_error "Gunicorn service failed to start!"
    print_status "Check logs with: sudo journalctl -u quiz-gunicorn.service -n 50"
    exit 1
fi

# Step 15: Setup Nginx (if not already done)
if [ ! -f "/etc/nginx/sites-available/quiz.global" ]; then
    print_status "Installing Nginx configuration..."
    cp nginx-quiz.global.conf /etc/nginx/sites-available/quiz.global
    ln -sf /etc/nginx/sites-available/quiz.global /etc/nginx/sites-enabled/quiz.global
    
    # Test Nginx configuration
    nginx -t
    print_status "Nginx configuration installed"
else
    print_status "Nginx configuration already exists"
fi

# Reload Nginx
systemctl reload nginx
print_status "Nginx reloaded"

# Step 16: Setup SSL with Certbot (if not already done)
if [ ! -f "/etc/letsencrypt/live/quiz.global/fullchain.pem" ]; then
    print_warning "SSL certificate not found. Installing Certbot..."
    apt-get update
    apt-get install -y certbot python3-certbot-nginx
    
    print_status "Requesting SSL certificate from Let's Encrypt..."
    certbot certonly --nginx -d quiz.global -d www.quiz.global
    print_status "SSL certificate installed"
else
    print_status "SSL certificate already exists"
fi

# Step 17: Setup auto-renewal for SSL
systemctl enable certbot.timer
systemctl start certbot.timer
print_status "SSL auto-renewal enabled"

# Final status
echo ""
echo "======================================"
echo -e "${GREEN}Deployment Complete!${NC}"
echo "======================================"
echo ""
print_status "Application is running at: https://www.quiz.global"
echo ""
echo "Useful commands:"
echo "  Check service status:     sudo systemctl status quiz-gunicorn"
echo "  View application logs:    sudo journalctl -u quiz-gunicorn.service -f"
echo "  Restart services:         sudo systemctl restart quiz-gunicorn"
echo "  Check Nginx:              sudo systemctl status nginx"
echo "  View Nginx error logs:    sudo tail -f /var/log/nginx/quiz.global_error.log"
echo ""
