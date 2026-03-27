# CI/CD Pipeline Documentation

This document provides comprehensive information about the FlavorSnap CI/CD pipeline configuration, setup, and usage.

## Overview

FlavorSnap uses a comprehensive CI/CD pipeline with automated testing, security scanning, container builds, and deployment to Kubernetes clusters. The pipeline is implemented using GitHub Actions and consists of three main workflows:

1. **CI Pipeline** (`.github/workflows/ci.yml`) - Continuous Integration
2. **Deploy Pipeline** (`.github/workflows/deploy.yml`) - Continuous Deployment
3. **Release Pipeline** (`.github/workflows/release.yml`) - Release Management

## Table of Contents

- [CI Pipeline](#ci-pipeline)
- [Deploy Pipeline](#deploy-pipeline)
- [Release Pipeline](#release-pipeline)
- [Security Scanning](#security-scanning)
- [Environment Configuration](#environment-configuration)
- [Manual Triggers](#manual-triggers)
- [Monitoring and Observability](#monitoring-and-observability)

---

## CI Pipeline

**File:** `.github/workflows/ci.yml`

### Triggers
- Pull requests to `main`, `master`, or `develop` branches
- Push to `main`, `master`, or `develop` branches
- Manual trigger via GitHub UI (workflow_dispatch)
- Scheduled daily runs at 3:00 AM UTC

### Jobs

#### 1. Code Quality & Linting (`lint-and-quality`)
- **Purpose:** Ensures code quality and consistency
- **Steps:**
  - Python linting (Black, Flake8, Pylint)
  - Frontend linting (ESLint)
  - Static analysis (MyPy)
- **Duration:** ~30 minutes timeout

#### 2. Tests (`tests`)
- **Purpose:** Run unit tests, integration tests, and performance benchmarks
- **Services:** PostgreSQL and Redis containers for integration testing
- **Features:**
  - Code coverage reporting
  - Performance smoke tests (on PR/push)
  - Full performance benchmarks (scheduled runs)
- **Duration:** ~90 minutes timeout
- **Dependencies:** Requires `lint-and-quality` to pass

#### 3. Build Frontend (`build-frontend`)
- **Purpose:** Build and cache frontend assets
- **Steps:**
  - Install Node.js dependencies
  - Create production build
  - Upload build artifacts
- **Duration:** ~30 minutes timeout

#### 4. Build Docker Images (`build-docker`)
- **Purpose:** Build and push Docker images to GitHub Container Registry
- **Triggers:** Only on push to `main` branch
- **Features:**
  - Multi-stage builds
  - Layer caching for faster builds
  - Automatic tagging with SHA and `latest`
- **Duration:** ~60 minutes timeout
- **Dependencies:** Requires `tests` and `build-frontend` to pass

### Artifacts
- Coverage reports (XML and HTML)
- Frontend build artifacts
- Security scan results

---

## Deploy Pipeline

**File:** `.github/workflows/deploy.yml`

### Triggers
- Push to `main` or `master` branches
- Version tags (e.g., `v1.0.0`)
- Manual trigger with environment selection

### Jobs

#### 1. Build and Push (`build-and-push`)
- **Purpose:** Build Docker image and push to registry
- **Features:**
  - Automatic version detection from tags or commit SHA
  - Vulnerability scanning with Trivy
  - Upload scan results to GitHub Security tab
- **Outputs:** Image tag and version number

#### 2. Deploy to Staging (`deploy-staging`)
- **Purpose:** Deploy to staging environment for validation
- **Triggers:** 
  - Manual deployment to staging
  - Automatic on push to `main`
- **Features:**
  - Kubernetes rolling update
  - Health check verification
  - Smoke tests
- **Environment:** `staging`

#### 3. Deploy to Production (`deploy-production`)
- **Purpose:** Deploy to production environment
- **Triggers:**
  - Manual deployment to production
  - Automatic on version tag push
- **Features:**
  - Requires successful staging deployment
  - Kubernetes rolling update
  - Deployment verification
  - Automatic backup creation
- **Environment:** `production`

#### 4. Notify (`notify`)
- **Purpose:** Send deployment notifications
- **Triggers:** Always runs after deployment jobs

### Required Secrets
```bash
# GitHub Repository Secrets needed:
KUBE_CONFIG_DATA_STAGING    # Base64 encoded kubeconfig for staging
KUBE_CONFIG_DATA_PRODUCTION # Base64 encoded kubeconfig for production
```

### Environment Protection Rules
Configure in GitHub Settings → Environments:
- **staging:** Allow specified deployers
- **production:** Require reviewers, delay deployment

---

## Release Pipeline

**File:** `.github/workflows/release.yml`

### Triggers
- Version tags (e.g., `v1.0.0`, `v2.1.3`)
- Manual trigger with version input

### Jobs

#### 1. Validate Version (`validate-version`)
- **Purpose:** Ensure version format and uniqueness
- **Validation:** Semantic versioning (X.Y.Z)
- **Output:** Validated version string

#### 2. Generate Changelog (`generate-changelog`)
- **Purpose:** Automatically create release notes
- **Features:**
  - Extract commits since last tag
  - List contributors
  - Categorize changes
- **Output:** Markdown changelog

#### 3. Build Release Artifacts (`build-release-artifacts`)
- **Purpose:** Create distributable packages
- **Artifacts:**
  - Frontend distribution (`.tar.gz`)
  - Python package (`.tar.gz`)
- **Duration:** ~60 minutes timeout

#### 4. Build Docker Images (`build-docker-images`)
- **Purpose:** Create and push release Docker images
- **Tags:** Version-specific and `latest`

#### 5. Create Release (`create-release`)
- **Purpose:** Publish GitHub release with artifacts
- **Features:**
  - Draft mode for review (optional)
  - Automatic asset upload
  - Installation instructions

### Usage Example
```bash
# Create and push a new release tag
git tag v1.0.0
git push origin v1.0.0

# Or use GitHub UI to manually trigger workflow
```

---

## Security Scanning

**File:** `.github/workflows/security.yml`

### Scan Types

#### Python Security Scan
- **Tools:** Safety, Bandit, Semgrep
- **Coverage:** Dependencies, code vulnerabilities, secrets

#### Rust Security Scan
- **Tools:** Cargo Audit, Clippy
- **Coverage:** Dependency vulnerabilities, code quality

#### Secret Scanning
- **Tools:** TruffleHog, Gitleaks
- **Coverage:** Committed secrets and API keys

#### Docker Security Scan
- **Tools:** Trivy
- **Coverage:** Container vulnerabilities

### Schedule
- Daily scans at 2:00 AM UTC
- On every push to protected branches
- On pull requests

---

## Environment Configuration

### Production Docker Compose

**File:** `docker-compose.prod.yml`

#### Services
- **Frontend:** Next.js application (3 replicas)
- **Backend:** Flask ML API (2 replicas)
- **Nginx:** Reverse proxy with SSL termination
- **PostgreSQL:** Primary database
- **Redis:** Caching layer
- **Prometheus:** Metrics collection
- **Grafana:** Monitoring dashboards

#### Health Checks
All services include health checks:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

#### Resource Limits
Each service has defined resource constraints:
```yaml
deploy:
  resources:
    limits:
      memory: 2G
      cpus: '1.0'
    reservations:
      memory: 1G
      cpus: '0.5'
```

### Kubernetes Deployment

**File:** `kubernetes/deployment.yaml`

#### Components
- Namespace: `flavorsnap`
- ConfigMaps for environment variables
- Secrets for sensitive data
- Deployments with auto-scaling (HPA)
- Services for internal communication
- Ingress with TLS termination

#### Auto-scaling Configuration
```yaml
spec:
  minReplicas: 2
  maxReplicas: 5
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        averageUtilization: 70
```

---

## Manual Triggers

### Deploy to Specific Environment

1. Go to GitHub repository
2. Navigate to **Actions** tab
3. Select **Deploy to Production** workflow
4. Click **Run workflow**
5. Choose:
   - Environment: `staging` or `production`
   - Version (optional, defaults to latest)
6. Click **Run workflow**

### Create Manual Release

1. Go to **Actions** tab
2. Select **Create Release** workflow
3. Click **Run workflow**
4. Enter version (e.g., `v1.2.3`)
5. Set dry run option if needed
6. Click **Run workflow**

---

## Monitoring and Observability

### Prometheus Metrics
- Request rate and latency
- Error rates
- Resource utilization
- Custom business metrics

### Grafana Dashboards
- System overview
- Application performance
- Database metrics
- Cache performance

### Alerting
Configured in `monitoring/alert_rules.yml`:
- High error rate (>5%)
- High response time (>2s)
- Low disk space (<20%)
- Service down

### Log Aggregation
- Application logs: `/app/logs`
- Nginx logs: `/var/log/nginx`
- Access logs with request details
- Error logs with stack traces

---

## Troubleshooting

### Common Issues

#### Build Failures
1. Check workflow logs in GitHub Actions
2. Verify dependencies are correctly specified
3. Ensure Docker build context is correct

#### Deployment Failures
1. Check Kubernetes events: `kubectl get events -n flavorsnap`
2. Verify pod status: `kubectl get pods -n flavorsnap`
3. Review deployment logs: `kubectl describe deployment/<name>`

#### Test Failures
1. Download coverage artifacts from workflow
2. Run tests locally with same environment
3. Check service dependencies (PostgreSQL, Redis)

### Recovery Procedures

#### Rollback Deployment
```bash
# Kubernetes rollback
kubectl rollout undo deployment/frontend-deployment -n flavorsnap
kubectl rollout undo deployment/backend-deployment -n flavorsnap

# Or redeploy previous version via GitHub Actions
```

#### Database Backup/Restore
```bash
# Create backup
pg_dump -U flavorsnap flavorsnap > backup.sql

# Restore from backup
psql -U flavorsnap flavorsnap < backup.sql
```

---

## Best Practices

### Before Merging
- ✅ All CI checks must pass
- ✅ Code coverage maintained or improved
- ✅ Security scans show no critical issues
- ✅ Performance tests within acceptable range

### Deployment Checklist
- ✅ Staging deployment successful
- ✅ Smoke tests passing
- ✅ No critical errors in logs
- ✅ Backup completed successfully
- ✅ Rollback plan prepared

### Release Checklist
- ✅ Changelog reviewed and updated
- ✅ Version number follows semantic versioning
- ✅ All tests passing
- ✅ Documentation updated
- ✅ Migration scripts prepared (if needed)

---

## Support and Contribution

For issues or questions about the CI/CD pipeline:
- Open an issue on GitHub
- Contact the DevOps team
- Check workflow history in Actions tab

To contribute improvements:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

**Last Updated:** March 27, 2026  
**Version:** 1.0.0
