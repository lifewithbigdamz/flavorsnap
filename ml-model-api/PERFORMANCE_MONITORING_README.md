# Performance Monitoring Integration

## Overview

This integration adds comprehensive performance monitoring capabilities to the FlavorSnap ML API, including:

- **Prometheus Metrics**: Request counting, duration tracking, and system resource monitoring
- **Performance Dashboard**: Interactive dashboard for visualizing model performance
- **Health Monitoring**: Detailed health checks with system metrics
- **Model Inference Tracking**: Performance metrics for ML model predictions

## Features

### 📊 Metrics Collection

#### HTTP Metrics
- Request count by method, endpoint, and status code
- Request duration histograms
- Exception tracking
- Rate limiting metrics

#### Model Inference Metrics
- Inference count by label and status
- Inference duration tracking
- Inference failure counting
- Model accuracy gauge

#### System Metrics
- CPU usage percentage
- Memory usage in bytes
- GPU memory usage (if available)
- Active connections count

### 🖥️ Performance Dashboard

Two dashboard modes are available:

#### Full Interactive Dashboard
- Model registry management
- A/B testing visualization
- Performance comparison charts
- Live metrics with auto-refresh
- Requires: `panel`, `plotly`, `pandas`, `numpy`

#### Simple HTML Dashboard
- Basic monitoring information
- Endpoint documentation
- Installation instructions
- Always available

### 🔍 Health Endpoints

#### `/health` - Basic Health Check
Returns application status with monitoring information

#### `/health/detailed` - Detailed Health Metrics
Comprehensive system health including:
- CPU, memory, and disk usage
- GPU information
- Model status
- Timestamped metrics

## Installation

### Basic Monitoring (Always Available)
```bash
# Core monitoring dependencies are already included
pip install prometheus-client psutil torch
```

### Full Dashboard Features
```bash
# Install all monitoring dependencies
pip install -r requirements-monitoring.txt
```

### Development Setup
```bash
# Install with development dependencies
pip install -r requirements-dev.txt
pip install -r requirements-monitoring.txt
```

## Usage

### Starting the Application
```bash
cd ml-model-api
python app.py
```

### Accessing Monitoring Features

1. **Performance Dashboard**: http://localhost:5000/dashboard
2. **Prometheus Metrics**: http://localhost:5000/metrics
3. **Health Check**: http://localhost:5000/health
4. **Detailed Health**: http://localhost:5000/health/detailed
5. **API Info**: http://localhost:5000/api/info

### Integration Points

#### Automatic Request Tracking
All HTTP requests are automatically tracked by the `MonitoringMiddleware`:
- Request count and duration
- Exception tracking
- System metrics updates

#### Model Inference Tracking
The `@track_inference` decorator automatically tracks:
- Inference duration
- Success/failure rates
- Prediction labels
- Processing time metrics

#### Manual Metrics Updates
```python
from monitoring import update_model_accuracy

# Update model accuracy metric
update_model_accuracy(0.95)
```

## Configuration

### Environment Variables
```bash
# Flask environment
FLASK_ENV=development

# Rate limiting storage
REDIS_URL=redis://localhost:6379

# API keys (comma-separated)
API_KEYS=key1,key2,key3
```

### Monitoring Customization

#### Custom Metrics
```python
from prometheus_client import Counter, Histogram

# Add custom metrics
CUSTOM_COUNTER = Counter('custom_operations_total', 'Total custom operations')
CUSTOM_HISTOGRAM = Histogram('custom_duration_seconds', 'Custom operation duration')
```

#### Dashboard Customization
The dashboard can be extended by modifying `performance_dashboard.py`:
- Add new tabs and visualizations
- Custom metrics charts
- Real-time data streams

## Prometheus Integration

### Metrics Endpoint
The `/metrics` endpoint provides Prometheus-compatible metrics:

```bash
curl http://localhost:5000/metrics
```

### Example Metrics Output
```
# HELP flask_http_request_total Total HTTP requests
# TYPE flask_http_request_total counter
flask_http_request_total{method="GET",endpoint="/health",status="200"} 42.0

# HELP flask_http_request_duration_seconds HTTP request duration in seconds
# TYPE flask_http_request_duration_seconds histogram
flask_http_request_duration_seconds_bucket{method="POST",endpoint="/predict",le="0.1"} 15.0

# HELP model_inference_total Total model inferences
# TYPE model_inference_total counter
model_inference_total{label="pizza",status="success"} 128.0
```

### Grafana Dashboard
Import the provided Grafana dashboard configuration to visualize metrics:
- Request rate and latency
- Error rates
- System resource usage
- Model performance metrics

## Security Considerations

### Rate Limiting
Monitoring endpoints have appropriate rate limits:
- `/dashboard`: 20 requests per minute
- `/metrics`: No rate limit (for Prometheus scraping)
- `/health`: No rate limit
- `/health/detailed`: No rate limit

### Access Control
- API key authentication for production endpoints
- Development mode skips API key checks
- Dashboard available without authentication (consider adding for production)

## Troubleshooting

### Common Issues

#### Dashboard Not Loading
```bash
# Check dependencies
pip install -r requirements-monitoring.txt

# Verify Panel installation
python -c "import panel; print('Panel version:', panel.__version__)"
```

#### Metrics Not Available
```bash
# Check prometheus-client installation
python -c "import prometheus_client; print('OK')"

# Verify middleware initialization
curl http://localhost:5000/metrics
```

#### System Metrics Missing
```bash
# Check psutil installation
python -c "import psutil; print('CPU:', psutil.cpu_percent())"
```

### Debug Mode
Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance Impact

### Minimal Overhead
- Request tracking: <1ms per request
- System metrics: Updated on-demand
- Memory usage: ~10MB additional

### Optimization Tips
- Use sampling for high-traffic endpoints
- Cache expensive metrics calculations
- Monitor monitoring system itself

## Development

### Adding New Metrics
1. Define metric in `monitoring.py`
2. Update in appropriate middleware/decorator
3. Add to dashboard if needed
4. Update documentation

### Extending Dashboard
1. Modify `performance_dashboard.py`
2. Add new tab or chart
3. Test with and without dependencies
4. Update README

## Production Deployment

### Docker Configuration
```dockerfile
# Add to Dockerfile
COPY requirements-monitoring.txt .
RUN pip install -r requirements-monitoring.txt
```

### Kubernetes
```yaml
# Add monitoring annotations
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "5000"
  prometheus.io/path: "/metrics"
```

### Monitoring Stack
- **Prometheus**: Metrics collection
- **Grafana**: Visualization
- **AlertManager**: Alerting
- **Node Exporter**: System metrics

## Contributing

### Testing
```bash
# Run monitoring tests
python -m pytest test_monitoring.py

# Test dashboard
python performance_dashboard.py
```

### Code Style
```bash
# Format code
black monitoring.py performance_dashboard.py

# Check linting
flake8 monitoring.py performance_dashboard.py
```

## License

This monitoring integration follows the same license as the main FlavorSnap project.

## Support

For issues and questions:
1. Check this README
2. Review the code comments
3. Check application logs
4. Open an issue in the repository
