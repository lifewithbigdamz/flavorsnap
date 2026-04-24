#!/bin/bash

# Advanced CI/CD Deployment Script
# Handles multi-environment deployments with rollback capabilities

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_ROOT/config/deployment.json"

# Default values
ENVIRONMENT=${1:-staging}
VERSION=${2:-latest}
STRATEGY=${3:-rolling}
DRY_RUN=${4:-false}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Load configuration
load_config() {
    if [[ -f "$CONFIG_FILE" ]]; then
        log "Loading configuration from $CONFIG_FILE"
        # Source the configuration (assuming it's a bash script or can be sourced)
        source "$CONFIG_FILE"
    else
        warning "Configuration file not found: $CONFIG_FILE"
        log "Using default configuration"
    fi
}

# Validate inputs
validate_inputs() {
    log "Validating deployment parameters..."
    
    if [[ -z "$ENVIRONMENT" ]]; then
        error "Environment must be specified"
        exit 1
    fi
    
    if [[ -z "$VERSION" ]]; then
        error "Version must be specified"
        exit 1
    fi
    
    valid_environments=("staging" "production" "development")
    if [[ ! " ${valid_environments[@]} " =~ " $ENVIRONMENT " ]]; then
        error "Invalid environment: $ENVIRONMENT. Valid environments: ${valid_environments[*]}"
        exit 1
    fi
    
    valid_strategies=("rolling" "blue_green" "canary")
    if [[ ! " ${valid_strategies[@]} " =~ " $STRATEGY " ]]; then
        error "Invalid strategy: $STRATEGY. Valid strategies: ${valid_strategies[*]}"
        exit 1
    fi
    
    success "Input validation passed"
}

# Pre-deployment checks
pre_deployment_checks() {
    log "Running pre-deployment checks..."
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        error "Docker is not running"
        exit 1
    fi
    
    # Check if kubectl is available (for Kubernetes deployments)
    if command -v kubectl &> /dev/null; then
        log "kubectl is available"
    else
        warning "kubectl not found - Kubernetes deployments may not work"
    fi
    
    # Check if required environment variables are set
    required_vars=("AWS_ACCESS_KEY_ID" "AWS_SECRET_ACCESS_KEY")
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    # Check if the version exists
    if [[ "$VERSION" != "latest" ]]; then
        if ! docker manifest inspect "$REGISTRY/$IMAGE_NAME:$VERSION" > /dev/null 2>&1; then
            error "Docker image $REGISTRY/$IMAGE_NAME:$VERSION not found"
            exit 1
        fi
    fi
    
    success "Pre-deployment checks passed"
}

# Backup current deployment
backup_deployment() {
    log "Creating backup of current deployment..."
    
    backup_dir="$PROJECT_ROOT/backups/$(date +%Y%m%d_%H%M%S)_$ENVIRONMENT"
    mkdir -p "$backup_dir"
    
    # Backup current Docker Compose file
    if [[ -f "$PROJECT_ROOT/docker-compose.yml" ]]; then
        cp "$PROJECT_ROOT/docker-compose.yml" "$backup_dir/"
    fi
    
    # Backup environment-specific configuration
    env_config="$PROJECT_ROOT/config/$ENVIRONMENT.env"
    if [[ -f "$env_config" ]]; then
        cp "$env_config" "$backup_dir/"
    fi
    
    # Get current running services
    if command -v docker-compose &> /dev/null; then
        docker-compose ps > "$backup_dir/current_services.txt" 2>&1 || true
    fi
    
    success "Backup created at $backup_dir"
    echo "$backup_dir"
}

# Health check function
health_check() {
    local service_url="$1"
    local max_attempts=30
    local attempt=1
    
    log "Performing health check on $service_url"
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f -s "$service_url/health" > /dev/null 2>&1; then
            success "Health check passed (attempt $attempt/$max_attempts)"
            return 0
        fi
        
        log "Health check failed (attempt $attempt/$max_attempts), retrying in 10 seconds..."
        sleep 10
        ((attempt++))
    done
    
    error "Health check failed after $max_attempts attempts"
    return 1
}

# Rolling deployment
rolling_deploy() {
    log "Starting rolling deployment to $ENVIRONMENT..."
    
    # Update Docker Compose with new image
    if [[ "$DRY_RUN" == "false" ]]; then
        # Pull new image
        log "Pulling new image: $REGISTRY/$IMAGE_NAME:$VERSION"
        docker pull "$REGISTRY/$IMAGE_NAME:$VERSION"
        
        # Update services one by one
        services=("api" "worker" "frontend")
        for service in "${services[@]}"; do
            log "Updating service: $service"
            
            # Scale up new service
            docker-compose up -d --no-deps --scale "$service=2" "$service"
            
            # Wait for new service to be healthy
            sleep 30
            
            # Scale down old service
            docker-compose up -d --no-deps --scale "$service=1" "$service"
            
            # Health check
            if ! health_check "http://localhost:8000"; then
                error "Health check failed for service $service"
                return 1
            fi
            
            success "Service $service updated successfully"
        done
    else
        log "DRY RUN: Would perform rolling deployment of $VERSION to $ENVIRONMENT"
    fi
    
    success "Rolling deployment completed"
}

# Blue-green deployment
blue_green_deploy() {
    log "Starting blue-green deployment to $ENVIRONMENT..."
    
    if [[ "$DRY_RUN" == "false" ]]; then
        # Create green environment
        green_compose="$PROJECT_ROOT/docker-compose.green.yml"
        cp "$PROJECT_ROOT/docker-compose.yml" "$green_compose"
        
        # Update green environment with new image
        sed -i "s|image: .*|image: $REGISTRY/$IMAGE_NAME:$VERSION|g" "$green_compose"
        
        # Start green environment
        log "Starting green environment..."
        docker-compose -f "$green_compose" up -d
        
        # Wait for green environment to be ready
        sleep 60
        
        # Health check on green environment
        if ! health_check "http://localhost:8001"; then
            error "Green environment health check failed"
            docker-compose -f "$green_compose" down
            return 1
        fi
        
        # Switch traffic to green
        log "Switching traffic to green environment..."
        # This would involve updating load balancer configuration
        # For demo purposes, we'll just stop blue and keep green
        
        # Stop blue environment
        docker-compose down
        
        # Rename green to blue
        mv "$green_compose" "$PROJECT_ROOT/docker-compose.yml"
        
        success "Traffic switched to green environment"
    else
        log "DRY RUN: Would perform blue-green deployment of $VERSION to $ENVIRONMENT"
    fi
    
    success "Blue-green deployment completed"
}

# Canary deployment
canary_deploy() {
    log "Starting canary deployment to $ENVIRONMENT..."
    
    if [[ "$DRY_RUN" == "false" ]]; then
        # Deploy canary version alongside current version
        canary_compose="$PROJECT_ROOT/docker-compose.canary.yml"
        cp "$PROJECT_ROOT/docker-compose.yml" "$canary_compose"
        
        # Update canary with new image
        sed -i "s|image: .*|image: $REGISTRY/$IMAGE_NAME:$VERSION|g" "$canary_compose"
        
        # Start canary with small percentage of traffic
        log "Starting canary deployment (10% traffic)..."
        docker-compose -f "$canary_compose" up -d --scale api=1
        
        # Monitor canary for a period
        log "Monitoring canary for 5 minutes..."
        sleep 300
        
        # Check canary health and metrics
        if ! health_check "http://localhost:8002"; then
            error "Canary deployment health check failed"
            docker-compose -f "$canary_compose" down
            return 1
        fi
        
        # If canary is successful, gradually increase traffic
        log "Canary successful, gradually increasing traffic..."
        docker-compose -f "$canary_compose" up -d --scale api=5
        
        # Final monitoring
        sleep 120
        
        # Replace old deployment
        docker-compose down
        mv "$canary_compose" "$PROJECT_ROOT/docker-compose.yml"
        docker-compose up -d
        
        success "Canary deployment completed and traffic fully migrated"
    else
        log "DRY RUN: Would perform canary deployment of $VERSION to $ENVIRONMENT"
    fi
}

# Post-deployment verification
post_deployment_verification() {
    log "Running post-deployment verification..."
    
    # Health check
    if ! health_check "http://localhost:8000"; then
        error "Post-deployment health check failed"
        return 1
    fi
    
    # Check service endpoints
    endpoints=("/health" "/api/health" "/api/version")
    for endpoint in "${endpoints[@]}"; do
        if ! curl -f -s "http://localhost:8000$endpoint" > /dev/null; then
            error "Endpoint $endpoint is not responding"
            return 1
        fi
    done
    
    # Check logs for errors
    error_count=$(docker-compose logs --since=5m api | grep -i error | wc -l)
    if [[ $error_count -gt 5 ]]; then
        warning "High error count detected: $error_count errors in last 5 minutes"
    fi
    
    success "Post-deployment verification passed"
}

# Rollback function
rollback() {
    local backup_dir="$1"
    
    log "Initiating rollback..."
    
    if [[ -z "$backup_dir" ]] || [[ ! -d "$backup_dir" ]]; then
        error "Invalid backup directory: $backup_dir"
        return 1
    fi
    
    # Stop current deployment
    docker-compose down
    
    # Restore Docker Compose file
    if [[ -f "$backup_dir/docker-compose.yml" ]]; then
        cp "$backup_dir/docker-compose.yml" "$PROJECT_ROOT/"
    fi
    
    # Restore environment configuration
    if [[ -f "$backup_dir/$ENVIRONMENT.env" ]]; then
        cp "$backup_dir/$ENVIRONMENT.env" "$PROJECT_ROOT/config/"
    fi
    
    # Restart services
    docker-compose up -d
    
    # Wait for services to be ready
    sleep 30
    
    # Health check
    if health_check "http://localhost:8000"; then
        success "Rollback completed successfully"
    else
        error "Rollback health check failed"
        return 1
    fi
}

# Notification function
send_notification() {
    local status="$1"
    local message="$2"
    
    log "Sending notification: $message"
    
    # Slack notification (if webhook URL is configured)
    if [[ -n "$SLACK_WEBHOOK_URL" ]]; then
        local color="good"
        if [[ "$status" == "failure" ]]; then
            color="danger"
        elif [[ "$status" == "warning" ]]; then
            color="warning"
        fi
        
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$message\", \"color\":\"$color\"}" \
            "$SLACK_WEBHOOK_URL" || true
    fi
    
    # Email notification (if configured)
    if [[ -n "$NOTIFICATION_EMAIL" ]] && command -v mail &> /dev/null; then
        echo "$message" | mail -s "Deployment $status for $ENVIRONMENT" "$NOTIFICATION_EMAIL" || true
    fi
}

# Main deployment function
deploy() {
    log "Starting deployment to $ENVIRONMENT with version $VERSION using $STRATEGY strategy"
    
    # Load configuration
    load_config
    
    # Validate inputs
    validate_inputs
    
    # Pre-deployment checks
    pre_deployment_checks
    
    # Create backup
    backup_dir=$(backup_deployment)
    
    # Perform deployment based on strategy
    case "$STRATEGY" in
        "rolling")
            if ! rolling_deploy; then
                error "Rolling deployment failed, initiating rollback..."
                rollback "$backup_dir"
                send_notification "failure" "Rolling deployment to $ENVIRONMENT failed and was rolled back"
                exit 1
            fi
            ;;
        "blue_green")
            if ! blue_green_deploy; then
                error "Blue-green deployment failed, initiating rollback..."
                rollback "$backup_dir"
                send_notification "failure" "Blue-green deployment to $ENVIRONMENT failed and was rolled back"
                exit 1
            fi
            ;;
        "canary")
            if ! canary_deploy; then
                error "Canary deployment failed, initiating rollback..."
                rollback "$backup_dir"
                send_notification "failure" "Canary deployment to $ENVIRONMENT failed and was rolled back"
                exit 1
            fi
            ;;
    esac
    
    # Post-deployment verification
    if ! post_deployment_verification; then
        error "Post-deployment verification failed, initiating rollback..."
        rollback "$backup_dir"
        send_notification "failure" "Deployment to $ENVIRONMENT failed verification and was rolled back"
        exit 1
    fi
    
    success "Deployment to $ENVIRONMENT completed successfully"
    send_notification "success" "Deployment to $ENVIRONMENT completed successfully with version $VERSION"
}

# Cleanup old backups
cleanup_backups() {
    log "Cleaning up old backups..."
    
    backup_dir="$PROJECT_ROOT/backups"
    if [[ -d "$backup_dir" ]]; then
        # Keep only the last 10 backups
        cd "$backup_dir"
        ls -t | tail -n +11 | xargs -r rm -rf
        success "Old backups cleaned up"
    fi
}

# Main script execution
main() {
    log "Deployment script started"
    log "Environment: $ENVIRONMENT"
    log "Version: $VERSION"
    log "Strategy: $STRATEGY"
    log "Dry Run: $DRY_RUN"
    
    # Trap to handle script interruption
    trap 'error "Script interrupted"; exit 1' INT TERM
    
    # Deploy
    deploy
    
    # Cleanup
    cleanup_backups
    
    success "Deployment script completed successfully"
}

# Help function
show_help() {
    echo "Usage: $0 [ENVIRONMENT] [VERSION] [STRATEGY] [DRY_RUN]"
    echo ""
    echo "Arguments:"
    echo "  ENVIRONMENT    Target environment (staging, production, development)"
    echo "  VERSION       Version to deploy (latest or specific version)"
    echo "  STRATEGY      Deployment strategy (rolling, blue_green, canary)"
    echo "  DRY_RUN       Run in dry-run mode (true/false)"
    echo ""
    echo "Examples:"
    echo "  $0 staging latest rolling"
    echo "  $0 production v1.2.3 blue_green"
    echo "  $0 production latest canary true"
}

# Check for help flag
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    show_help
    exit 0
fi

# Run main function
main
