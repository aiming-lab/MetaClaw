# Production Configuration for Project Orion API
# Last updated: 2026-03-15

API_TIMEOUT = 30  # seconds
LOG_LEVEL = "WARNING"
DB_HOST = "prod-db.orion.internal"
DB_PORT = 5432
DB_NAME = "orion_production"
DB_USER = "orion_api_user"
MAX_CONNECTIONS = 100
CACHE_TTL = 3600
ENABLE_METRICS = True
METRICS_PORT = 9090
