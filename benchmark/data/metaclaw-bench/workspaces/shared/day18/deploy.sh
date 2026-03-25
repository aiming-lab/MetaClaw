#!/bin/bash
# Deployment script for Project Orion API
# Deploys to production environment

set -e

echo "Starting deployment process..."

# Configuration
SERVER_ADDR="api.v2.orion.internal"
DEPLOY_USER="deploy"
APP_DIR="/opt/orion/api"
BACKUP_DIR="/opt/orion/backups"

echo "Target server: $SERVER_ADDR"

# Create backup
echo "Creating backup..."
ssh ${DEPLOY_USER}@${SERVER_ADDR} "mkdir -p $BACKUP_DIR && \
    cp -r $APP_DIR $BACKUP_DIR/api_backup_$(date +%Y%m%d_%H%M%S)"

# Upload new code
echo "Uploading application code..."
rsync -avz --exclude='*.pyc' --exclude='__pycache__' \
    ./ ${DEPLOY_USER}@${SERVER_ADDR}:${APP_DIR}/

# Restart service
echo "Restarting API service..."
ssh ${DEPLOY_USER}@${SERVER_ADDR} "systemctl restart orion-api"

# Health check
echo "Performing health check..."
sleep 5
curl -f http://${SERVER_ADDR}:8080/health || {
    echo "Health check failed! Rolling back..."
    ssh ${DEPLOY_USER}@${SERVER_ADDR} "systemctl stop orion-api && \
        rm -rf $APP_DIR && \
        cp -r $BACKUP_DIR/api_backup_latest $APP_DIR && \
        systemctl start orion-api"
    exit 1
}

echo "Deployment completed successfully!"
