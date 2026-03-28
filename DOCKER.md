# 🐳 FlavorSnap Docker Configuration

This document provides comprehensive guidance for deploying FlavorSnap using Docker with production-ready configurations, security hardening, and environment-specific optimizations.

## 📋 Table of Contents

- [🏗️ Architecture Overview](#️-architecture-overview)
- [🚀 Quick Start](#-quick-start)
- [⚙️ Configuration](#️-configuration)
- [🔒 Security Features](#-security-features)
- [🌍 Environment-Specific Deployments](#-environment-specific-deployments)
- [📊 Monitoring and Health Checks](#-monitoring-and-health-checks)
- [🛠️ Development Workflow](#️-development-workflow)
- [🔧 Troubleshooting](#-troubleshooting)
- [📈 Performance Optimization](#-performance-optimization)

## 🏗️ Architecture Overview

### Multi-Stage Builds

Our Docker configuration uses multi-stage builds for optimal image size and security:

#### Frontend (Next.js)
- **Build Stage**: Compiles Next.js application with all dependencies
- **Runtime Stage**: Minimal Alpine Linux with only production dependencies

#### Backend (Flask ML API)
- **Dependencies Stage**: Installs Python packages and build tools
- **Production Stage**: Minimal runtime with security hardening

### Services

1. **Frontend**: Next.js application (port 3000)
2. **Backend**: Flask ML inference API (port 5000)
3. **Nginx**: Reverse proxy with SSL termination (port 80/443) - Production only

## 🚀 Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ RAM available
- `model.pth` file in project root

### Production Deployment

```bash
# Using the deployment script (recommended)
./scripts/docker-deploy.sh production full

# Or manually
cp .env.docker .env
docker-compose build
docker-compose up -d
```

### Development Deployment

```bash
# Using the deployment script
./scripts/docker-deploy.sh development full

# Or manually
docker-compose -f docker-compose.dev.yml up -d
```

### Windows PowerShell

```powershell
# Production deployment
.\scripts\docker-deploy.ps1 -Environment production -Command full

# Development deployment
.\scripts\docker-deploy.ps1 -Environment development -Command start
```

## ⚙️ Configuration

### Environment Variables

Copy `.env.docker` to `.env` and customize:

```bash
# Build Configuration
BUILD_ENV=production

# Frontend Configuration
FRONTEND_PORT=3000
NEXT_PUBLIC_API_URL=http://backend:5000
NEXT_PUBLIC_MODEL_ENDPOINT=/predict

# Backend Configuration
BACKEND_PORT=5000
MODEL_PATH=/app/models/model.pth
UPLOAD_FOLDER=/app/uploads
LOG_LEVEL=INFO
MAX_CONTENT_LENGTH=16777216

# Nginx Configuration (Production Only)
NGINX_PORT=80
NGINX_HTTPS_PORT=443

# Resource Limits
FRONTEND_MEMORY_LIMIT=512M
BACKEND_MEMORY_LIMIT=2G
FRONTEND_CPU_LIMIT=1.0
BACKEND_CPU_LIMIT=2.0
```

### SSL Configuration (Production)

1. Place SSL certificates in `nginx/ssl/`:
   - `cert.pem` - SSL certificate
   - `key.pem` - Private key

2. Update environment variables:
```bash
SSL_CERT_PATH=/etc/nginx/ssl/cert.pem
SSL_KEY_PATH=/etc/nginx/ssl/key.pem
```

## 🔒 Security Features

### Container Security

- **Non-root users**: All containers run as non-root users
- **Read-only filesystem**: Frontend container runs read-only
- **Capability dropping**: Unnecessary Linux capabilities are dropped
- **Security options**: `no-new-privileges:true` prevents privilege escalation
- **Resource limits**: CPU and memory limits prevent resource exhaustion

### Network Security

- **Isolated networks**: Services communicate via private Docker network
- **Rate limiting**: Nginx provides rate limiting for API endpoints
- **Security headers**: OWASP-recommended security headers
- **CORS protection**: Configurable CORS origins

### File Security

- **Minimal attack surface**: Only necessary files included in images
- **Secure file permissions**: Proper ownership and permissions
- **Docker ignore**: Sensitive files excluded from build context

## 🌍 Environment-Specific Deployments

### Production Environment

Features:
- Nginx reverse proxy
- SSL termination
- Rate limiting
- Security headers
- Resource limits
- Health checks
- Read-only filesystem where possible

```bash
docker-compose --profile production up -d
```

### Development Environment

Features:
- Hot reloading
- Debug mode
- Volume mounts for live code changes
- Development dependencies
- Relaxed security for debugging

```bash
docker-compose -f docker-compose.dev.yml up -d
```

## 📊 Monitoring and Health Checks

### Health Check Endpoints

- **Frontend**: `GET /` - Returns 200 if application is running
- **Backend**: `GET /health` - Returns model status and health
- **Nginx**: `GET /health` - Simple health check endpoint

### Health Check Configuration

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

### Monitoring Commands

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f

# View resource usage
docker stats

# Health check details
docker inspect --format='{{.State.Health}}' container_name
```

## 🛠️ Development Workflow

### Local Development

1. **Start development environment**:
```bash
./scripts/docker-deploy.sh development start
```

2. **Live reloading**:
   - Frontend changes: Automatically reload via Next.js
   - Backend changes: Restart container or use volume mounts

3. **Debugging**:
```bash
# Attach to container
docker-compose exec backend bash
docker-compose exec frontend sh

# View logs in real-time
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Building Images

```bash
# Build all images
docker-compose build

# Build specific service
docker-compose build frontend
docker-compose build backend

# Build with no cache
docker-compose build --no-cache
```

### Testing

```bash
# Run tests in containers
docker-compose exec backend python -m pytest
docker-compose exec frontend npm test

# Integration tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

## 🔧 Troubleshooting

### Common Issues

#### Container Won't Start

```bash
# Check logs
docker-compose logs service_name

# Check configuration
docker-compose config

# Check resource usage
docker system df
docker system prune
```

#### Model Loading Issues

```bash
# Check model file
docker-compose exec backend ls -la /app/models/

# Check model integrity
docker-compose exec backend python -c "import torch; print(torch.load('/app/models/model.pth').keys())"
```

#### Permission Issues

```bash
# Fix file permissions
sudo chown -R 1001:1001 uploads/
sudo chmod -R 755 uploads/
```

#### Network Issues

```bash
# Check network connectivity
docker-compose exec frontend ping backend
docker-compose exec backend ping frontend

# Check port binding
docker-compose port backend 5000
docker-compose port frontend 3000
```

### Performance Issues

```bash
# Monitor resource usage
docker stats --no-stream

# Check image sizes
docker images

# Optimize images
docker-compose build --no-cache --parallel
```

## 📈 Performance Optimization

### Image Size Optimization

- **Multi-stage builds**: Reduce final image size by ~70%
- **Alpine Linux**: Minimal base images
- **.dockerignore**: Exclude unnecessary files
- **Dependency caching**: Optimize layer caching

### Runtime Performance

- **Resource limits**: Prevent resource contention
- **Health checks**: Automatic restart on failure
- **Connection pooling**: Nginx upstream connection pooling
- **Gzip compression**: Reduce bandwidth usage

### Caching Strategy

- **Static assets**: Long-term caching (1 year)
- **API responses**: Configure appropriate cache headers
- **Docker layer caching**: Optimize build order

### Scaling

```bash
# Scale services
docker-compose up -d --scale backend=3 --scale frontend=2

# Production scaling with load balancer
docker-compose --profile production up -d --scale backend=3
```

## 🔄 CI/CD Integration

### GitHub Actions Example

```yaml
name: Docker Build and Deploy

on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker images
        run: |
          docker-compose build
          
      - name: Run tests
        run: |
          docker-compose -f docker-compose.test.yml up --abort-on-container-exit
          
      - name: Deploy to production
        run: |
          ./scripts/docker-deploy.sh production full
```

## 📝 Best Practices

1. **Always use specific image tags** (avoid `latest`)
2. **Regularly update base images** for security patches
3. **Monitor resource usage** and adjust limits accordingly
4. **Implement proper logging** for debugging and monitoring
5. **Use environment-specific configurations**
6. **Test disaster recovery procedures**
7. **Implement proper backup strategies** for data volumes

## 🆘 Support

For Docker-related issues:

1. Check the troubleshooting section above
2. Review container logs: `docker-compose logs`
3. Check system resources: `docker system df`
4. Verify configuration: `docker-compose config`

For application issues, refer to the main README.md file.

---

**Note**: This Docker configuration is designed for production use with security best practices. For development, use the development-specific compose file for better debugging experience.
