#!/bin/bash

# Comprehensive Health Check Script
# Performs health checks on all system components

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_ROOT/logs/health-check.log"
ALERT_FILE="$PROJECT_ROOT/logs/alerts.log"

# Health check endpoints
SERVICES=(
    "api:http://localhost:8000/health"
    "oracle:http://localhost:8000/api/oracles/health"
    "zk-proofs:http://localhost:8000/api/zk/health"
    "monitoring:http://localhost:8000/monitoring/health"
)

# Thresholds
CPU_THRESHOLD=80
MEMORY_THRESHOLD=85
DISK_THRESHOLD=90
RESPONSE_TIME_THRESHOLD=5

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Create log directory
mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "$(dirname "$ALERT_FILE")"

# Alert function
send_alert() {
    local severity="$1"
    local service="$2"
    local message="$3"
    
    local alert_entry="[$(date +'%Y-%m-%d %H:%M:%S')] [$severity] $service: $message"
    echo "$alert_entry" | tee -a "$ALERT_FILE"
    
    # Send to monitoring system
    if command -v curl &> /dev/null; then
        curl -X POST "http://localhost:8000/monitoring/alerts" \
             -H "Content-Type: application/json" \
             -d "{\"severity\": \"$severity\", \"service\": \"$service\", \"message\": \"$message\"}" \
             2>/dev/null || true
    fi
    
    # Send Slack notification if webhook is configured
    if [[ -n "$SLACK_WEBHOOK_URL" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$alert_entry\"}" \
            "$SLACK_WEBHOOK_URL" 2>/dev/null || true
    fi
}

# Check service health
check_service_health() {
    local service_name="$1"
    local service_url="$2"
    
    log "Checking health of $service_name at $service_url"
    
    if ! command -v curl &> /dev/null; then
        error "curl not available, cannot check $service_name"
        return 1
    fi
    
    local start_time=$(date +%s.%N)
    local response_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$service_url" || echo "000")
    local end_time=$(date +%s.%N)
    local response_time=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "0")
    
    case "$response_code" in
        200)
            if (( $(echo "$response_time > $RESPONSE_TIME_THRESHOLD" | bc -l 2>/dev/null || echo 0) )); then
                warning "$service_name response time is high: ${response_time}s"
                send_alert "warning" "$service_name" "High response time: ${response_time}s"
                return 1
            else
                success "$service_name is healthy (response time: ${response_time}s)"
                return 0
            fi
            ;;
        000)
            error "$service_name is not responding"
            send_alert "critical" "$service_name" "Service not responding"
            return 2
            ;;
        *)
            error "$service_name returned HTTP $response_code"
            send_alert "critical" "$service_name" "HTTP error: $response_code"
            return 2
            ;;
    esac
}

# Check system resources
check_system_resources() {
    log "Checking system resources"
    
    # CPU usage
    if command -v top &> /dev/null; then
        local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//' 2>/dev/null || echo "0")
        if (( $(echo "$cpu_usage > $CPU_THRESHOLD" | bc -l 2>/dev/null || echo 0) )); then
            warning "High CPU usage: ${cpu_usage}%"
            send_alert "warning" "system" "High CPU usage: ${cpu_usage}%"
        else
            success "CPU usage is normal: ${cpu_usage}%"
        fi
    fi
    
    # Memory usage
    if command -v free &> /dev/null; then
        local memory_info=$(free -m | grep "Mem:")
        local total_memory=$(echo $memory_info | awk '{print $2}')
        local used_memory=$(echo $memory_info | awk '{print $3}')
        local memory_usage=$((used_memory * 100 / total_memory))
        
        if [[ $memory_usage -gt $MEMORY_THRESHOLD ]]; then
            warning "High memory usage: ${memory_usage}%"
            send_alert "warning" "system" "High memory usage: ${memory_usage}%"
        else
            success "Memory usage is normal: ${memory_usage}%"
        fi
    fi
    
    # Disk usage
    if command -v df &> /dev/null; then
        local disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
        if [[ $disk_usage -gt $DISK_THRESHOLD ]]; then
            error "High disk usage: ${disk_usage}%"
            send_alert "critical" "system" "High disk usage: ${disk_usage}%"
        else
            success "Disk usage is normal: ${disk_usage}%"
        fi
    fi
    
    # Load average
    if command -v uptime &> /dev/null; then
        local load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
        local cpu_count=$(nproc 2>/dev/null || echo "1")
        
        if (( $(echo "$load_avg > $cpu_count" | bc -l 2>/dev/null || echo 0) )); then
            warning "High load average: $load_avg (CPU count: $cpu_count)"
            send_alert "warning" "system" "High load average: $load_avg"
        else
            success "Load average is normal: $load_avg"
        fi
    fi
}

# Check Docker containers
check_docker_containers() {
    log "Checking Docker containers"
    
    if ! command -v docker &> /dev/null; then
        warning "Docker not available"
        return 1
    fi
    
    if ! docker info &> /dev/null; then
        error "Docker daemon not running"
        send_alert "critical" "docker" "Docker daemon not running"
        return 2
    fi
    
    local containers=$(docker ps --format "table {{.Names}}\t{{.Status}}" | tail -n +2)
    local unhealthy_count=0
    
    while IFS=$'\t' read -r container_name container_status; do
        if [[ "$container_status" != *"Up"* ]]; then
            error "Container $container_name is not running: $container_status"
            send_alert "critical" "docker" "Container $container_name not running"
            ((unhealthy_count++))
        else
            success "Container $container_name is running: $container_status"
        fi
    done <<< "$containers"
    
    if [[ $unhealthy_count -eq 0 ]]; then
        success "All Docker containers are healthy"
    fi
}

# Check database connectivity
check_database() {
    log "Checking database connectivity"
    
    # Check PostgreSQL if available
    if command -v psql &> /dev/null && [[ -n "$DATABASE_URL" ]]; then
        if psql "$DATABASE_URL" -c "SELECT 1;" &> /dev/null; then
            success "PostgreSQL database is accessible"
        else
            error "PostgreSQL database is not accessible"
            send_alert "critical" "database" "PostgreSQL not accessible"
        fi
    fi
    
    # Check Redis if available
    if command -v redis-cli &> /dev/null && [[ -n "$REDIS_URL" ]]; then
        if redis-cli -u "$REDIS_URL" ping &> /dev/null; then
            success "Redis is accessible"
        else
            error "Redis is not accessible"
            send_alert "critical" "database" "Redis not accessible"
        fi
    fi
}

# Check external dependencies
check_external_dependencies() {
    log "Checking external dependencies"
    
    # Check internet connectivity
    if ping -c 1 8.8.8.8 &> /dev/null; then
        success "Internet connectivity is working"
    else
        warning "No internet connectivity"
        send_alert "warning" "network" "No internet connectivity"
    fi
    
    # Check DNS resolution
    if nslookup google.com &> /dev/null; then
        success "DNS resolution is working"
    else
        warning "DNS resolution issues"
        send_alert "warning" "network" "DNS resolution issues"
    fi
}

# Generate health report
generate_health_report() {
    log "Generating health report"
    
    local report_file="$PROJECT_ROOT/logs/health-report-$(date +%Y%m%d_%H%M%S).json"
    
    # Collect health data from monitoring endpoint
    if command -v curl &> /dev/null; then
        local health_data=$(curl -s "http://localhost:8000/monitoring/health" 2>/dev/null || echo "{}")
        echo "$health_data" > "$report_file"
        success "Health report generated: $report_file"
    else
        warning "Could not generate health report - curl not available"
    fi
}

# Main health check function
main() {
    log "Starting comprehensive health check"
    
    local exit_code=0
    local failed_checks=0
    
    # Check system resources
    if ! check_system_resources; then
        ((failed_checks++))
    fi
    
    # Check service health
    for service in "${SERVICES[@]}"; do
        service_name=$(echo "$service" | cut -d':' -f1)
        service_url=$(echo "$service" | cut -d':' -f2-)
        
        if ! check_service_health "$service_name" "$service_url"; then
            ((failed_checks++))
            exit_code=1
        fi
    done
    
    # Check Docker containers
    if ! check_docker_containers; then
        ((failed_checks++))
        exit_code=1
    fi
    
    # Check database
    if ! check_database; then
        ((failed_checks++))
        exit_code=1
    fi
    
    # Check external dependencies
    if ! check_external_dependencies; then
        ((failed_checks++))
        exit_code=1
    fi
    
    # Generate report
    generate_health_report
    
    # Summary
    log "Health check completed"
    if [[ $failed_checks -eq 0 ]]; then
        success "All health checks passed"
    else
        error "$failed_checks health checks failed"
    fi
    
    log "Health check summary logged to $LOG_FILE"
    log "Alerts logged to $ALERT_FILE"
    
    exit $exit_code
}

# Help function
show_help() {
    echo "Comprehensive Health Check Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -q, --quiet    Suppress output (only log to file)"
    echo "  -v, --verbose  Verbose output"
    echo ""
    echo "Environment Variables:"
    echo "  DATABASE_URL    PostgreSQL connection URL"
    echo "  REDIS_URL       Redis connection URL"
    echo "  SLACK_WEBHOOK_URL  Slack webhook for notifications"
    echo ""
    echo "Thresholds:"
    echo "  CPU_THRESHOLD:     $CPU_THRESHOLD%"
    echo "  MEMORY_THRESHOLD:  $MEMORY_THRESHOLD%"
    echo "  DISK_THRESHOLD:    $DISK_THRESHOLD%"
    echo "  RESPONSE_TIME_THRESHOLD: ${RESPONSE_TIME_THRESHOLD}s"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -q|--quiet)
            exec > "$LOG_FILE" 2>&1
            shift
            ;;
        -v|--verbose)
            set -x
            shift
            ;;
        *)
            error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Run main function
main
