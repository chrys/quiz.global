#!/bin/bash
# PostgreSQL backup script for Quiz Global
# Schedule with cron: 0 2 * * * /srv/quiz.global/backup_db.sh

BACKUP_DIR="/srv/quiz.global/backups"
DB_NAME="quiz_global"
DB_USER="quiz_user"
DB_HOST="localhost"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql"
BACKUP_FILE_GZ="${BACKUP_FILE}.gz"

# Log file
LOG_FILE="/var/log/quiz-backup.log"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Function to log messages
log_message() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_message "=== Starting PostgreSQL backup ==="

# Create database dump
if PGPASSWORD="$DB_PASSWORD" pg_dump -U "$DB_USER" -h "$DB_HOST" "$DB_NAME" > "$BACKUP_FILE"; then
    log_message "Database dump created successfully: $BACKUP_FILE"
    
    # Compress the backup
    if gzip "$BACKUP_FILE"; then
        log_message "Backup compressed: $BACKUP_FILE_GZ"
        SIZE=$(du -h "$BACKUP_FILE_GZ" | cut -f1)
        log_message "Backup size: $SIZE"
    else
        log_message "ERROR: Failed to compress backup"
        exit 1
    fi
else
    log_message "ERROR: Database dump failed"
    exit 1
fi

# Delete old backups (keep only last 7 days)
log_message "Cleaning up old backups..."
find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -mtime +7 -delete
REMAINING=$(find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" | wc -l)
log_message "Old backups deleted. Remaining backups: $REMAINING"

# Optional: Upload to cloud storage (AWS S3, Google Cloud Storage, etc.)
# Example for AWS S3:
# aws s3 cp "$BACKUP_FILE_GZ" "s3://your-backup-bucket/quiz-global/$BACKUP_FILE_GZ"

log_message "=== Backup completed successfully ==="
log_message ""
