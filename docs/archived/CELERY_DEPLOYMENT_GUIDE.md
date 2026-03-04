# Celery + Redis Deployment Guide

## Quick Start

### Development Environment (Docker Compose)

#### 1. Update Environment Variables

In `.devcontainer/.env` or directly in `docker-compose.yml`:

```env
USE_CELERY_TASKS=true
REDIS_HOST=redis
CELERY_BROKER_URL=redis://redis:6379/0
```

#### 2. Start Services

```bash
cd .devcontainer
docker-compose up -d redis celery-worker celery-beat app
```

#### 3. Verify Services

```bash
# Check all services running
docker-compose ps

# Check Redis
docker exec audiobooksync-redis redis-cli ping
# Expected: PONG

# Check Celery Worker
docker-compose logs celery-worker | grep "Ready to accept tasks"

# Check Celery Beat
docker-compose logs celery-beat | grep "celery beat started"
```

#### 4. Test Task Execution

```bash
# Trigger a download via API
curl -X POST http://localhost:8000/api/downloads \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"asin": "B00XXXX"}'

# Check worker logs for task execution
docker-compose logs celery-worker -f
```

### Production Environment

#### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 2. Configure Environment

Set these variables in your production environment:

```bash
# Redis Configuration
REDIS_HOST=<redis-host>
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=<your-password>  # If using password auth

# Celery Feature Flag
USE_CELERY_TASKS=true

# Celery Configuration
CELERY_MAX_RETRIES=3
CELERY_RETRY_DELAY=60
CELERY_TASK_TIME_LIMIT=7200

# Cleanup Retention
CLEANUP_RETENTION_SYNC_DAYS=90
CLEANUP_RETENTION_ERROR_DAYS=30
CLEANUP_RETENTION_COMPLETED_DAYS=7
```

#### 3. Start Services

**FastAPI Application:**
```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Celery Worker:**
```bash
celery -A src.celery_app worker -l info --concurrency=4
```

**Celery Beat (Scheduler):**
```bash
celery -A src.celery_app beat -l info
```

#### 4. Verify Deployment

```bash
# Check Celery worker status
celery -A src.celery_app inspect active

# Check Celery Beat status
celery -A src.celery_app inspect scheduled

# Check Redis connectivity
redis-cli -h <redis-host> -p 6379 -a <password> ping
```

### Using Systemd for Production

Create service files for automatic startup:

#### `/etc/systemd/system/audiobooksync-app.service`

```ini
[Unit]
Description=AudioBookSync FastAPI Application
After=network.target redis.service

[Service]
Type=notify
User=audiobooksync
WorkingDirectory=/opt/audiobooksync
Environment="PATH=/opt/audiobooksync/.venv/bin"
EnvironmentFile=/etc/audiobooksync/app.env
ExecStart=/opt/audiobooksync/.venv/bin/uvicorn \
    src.api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### `/etc/systemd/system/audiobooksync-celery-worker.service`

```ini
[Unit]
Description=AudioBookSync Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=audiobooksync
WorkingDirectory=/opt/audiobooksync
Environment="PATH=/opt/audiobooksync/.venv/bin"
EnvironmentFile=/etc/audiobooksync/app.env
ExecStart=/opt/audiobooksync/.venv/bin/celery \
    -A src.celery_app \
    worker \
    -l info \
    --concurrency=4 \
    --logfile=/var/log/audiobooksync/celery-worker.log \
    --pidfile=/var/run/audiobooksync/celery-worker.pid
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### `/etc/systemd/system/audiobooksync-celery-beat.service`

```ini
[Unit]
Description=AudioBookSync Celery Beat Scheduler
After=network.target redis.service

[Service]
Type=simple
User=audiobooksync
WorkingDirectory=/opt/audiobooksync
Environment="PATH=/opt/audiobooksync/.venv/bin"
EnvironmentFile=/etc/audiobooksync/app.env
ExecStart=/opt/audiobooksync/.venv/bin/celery \
    -A src.celery_app \
    beat \
    -l info \
    --logfile=/var/log/audiobooksync/celery-beat.log
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Enable and Start Services

```bash
# Enable services to start on boot
sudo systemctl enable audiobooksync-app.service
sudo systemctl enable audiobooksync-celery-worker.service
sudo systemctl enable audiobooksync-celery-beat.service

# Start services
sudo systemctl start audiobooksync-app.service
sudo systemctl start audiobooksync-celery-worker.service
sudo systemctl start audiobooksync-celery-beat.service

# Check status
sudo systemctl status audiobooksync-app.service
sudo systemctl status audiobooksync-celery-worker.service
sudo systemctl status audiobooksync-celery-beat.service
```

### Using Docker Compose (Production-like)

#### `docker-compose.prod.yml`

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: audiobooksync-redis-prod
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: audiobooksync-app-prod
    environment:
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
      - USE_CELERY_TASKS=true
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
    depends_on:
      redis:
        condition: service_healthy
      postgres:
        condition: service_healthy
    ports:
      - "8000:8000"
    restart: unless-stopped

  celery-worker:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: audiobooksync-celery-worker-prod
    command: celery -A src.celery_app worker -l info --concurrency=4
    environment:
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped

  celery-beat:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: audiobooksync-celery-beat-prod
    command: celery -A src.celery_app beat -l info
    environment:
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped

volumes:
  redis_data:
```

#### Deploy

```bash
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml ps
```

## Monitoring

### Check Task Queue Depth

```bash
# Using Celery CLI
celery -A src.celery_app inspect active

# Using Redis
redis-cli
> LLEN celery

# Watch in real-time
watch -n 1 'redis-cli LLEN celery'
```

### Check Worker Status

```bash
# Active workers
celery -A src.celery_app inspect active_queues

# Worker stats
celery -A src.celery_app inspect stats

# Currently executing tasks
celery -A src.celery_app inspect active
```

### Monitor Scheduled Tasks

```bash
# Check Beat schedule
celery -A src.celery_app inspect scheduled

# Watch Beat logs
tail -f /var/log/audiobooksync/celery-beat.log
```

### Redis Memory Usage

```bash
redis-cli
> INFO memory
```

## Troubleshooting

### No tasks executing

1. Check `USE_CELERY_TASKS` is `true`:
   ```bash
   echo $USE_CELERY_TASKS
   ```

2. Check worker is running:
   ```bash
   celery -A src.celery_app inspect active_queues
   ```

3. Check Redis connection:
   ```bash
   redis-cli ping
   ```

4. Check application logs for task enqueue errors

### High Redis memory usage

1. Check for tasks stuck in queue:
   ```bash
   redis-cli LLEN celery
   ```

2. Check result retention:
   ```bash
   redis-cli DBSIZE
   redis-cli --scan | wc -l
   ```

3. Clear old results:
   ```bash
   redis-cli FLUSHDB  # WARNING: clears all data
   ```

### Worker crashes frequently

1. Check worker logs for errors
2. Increase time limit if tasks timeout:
   ```bash
   CELERY_TASK_TIME_LIMIT=14400  # 4 hours
   ```

3. Check system resources (memory, CPU)

### WebSocket not receiving progress updates

1. Verify Redis pub/sub working:
   ```bash
   redis-cli
   > SUBSCRIBE ws:user:test-user
   ```

2. Manually publish test message:
   ```bash
   redis-cli
   > PUBLISH ws:user:test-user '{"type":"test","data":{"msg":"hello"}}'
   ```

3. Check WebSocket manager logs for Redis errors

## Performance Tuning

### Worker Concurrency

Adjust based on CPU cores and task type:

```bash
# CPU-bound tasks
celery -A src.celery_app worker --concurrency=<cpu_count>

# IO-bound tasks (downloads, etc.)
celery -A src.celery_app worker --concurrency=16 --pool=solo
```

### Task Time Limits

Increase for long-running operations:

```bash
CELERY_TASK_TIME_LIMIT=14400      # 4 hours
CELERY_TASK_SOFT_TIME_LIMIT=13800  # 3 hr 50 min
```

### Redis Connection Pooling

For high-traffic scenarios:

```bash
CELERY_BROKER_POOL_LIMIT=10
CELERY_RESULT_BACKEND_POOL_LIMIT=10
```

## Backup Strategy

### Redis Persistence

Ensure Redis uses AOF (Append-Only File) for data persistence:

```bash
# In Redis config
appendonly yes
appendfsync everysec
```

### Backup Redis Data

```bash
# Manual backup
redis-cli BGSAVE
# Creates: dump.rdb

# Automated backup
redis-cli CONFIG SET save "900 1 300 10 60 10000"
# Saves if: 900s with 1 change, 300s with 10 changes, 60s with 10000 changes
```

## Monitoring with Flower (Optional)

```bash
# Install Flower
pip install flower

# Start Flower
celery -A src.celery_app flower

# Access at http://localhost:5555
```

## Security Considerations

1. **Redis**: Require password authentication
2. **Celery**: Don't allow pickle serialization (use JSON)
3. **Tasks**: Validate all input data
4. **Logs**: Don't log sensitive data (passwords, tokens)
5. **Network**: Keep Redis on private network, don't expose to internet

## Scaling Considerations

1. **Single worker**: Use for development and small deployments
2. **Multiple workers**: Scale horizontally by adding more worker processes
3. **Load balancing**: Use task routing for different task types
4. **Database**: May need connection pooling for high concurrency

## Rollback Procedure

If issues occur with Celery:

1. Set `USE_CELERY_TASKS=false`
2. Restart FastAPI application
3. Stop Celery worker and beat
4. Application reverts to FastAPI BackgroundTasks immediately

## Verification Checklist

- [ ] Redis service running and accessible
- [ ] Celery worker running and accepting tasks
- [ ] Celery beat scheduler running
- [ ] `USE_CELERY_TASKS=true` in environment
- [ ] Task logs showing execution
- [ ] WebSocket progress updates working
- [ ] Scheduled tasks executing on schedule
- [ ] Redis memory usage reasonable
- [ ] No task timeouts occurring

## Support

For issues or questions:
1. Check logs: `docker-compose logs <service>`
2. Verify configuration in `.env` and `config.py`
3. Test Redis connection directly
4. Review Celery documentation for specific errors
