#!/bin/bash
# Phase A - Step 1: Create complete database backup before migration
# This script creates a timestamped backup of the entire Firebase database

set -e  # Exit on any error

echo "=== GIIR Conference System - Database Backup Script ==="
echo "Phase A - Step 1: Database Backup"
echo ""

# Generate timestamp for backup file
BACKUP_DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="backups"
BACKUP_FILE="${BACKUP_DIR}/firebase-backup-${BACKUP_DATE}.json"

# Create backups directory if it doesn't exist
mkdir -p ${BACKUP_DIR}

echo "Creating database backup..."
echo "Backup file: ${BACKUP_FILE}"
echo ""

# Create Firebase database backup
firebase database:get / --output ${BACKUP_FILE}

if [ $? -eq 0 ]; then
    echo "✅ Backup created successfully: ${BACKUP_FILE}"
    
    # Get file size for verification
    if [ -f "${BACKUP_FILE}" ]; then
        FILE_SIZE=$(stat -c%s "${BACKUP_FILE}" 2>/dev/null || stat -f%z "${BACKUP_FILE}" 2>/dev/null || echo "unknown")
        echo "📁 Backup file size: ${FILE_SIZE} bytes"
    fi
    
    echo ""
    echo "=== Backup Verification ==="
    echo "✅ Backup completed at: $(date)"
    echo "📂 Backup location: ${BACKUP_FILE}"
    echo "🔍 Please verify the backup file contains expected data"
    echo ""
    echo "Next step: Run './2-create-default-conference.js' to create default conference schema"
else
    echo "❌ Backup failed!"
    echo "Please check your Firebase configuration and try again"
    exit 1
fi 