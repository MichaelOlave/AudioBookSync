# AudioBookSync Production Deployment Guide

## Overview

This guide covers deploying AudioBookSync backend to your home lab with:
- Vercel frontend running at `https://your-frontend.vercel.app`
- Home lab API running at `https://api.example.com`
- Nginx reverse proxy handling CORS and SSL/TLS
- Docker Compose orchestration

---

## Prerequisites

### On Your Home Lab Server

- **Docker & Docker Compose** installed
- **Domain name** pointing to your home lab's public IP (e.g., `api.example.com`)
- **SSL Certificate** from Let's Encrypt (free) or your CA
- **Port forwarding** configured:
  - Port 80 (HTTP) → Server port 80
  - Port 443 (HTTPS) → Server port 443
- **Firewall rules** allowing inbound traffic on ports 80/443

### On Your Local Development Machine

- This repository cloned
- Changes committed to git

---

## Step 1: Set Up Domain & DNS

### Option A: Using Let's Encrypt (Recommended)

1. **Generate SSL certificates** on your home lab server:

```bash
sudo apt-get install certbot python3-certbot-nginx  # Ubuntu/Debian
# or
brew install certbot  # macOS

# Generate certificate
sudo certbot certonly --standalone -d api.example.com

# Certificates will be at:
# /etc/letsencrypt/live/api.example.com/fullchain.pem
# /etc/letsencrypt/live/api.example.com/privkey.pem
```

2. **Create certificate directory** in your project:

```bash
mkdir -p certs
sudo cp /etc/letsencrypt/live/api.example.com/fullchain.pem certs/
sudo cp /etc/letsencrypt/live/api.example.com/privkey.pem certs/
sudo chown $USER:$USER certs/*
chmod 600 certs/privkey.pem
```

3. **Auto-renewal setup** (optional but recommended):

```bash
# Add to crontab
0 2 * * * certbot renew --quiet && cp /etc/letsencrypt/live/api.example.com/* /path/to/project/certs/
```

---

## Step 2: Configure Environment Variables

1. **Copy and edit the production env file:**

```bash
cp .env.production .env
```

2. **Update critical values:**

```bash
# Generate secure random values
openssl rand -hex 32  # For SECRET_KEY

# Edit .env file
nano .env
```

**Required changes in `.env`:**

```env
# Database password - strong password!
POSTGRES_PASSWORD=YourStrongPasswordHere123!

# Security - generate new with: openssl rand -hex 32
SECRET_KEY=your_generated_random_hex_string

# Your Vercel frontend domain
CORS_ORIGINS=https://your-frontend.vercel.app

# MinIO credentials
MINIO_ACCESS_KEY=YourStrongMinIOKey123!
MINIO_SECRET_KEY=YourStrongMinIOSecret123!

# Your actual domain
# (Note: This is configured in nginx-production.conf)
```

3. **Update nginx configuration:**

Edit `.devcontainer/nginx-production.conf` and replace:
- `api.example.com` with your actual domain (2 occurrences)
- `https://your-frontend.vercel.app` with your Vercel frontend URL (3 occurrences)

```bash
# Find and replace
sed -i 's/api.example.com/your-actual-domain.com/g' .devcontainer/nginx-production.conf
sed -i 's/https:\/\/your-frontend.vercel.app/https:\/\/your-vercel-app.vercel.app/g' .devcontainer/nginx-production.conf
```

---

## Step 3: Prepare Your Home Lab Server

### Copy project to home lab:

```bash
# On your local machine
git push origin main

# On home lab server
git clone <your-repo-url>
cd AudioBookSync

# Copy certificates
mkdir -p certs
# Copy your Let's Encrypt certificates here
cp /path/to/fullchain.pem certs/
cp /path/to/privkey.pem certs/
```

### Create required directories:

```bash
mkdir -p audiobooks/{downloaded,decrypted}
mkdir -p logs
mkdir -p auth  # For Audible auth.json
```

---

## Step 4: Deploy

### Start all services:

```bash
# Pull latest code
git pull origin main

# Load environment
source .env

# Start the stack
docker-compose -f docker-compose.production.yml up -d

# Check status
docker-compose -f docker-compose.production.yml ps

# View logs
docker-compose -f docker-compose.production.yml logs -f nginx
```

### Verify services are healthy:

```bash
# Check all services
docker-compose -f docker-compose.production.yml logs nginx postgres redis minio

# Test API is responding
curl https://api.example.com/api/v1/health

# Test MinIO is responding
curl https://api.example.com/minio/

# Check health endpoint
curl https://api.example.com/health
```

---

## Step 5: Configure Frontend (Vercel)

### Update your Vercel environment variables:

In Vercel project settings, set:

```
VITE_API_BASE_URL=https://api.example.com/api/v1
VITE_MINIO_ENDPOINT=https://api.example.com/minio
```

Or update your frontend code to use:

```javascript
const API_URL = 'https://api.example.com/api/v1'
const MINIO_URL = 'https://api.example.com/minio'
```

### Test CORS:

Your frontend should now be able to call:
```javascript
fetch('https://api.example.com/api/v1/auth/login', {
  method: 'POST',
  credentials: 'include',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email, password })
})
```

---

## Step 6: Database Migrations

### Run migrations after first deployment:

```bash
# Access the app container
docker-compose -f docker-compose.production.yml exec app bash

# Run migrations
alembic upgrade head

# Exit container
exit
```

---

## Monitoring & Maintenance

### View logs:

```bash
# All services
docker-compose -f docker-compose.production.yml logs -f

# Specific service
docker-compose -f docker-compose.production.yml logs -f app
docker-compose -f docker-compose.production.yml logs -f nginx
docker-compose -f docker-compose.production.yml logs -f postgres
```

### Stop and restart:

```bash
# Stop all
docker-compose -f docker-compose.production.yml down

# Start all
docker-compose -f docker-compose.production.yml up -d

# Restart specific service
docker-compose -f docker-compose.production.yml restart app
```

### Backup database:

```bash
# Backup PostgreSQL
docker-compose -f docker-compose.production.yml exec postgres \
  pg_dump -U postgres audiobooksync > backup-$(date +%Y%m%d).sql

# Backup MinIO data
docker run --rm -v audiobooksync_minio_data:/data -v $(pwd)/backups:/backups \
  alpine tar czf /backups/minio-$(date +%Y%m%d).tar.gz -C /data .
```

---

## Troubleshooting

### Frontend can't reach API

1. **Check CORS headers:**
```bash
curl -i -H "Origin: https://your-frontend.vercel.app" \
  https://api.example.com/api/v1/health
```

2. **Check nginx config loaded correctly:**
```bash
docker-compose -f docker-compose.production.yml exec nginx nginx -t
```

3. **Verify domain resolves:**
```bash
nslookup api.example.com
# Should return your home lab's public IP
```

### SSL certificate issues

```bash
# Check certificate validity
openssl x509 -in certs/fullchain.pem -text -noout

# Verify key matches certificate
openssl pkey -in certs/privkey.pem -check

# Test SSL connection
openssl s_client -connect api.example.com:443
```

### Services not starting

```bash
# Check logs
docker-compose -f docker-compose.production.yml logs

# Rebuild containers
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml build --no-cache
docker-compose -f docker-compose.production.yml up -d
```

### Database connection errors

```bash
# Check PostgreSQL is ready
docker-compose -f docker-compose.production.yml exec postgres \
  pg_isready -U postgres -d audiobooksync

# Check logs
docker-compose -f docker-compose.production.yml logs postgres
```

---

## Security Checklist

- [ ] Changed `SECRET_KEY` to a new random value
- [ ] Changed `POSTGRES_PASSWORD` to a strong password
- [ ] Changed MinIO credentials
- [ ] Updated CORS_ORIGINS to your actual Vercel domain
- [ ] Updated nginx config with your actual domain
- [ ] Set up SSL certificate auto-renewal
- [ ] Configured firewall to allow only ports 80/443
- [ ] Disabled public access to MinIO console (only through /console/ path)
- [ ] Set up automated backups for PostgreSQL and MinIO
- [ ] Reviewed logs for errors/security issues

---

## Architecture

```
Vercel Frontend (https://your-frontend.vercel.app)
            ↓
    [Internet]
            ↓
Home Lab Server
    Nginx (443)
    ├─→ /api/* → FastAPI (8000)
    ├─→ /minio/* → MinIO S3 (9000)
    └─→ CORS headers configured

Behind Nginx:
    - PostgreSQL (5432)
    - Redis (6379)
    - MinIO (9000/9001)
    - Celery Worker
    - Celery Beat
```

---

## Support

For issues with:
- **Deployment**: Check docker logs: `docker-compose -f docker-compose.production.yml logs`
- **SSL**: Check Let's Encrypt renewal and certificate paths
- **CORS**: Verify nginx config has correct Vercel domain
- **Database**: Check PostgreSQL is running and accessible
