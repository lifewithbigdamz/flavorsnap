#!/usr/bin/env python3
"""
Model Monitoring System for FlavorSnap
Handles performance monitoring, drift detection, and alerting
"""

import os
import time
import json
import logging
import threading
import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import requests
from scipy import stats
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
import prometheus_client as prom
from prometheus_client import CollectorRegistry, Gauge, Counter, Histogram

# Import existing components
from model_registry import ModelRegistry
from monitoring import MODEL_ACCURACY, MODEL_INFERENCE_COUNT, MODEL_INFERENCE_DURATION

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/model_monitoring.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class DriftType(Enum):
    """Types of drift to detect"""
    DATA_DRIFT = "data_drift"
    CONCEPT_DRIFT = "concept_drift"
    PERFORMANCE_DRIFT = "performance_drift"

@dataclass
class MonitoringConfig:
    """Configuration for model monitoring"""
    # Performance thresholds
    accuracy_threshold: float = 0.85
    latency_threshold_p95: float = 1.0  # seconds
    error_rate_threshold: float = 0.01  # 1%
    
    # Drift detection
    drift_detection_enabled: bool = True
    drift_threshold: float = 0.1
    drift_window_size: int = 1000
    drift_check_interval: int = 300  # seconds
    
    # Data quality
    data_quality_checks: bool = True
    missing_data_threshold: float = 0.05
    outlier_threshold: float = 0.1
    
    # Alerting
    alert_channels: List[str] = None
    alert_cooldown: int = 300  # seconds
    
    # Monitoring frequency
    monitoring_interval: int = 60  # seconds
    metrics_retention_days: int = 30
    
    def __post_init__(self):
        if self.alert_channels is None:
            self.alert_channels = ["email", "slack"]

@dataclass
class Alert:
    """Monitoring alert"""
    alert_id: str
    severity: AlertSeverity
    alert_type: str
    model_version: str
    message: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class ModelMetrics:
    """Model performance metrics"""
    model_version: str
    timestamp: datetime
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    latency_p50: float
    latency_p95: float
    latency_p99: float
    throughput: float
    error_rate: float
    prediction_count: int
    confidence_score_avg: float

class ModelMonitoringSystem:
    """Comprehensive model monitoring system"""
    
    def __init__(self, model_registry: ModelRegistry, config: MonitoringConfig = None):
        self.model_registry = model_registry
        self.config = config or MonitoringConfig()
        
        # Monitoring state
        self.active_alerts = {}
        self.metrics_history = {}
        self.baseline_metrics = {}
        
        # Prometheus metrics
        self.registry = CollectorRegistry()
        self._setup_prometheus_metrics()
        
        # Database
        self.db_path = "model_monitoring.db"
        self._init_database()
        
        # Start monitoring threads
        self._start_monitoring_threads()
        
        logger.info("ModelMonitoringSystem initialized")
    
    def _setup_prometheus_metrics(self):
        """Setup Prometheus metrics"""
        self.drift_score_gauge = Gauge(
            'model_drift_score',
            'Model drift score',
            ['model_version', 'drift_type'],
            registry=self.registry
        )
        
        self.data_quality_gauge = Gauge(
            'data_quality_score',
            'Data quality score',
            ['model_version', 'metric'],
            registry=self.registry
        )
        
        self.alert_counter = Counter(
            'model_alerts_total',
            'Total model alerts',
            ['model_version', 'severity', 'alert_type'],
            registry=self.registry
        )
        
        self.prediction_histogram = Histogram(
            'prediction_confidence_distribution',
            'Prediction confidence distribution',
            ['model_version'],
            registry=self.registry
        )
    
    def _init_database(self):
        """Initialize monitoring database"""
        os.makedirs("logs", exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_version TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    accuracy REAL,
                    precision REAL,
                    recall REAL,
                    f1_score REAL,
                    latency_p50 REAL,
                    latency_p95 REAL,
                    latency_p99 REAL,
                    throughput REAL,
                    error_rate REAL,
                    prediction_count INTEGER,
                    confidence_score_avg REAL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS drift_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_version TEXT NOT NULL,
                    drift_type TEXT NOT NULL,
                    drift_score REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    baseline_window TEXT,
                    current_window TEXT,
                    features TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id TEXT PRIMARY KEY,
                    severity TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolved_at TEXT,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS data_quality_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_version TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    missing_data_rate REAL,
                    outlier_rate REAL,
                    feature_drift_score REAL,
                    data_volume INTEGER,
                    unique_predictions INTEGER
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_model_metrics_version_time ON model_metrics(model_version, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_drift_metrics_version_time ON drift_metrics(model_version, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_version_resolved ON alerts(model_version, resolved)")
    
    def _start_monitoring_threads(self):
        """Start background monitoring threads"""
        # Performance monitoring thread
        performance_thread = threading.Thread(
            target=self._performance_monitoring_loop,
            daemon=True
        )
        performance_thread.start()
        
        # Drift detection thread
        if self.config.drift_detection_enabled:
            drift_thread = threading.Thread(
                target=self._drift_detection_loop,
                daemon=True
            )
            drift_thread.start()
        
        # Data quality monitoring thread
        if self.config.data_quality_checks:
            quality_thread = threading.Thread(
                target=self._data_quality_monitoring_loop,
                daemon=True
            )
            quality_thread.start()
        
        logger.info("Monitoring threads started")
    
    def _performance_monitoring_loop(self):
        """Monitor model performance metrics"""
        while True:
            try:
                self._collect_performance_metrics()
                time.sleep(self.config.monitoring_interval)
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                time.sleep(60)
    
    def _drift_detection_loop(self):
        """Monitor for model drift"""
        while True:
            try:
                self._check_drift()
                time.sleep(self.config.drift_check_interval)
            except Exception as e:
                logger.error(f"Drift detection error: {e}")
                time.sleep(60)
    
    def _data_quality_monitoring_loop(self):
        """Monitor data quality metrics"""
        while True:
            try:
                self._check_data_quality()
                time.sleep(self.config.monitoring_interval)
            except Exception as e:
                logger.error(f"Data quality monitoring error: {e}")
                time.sleep(60)
    
    def _collect_performance_metrics(self):
        """Collect performance metrics for active models"""
        try:
            current_model = self.model_registry.get_active_model()
            if not current_model:
                return
            
            # Get metrics from Prometheus or other sources
            metrics = self._get_current_metrics(current_model.version)
            
            if metrics:
                # Save to database
                self._save_metrics(metrics)
                
                # Update Prometheus metrics
                MODEL_ACCURACY.set(metrics.accuracy)
                
                # Check for performance alerts
                self._check_performance_alerts(metrics)
                
                logger.debug(f"Collected metrics for {current_model.version}")
            
        except Exception as e:
            logger.error(f"Failed to collect performance metrics: {e}")
    
    def _get_current_metrics(self, model_version: str) -> Optional[ModelMetrics]:
        """Get current performance metrics for model"""
        try:
            # This would integrate with your monitoring system
            # For now, simulate metrics
            
            # Get recent inference data
            inference_data = self._get_recent_inference_data(model_version, window=100)
            
            if not inference_data:
                return None
            
            # Calculate metrics
            predictions = [d.get('prediction') for d in inference_data]
            true_labels = [d.get('true_label') for d in inference_data if d.get('true_label') is not None]
            confidences = [d.get('confidence') for d in inference_data]
            latencies = [d.get('latency') for d in inference_data]
            
            # Calculate performance metrics
            accuracy = accuracy_score(true_labels, predictions[:len(true_labels)]) if true_labels else 0.8
            
            if true_labels:
                precision, recall, f1, _ = precision_recall_fscore_support(
                    true_labels, predictions[:len(true_labels)], average='weighted', zero_division=0
                )
            else:
                precision, recall, f1 = 0.8, 0.8, 0.8
            
            # Calculate latency percentiles
            latencies_array = np.array(latencies)
            latency_p50 = np.percentile(latencies_array, 50)
            latency_p95 = np.percentile(latencies_array, 95)
            latency_p99 = np.percentile(latencies_array, 99)
            
            # Calculate throughput
            time_window = 300  # 5 minutes
            throughput = len(inference_data) / time_window
            
            # Calculate error rate
            errors = sum(1 for d in inference_data if d.get('error', False))
            error_rate = errors / len(inference_data)
            
            # Average confidence
            confidence_avg = np.mean(confidences) if confidences else 0.8
            
            return ModelMetrics(
                model_version=model_version,
                timestamp=datetime.now(),
                accuracy=accuracy,
                precision=precision,
                recall=recall,
                f1_score=f1,
                latency_p50=latency_p50,
                latency_p95=latency_p95,
                latency_p99=latency_p99,
                throughput=throughput,
                error_rate=error_rate,
                prediction_count=len(inference_data),
                confidence_score_avg=confidence_avg
            )
            
        except Exception as e:
            logger.error(f"Failed to get current metrics: {e}")
            return None
    
    def _get_recent_inference_data(self, model_version: str, window: int = 100) -> List[Dict[str, Any]]:
        """Get recent inference data for model"""
        try:
            # This would query your inference logs or database
            # For now, simulate data
            
            current_time = time.time()
            inference_data = []
            
            for i in range(window):
                # Simulate inference data
                inference_data.append({
                    'prediction': np.random.randint(0, 101),  # Food classes
                    'true_label': np.random.randint(0, 101) if i % 10 == 0 else None,  # Ground truth available sometimes
                    'confidence': np.random.beta(8, 2),  # Confidence scores
                    'latency': np.random.exponential(0.1),  # Latency in seconds
                    'error': np.random.random() < 0.01,  # 1% error rate
                    'timestamp': current_time - (window - i) * 30  # 30 seconds apart
                })
            
            return inference_data
            
        except Exception as e:
            logger.error(f"Failed to get inference data: {e}")
            return []
    
    def _save_metrics(self, metrics: ModelMetrics):
        """Save metrics to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO model_metrics 
                    (model_version, timestamp, accuracy, precision, recall, f1_score,
                     latency_p50, latency_p95, latency_p99, throughput, error_rate,
                     prediction_count, confidence_score_avg)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metrics.model_version,
                    metrics.timestamp.isoformat(),
                    metrics.accuracy,
                    metrics.precision,
                    metrics.recall,
                    metrics.f1_score,
                    metrics.latency_p50,
                    metrics.latency_p95,
                    metrics.latency_p99,
                    metrics.throughput,
                    metrics.error_rate,
                    metrics.prediction_count,
                    metrics.confidence_score_avg
                ))
            
            # Update metrics history
            if metrics.model_version not in self.metrics_history:
                self.metrics_history[metrics.model_version] = []
            
            self.metrics_history[metrics.model_version].append(metrics)
            
            # Keep only recent history
            max_history = 1000
            if len(self.metrics_history[metrics.model_version]) > max_history:
                self.metrics_history[metrics.model_version] = self.metrics_history[metrics.model_version][-max_history:]
            
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def _check_performance_alerts(self, metrics: ModelMetrics):
        """Check for performance-related alerts"""
        try:
            alerts = []
            
            # Accuracy alert
            if metrics.accuracy < self.config.accuracy_threshold:
                alerts.append(Alert(
                    alert_id=f"accuracy_alert_{int(time.time())}",
                    severity=AlertSeverity.HIGH,
                    alert_type="accuracy_drop",
                    model_version=metrics.model_version,
                    message=f"Model accuracy {metrics.accuracy:.3f} below threshold {self.config.accuracy_threshold}",
                    timestamp=datetime.now(),
                    metadata={"current_accuracy": metrics.accuracy, "threshold": self.config.accuracy_threshold}
                ))
            
            # Latency alert
            if metrics.latency_p95 > self.config.latency_threshold_p95:
                alerts.append(Alert(
                    alert_id=f"latency_alert_{int(time.time())}",
                    severity=AlertSeverity.MEDIUM,
                    alert_type="latency_increase",
                    model_version=metrics.model_version,
                    message=f"P95 latency {metrics.latency_p95:.3f}s above threshold {self.config.latency_threshold_p95}s",
                    timestamp=datetime.now(),
                    metadata={"current_latency": metrics.latency_p95, "threshold": self.config.latency_threshold_p95}
                ))
            
            # Error rate alert
            if metrics.error_rate > self.config.error_rate_threshold:
                alerts.append(Alert(
                    alert_id=f"error_rate_alert_{int(time.time())}",
                    severity=AlertSeverity.CRITICAL,
                    alert_type="high_error_rate",
                    model_version=metrics.model_version,
                    message=f"Error rate {metrics.error_rate:.3f} above threshold {self.config.error_rate_threshold}",
                    timestamp=datetime.now(),
                    metadata={"current_error_rate": metrics.error_rate, "threshold": self.config.error_rate_threshold}
                ))
            
            # Send alerts
            for alert in alerts:
                self._send_alert(alert)
            
        except Exception as e:
            logger.error(f"Failed to check performance alerts: {e}")
    
    def _check_drift(self):
        """Check for model drift"""
        try:
            current_model = self.model_registry.get_active_model()
            if not current_model:
                return
            
            # Check different types of drift
            drift_scores = {}
            
            # Data drift
            data_drift_score = self._calculate_data_drift(current_model.version)
            if data_drift_score is not None:
                drift_scores[DriftType.DATA_DRIFT] = data_drift_score
                self.drift_score_gauge.labels(
                    model_version=current_model.version,
                    drift_type="data"
                ).set(data_drift_score)
            
            # Performance drift
            performance_drift_score = self._calculate_performance_drift(current_model.version)
            if performance_drift_score is not None:
                drift_scores[DriftType.PERFORMANCE_DRIFT] = performance_drift_score
                self.drift_score_gauge.labels(
                    model_version=current_model.version,
                    drift_type="performance"
                ).set(performance_drift_score)
            
            # Check for drift alerts
            for drift_type, score in drift_scores.items():
                if score > self.config.drift_threshold:
                    alert = Alert(
                        alert_id=f"drift_alert_{drift_type.value}_{int(time.time())}",
                        severity=AlertSeverity.MEDIUM,
                        alert_type="model_drift",
                        model_version=current_model.version,
                        message=f"{drift_type.value} detected with score {score:.3f}",
                        timestamp=datetime.now(),
                        metadata={
                            "drift_type": drift_type.value,
                            "drift_score": score,
                            "threshold": self.config.drift_threshold
                        }
                    )
                    self._send_alert(alert)
            
            # Save drift metrics
            self._save_drift_metrics(current_model.version, drift_scores)
            
        except Exception as e:
            logger.error(f"Failed to check drift: {e}")
    
    def calculate_data_drift(self, model_version: str = None) -> float:
        """Calculate data drift score"""
        if not model_version:
            current_model = self.model_registry.get_active_model()
            if not current_model:
                return 0.0
            model_version = current_model.version
        
        return self._calculate_data_drift(model_version)
    
    def _calculate_data_drift(self, model_version: str) -> Optional[float]:
        """Calculate data drift using statistical tests"""
        try:
            # Get current and baseline data
            current_data = self._get_current_data_distribution(model_version)
            baseline_data = self._get_baseline_data_distribution(model_version)
            
            if not current_data or not baseline_data:
                return None
            
            # Calculate drift using Kolmogorov-Smirnov test
            drift_scores = []
            
            for feature in current_data.columns:
                if feature in baseline_data.columns:
                    current_values = current_data[feature].dropna()
                    baseline_values = baseline_data[feature].dropna()
                    
                    if len(current_values) > 0 and len(baseline_values) > 0:
                        ks_statistic, p_value = stats.ks_2samp(current_values, baseline_values)
                        drift_scores.append(ks_statistic)
            
            # Return average drift score
            return np.mean(drift_scores) if drift_scores else 0.0
            
        except Exception as e:
            logger.error(f"Failed to calculate data drift: {e}")
            return None
    
    def _get_current_data_distribution(self, model_version: str) -> Optional[pd.DataFrame]:
        """Get current data distribution"""
        try:
            # This would get current inference data
            # For now, simulate data
            np.random.seed(42)
            
            data = {
                'feature_1': np.random.normal(0.5, 0.1, 100),
                'feature_2': np.random.exponential(1.0, 100),
                'feature_3': np.random.beta(2, 2, 100)
            }
            
            return pd.DataFrame(data)
            
        except Exception as e:
            logger.error(f"Failed to get current data distribution: {e}")
            return None
    
    def _get_baseline_data_distribution(self, model_version: str) -> Optional[pd.DataFrame]:
        """Get baseline data distribution"""
        try:
            # This would get training data or historical data
            # For now, simulate baseline data
            np.random.seed(123)
            
            data = {
                'feature_1': np.random.normal(0.4, 0.1, 100),
                'feature_2': np.random.exponential(0.9, 100),
                'feature_3': np.random.beta(2.2, 1.8, 100)
            }
            
            return pd.DataFrame(data)
            
        except Exception as e:
            logger.error(f"Failed to get baseline data distribution: {e}")
            return None
    
    def _calculate_performance_drift(self, model_version: str) -> Optional[float]:
        """Calculate performance drift"""
        try:
            # Get current performance
            current_metrics = self._get_current_metrics(model_version)
            if not current_metrics:
                return None
            
            # Get baseline performance
            baseline_metrics = self.baseline_metrics.get(model_version)
            if not baseline_metrics:
                # Set current as baseline if not available
                self.baseline_metrics[model_version] = current_metrics
                return 0.0
            
            # Calculate drift as relative change
            accuracy_drift = abs(current_metrics.accuracy - baseline_metrics.accuracy) / baseline_metrics.accuracy
            latency_drift = abs(current_metrics.latency_p95 - baseline_metrics.latency_p95) / baseline_metrics.latency_p95
            error_rate_drift = abs(current_metrics.error_rate - baseline_metrics.error_rate) / baseline_metrics.error_rate
            
            # Combine drift scores
            total_drift = (accuracy_drift + latency_drift + error_rate_drift) / 3
            
            return total_drift
            
        except Exception as e:
            logger.error(f"Failed to calculate performance drift: {e}")
            return None
    
    def _check_data_quality(self):
        """Check data quality metrics"""
        try:
            current_model = self.model_registry.get_active_model()
            if not current_model:
                return
            
            # Get recent data
            recent_data = self._get_recent_inference_data(current_model.version, window=500)
            if not recent_data:
                return
            
            # Calculate quality metrics
            missing_data_rate = self._calculate_missing_data_rate(recent_data)
            outlier_rate = self._calculate_outlier_rate(recent_data)
            data_volume = len(recent_data)
            unique_predictions = len(set(d['prediction'] for d in recent_data))
            
            # Update Prometheus metrics
            self.data_quality_gauge.labels(
                model_version=current_model.version,
                metric="missing_data_rate"
            ).set(missing_data_rate)
            
            self.data_quality_gauge.labels(
                model_version=current_model.version,
                metric="outlier_rate"
            ).set(outlier_rate)
            
            # Check for quality alerts
            if missing_data_rate > self.config.missing_data_threshold:
                alert = Alert(
                    alert_id=f"missing_data_alert_{int(time.time())}",
                    severity=AlertSeverity.MEDIUM,
                    alert_type="data_quality",
                    model_version=current_model.version,
                    message=f"High missing data rate: {missing_data_rate:.3f}",
                    timestamp=datetime.now(),
                    metadata={"missing_data_rate": missing_data_rate}
                )
                self._send_alert(alert)
            
            if outlier_rate > self.config.outlier_threshold:
                alert = Alert(
                    alert_id=f"outlier_alert_{int(time.time())}",
                    severity=AlertSeverity.LOW,
                    alert_type="data_quality",
                    model_version=current_model.version,
                    message=f"High outlier rate: {outlier_rate:.3f}",
                    timestamp=datetime.now(),
                    metadata={"outlier_rate": outlier_rate}
                )
                self._send_alert(alert)
            
            # Save quality metrics
            self._save_data_quality_metrics(
                current_model.version,
                missing_data_rate,
                outlier_rate,
                data_volume,
                unique_predictions
            )
            
        except Exception as e:
            logger.error(f"Failed to check data quality: {e}")
    
    def _calculate_missing_data_rate(self, data: List[Dict[str, Any]]) -> float:
        """Calculate missing data rate"""
        try:
            if not data:
                return 0.0
            
            total_fields = 0
            missing_fields = 0
            
            for record in data:
                for key, value in record.items():
                    total_fields += 1
                    if value is None or (isinstance(value, str) and not value.strip()):
                        missing_fields += 1
            
            return missing_fields / total_fields if total_fields > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Failed to calculate missing data rate: {e}")
            return 0.0
    
    def _calculate_outlier_rate(self, data: List[Dict[str, Any]]) -> float:
        """Calculate outlier rate based on confidence scores"""
        try:
            confidences = [d.get('confidence', 0) for d in data if d.get('confidence') is not None]
            
            if not confidences:
                return 0.0
            
            # Define outliers as confidence scores more than 2 std deviations below mean
            mean_confidence = np.mean(confidences)
            std_confidence = np.std(confidences)
            outlier_threshold = mean_confidence - 2 * std_confidence
            
            outliers = sum(1 for c in confidences if c < outlier_threshold)
            
            return outliers / len(confidences)
            
        except Exception as e:
            logger.error(f"Failed to calculate outlier rate: {e}")
            return 0.0
    
    def _send_alert(self, alert: Alert):
        """Send alert notification"""
        try:
            # Check cooldown
            alert_key = f"{alert.model_version}_{alert.alert_type}"
            if alert_key in self.active_alerts:
                last_alert_time = self.active_alerts[alert_key].timestamp
                if (datetime.now() - last_alert_time).seconds < self.config.alert_cooldown:
                    return
            
            # Save alert
            self._save_alert(alert)
            self.active_alerts[alert_key] = alert
            
            # Update Prometheus counter
            self.alert_counter.labels(
                model_version=alert.model_version,
                severity=alert.severity.value,
                alert_type=alert.alert_type
            ).inc()
            
            # Send to notification channels
            for channel in self.config.alert_channels:
                if channel == "email":
                    self._send_email_alert(alert)
                elif channel == "slack":
                    self._send_slack_alert(alert)
            
            logger.warning(f"Alert sent: {alert.alert_type} - {alert.message}")
            
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
    
    def _send_email_alert(self, alert: Alert):
        """Send email alert"""
        try:
            # This would integrate with your email service
            logger.info(f"Email alert sent: {alert.alert_type}")
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    def _send_slack_alert(self, alert: Alert):
        """Send Slack alert"""
        try:
            # This would integrate with your Slack webhook
            logger.info(f"Slack alert sent: {alert.alert_type}")
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
    
    def _save_alert(self, alert: Alert):
        """Save alert to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO alerts 
                    (alert_id, severity, alert_type, model_version, message,
                     timestamp, resolved, resolved_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    alert.alert_id,
                    alert.severity.value,
                    alert.alert_type,
                    alert.model_version,
                    alert.message,
                    alert.timestamp.isoformat(),
                    alert.resolved,
                    alert.resolved_at.isoformat() if alert.resolved_at else None,
                    json.dumps(alert.metadata) if alert.metadata else None
                ))
        except Exception as e:
            logger.error(f"Failed to save alert: {e}")
    
    def _save_drift_metrics(self, model_version: str, drift_scores: Dict[DriftType, float]):
        """Save drift metrics to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                for drift_type, score in drift_scores.items():
                    conn.execute("""
                        INSERT INTO drift_metrics 
                        (model_version, drift_type, drift_score, timestamp)
                        VALUES (?, ?, ?, ?)
                    """, (
                        model_version,
                        drift_type.value,
                        score,
                        datetime.now().isoformat()
                    ))
        except Exception as e:
            logger.error(f"Failed to save drift metrics: {e}")
    
    def _save_data_quality_metrics(self, model_version: str, missing_data_rate: float,
                                  outlier_rate: float, data_volume: int, unique_predictions: int):
        """Save data quality metrics to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO data_quality_metrics 
                    (model_version, timestamp, missing_data_rate, outlier_rate,
                     data_volume, unique_predictions)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    model_version,
                    datetime.now().isoformat(),
                    missing_data_rate,
                    outlier_rate,
                    data_volume,
                    unique_predictions
                ))
        except Exception as e:
            logger.error(f"Failed to save data quality metrics: {e}")
    
    def get_model_performance(self, model_version: str, time_window: int = 24) -> Dict[str, Any]:
        """Get model performance metrics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM model_metrics 
                    WHERE model_version = ? 
                    AND timestamp > datetime('now', '-{} hours')
                    ORDER BY timestamp DESC
                """.format(time_window), (model_version,))
                
                metrics = []
                for row in cursor.fetchall():
                    metrics.append({
                        'timestamp': row['timestamp'],
                        'accuracy': row['accuracy'],
                        'precision': row['precision'],
                        'recall': row['recall'],
                        'f1_score': row['f1_score'],
                        'latency_p50': row['latency_p50'],
                        'latency_p95': row['latency_p95'],
                        'latency_p99': row['latency_p99'],
                        'throughput': row['throughput'],
                        'error_rate': row['error_rate'],
                        'prediction_count': row['prediction_count'],
                        'confidence_score_avg': row['confidence_score_avg']
                    })
                
                # Calculate aggregates
                if metrics:
                    avg_accuracy = np.mean([m['accuracy'] for m in metrics])
                    avg_latency_p95 = np.mean([m['latency_p95'] for m in metrics])
                    avg_error_rate = np.mean([m['error_rate'] for m in metrics])
                    total_predictions = sum([m['prediction_count'] for m in metrics])
                    
                    return {
                        'model_version': model_version,
                        'time_window_hours': time_window,
                        'metrics_count': len(metrics),
                        'avg_accuracy': avg_accuracy,
                        'avg_latency_p95': avg_latency_p95,
                        'avg_error_rate': avg_error_rate,
                        'total_predictions': total_predictions,
                        'detailed_metrics': metrics
                    }
                else:
                    return {
                        'model_version': model_version,
                        'time_window_hours': time_window,
                        'metrics_count': 0,
                        'message': 'No metrics available'
                    }
                
        except Exception as e:
            logger.error(f"Failed to get model performance: {e}")
            return {}
    
    def get_alerts(self, model_version: str = None, resolved: bool = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get alerts"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                query = "SELECT * FROM alerts WHERE 1=1"
                params = []
                
                if model_version:
                    query += " AND model_version = ?"
                    params.append(model_version)
                
                if resolved is not None:
                    query += " AND resolved = ?"
                    params.append(resolved)
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor = conn.execute(query, params)
                
                alerts = []
                for row in cursor.fetchall():
                    alerts.append({
                        'alert_id': row['alert_id'],
                        'severity': row['severity'],
                        'alert_type': row['alert_type'],
                        'model_version': row['model_version'],
                        'message': row['message'],
                        'timestamp': row['timestamp'],
                        'resolved': bool(row['resolved']),
                        'resolved_at': row['resolved_at'],
                        'metadata': json.loads(row['metadata']) if row['metadata'] else {}
                    })
                
                return alerts
                
        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            return []
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE alerts 
                    SET resolved = TRUE, resolved_at = ?
                    WHERE alert_id = ?
                """, (datetime.now().isoformat(), alert_id))
            
            # Update active alerts
            for key, alert in self.active_alerts.items():
                if alert.alert_id == alert_id:
                    alert.resolved = True
                    alert.resolved_at = datetime.now()
                    break
            
            logger.info(f"Alert resolved: {alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resolve alert: {e}")
            return False
    
    def get_monitoring_dashboard(self) -> Dict[str, Any]:
        """Get monitoring dashboard data"""
        try:
            current_model = self.model_registry.get_active_model()
            if not current_model:
                return {"error": "No active model"}
            
            # Get recent performance
            performance = self.get_model_performance(current_model.version, time_window=24)
            
            # Get recent alerts
            recent_alerts = self.get_alerts(resolved=False, limit=10)
            
            # Get drift metrics
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT drift_type, AVG(drift_score) as avg_score
                    FROM drift_metrics 
                    WHERE model_version = ? 
                    AND timestamp > datetime('now', '-24 hours')
                    GROUP BY drift_type
                """, (current_model.version,))
                
                drift_metrics = {}
                for row in cursor.fetchall():
                    drift_metrics[row['drift_type']] = row['avg_score']
            
            return {
                'model_version': current_model.version,
                'performance': performance,
                'recent_alerts': recent_alerts,
                'drift_metrics': drift_metrics,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get monitoring dashboard: {e}")
            return {}

# CLI interface
def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="FlavorSnap Model Monitoring")
    parser.add_argument("--performance", type=str, help="Get model performance")
    parser.add_argument("--alerts", action="store_true", help="Get alerts")
    parser.add_argument("--resolve", type=str, help="Resolve alert")
    parser.add_argument("--dashboard", action="store_true", help="Get monitoring dashboard")
    parser.add_argument("--drift", type=str, help="Calculate data drift for model")
    
    args = parser.parse_args()
    
    # Initialize monitoring system
    model_registry = ModelRegistry()
    monitoring = ModelMonitoringSystem(model_registry)
    
    if args.performance:
        performance = monitoring.get_model_performance(args.performance)
        print(json.dumps(performance, indent=2))
    
    elif args.alerts:
        alerts = monitoring.get_alerts()
        print(json.dumps(alerts, indent=2))
    
    elif args.resolve:
        success = monitoring.resolve_alert(args.resolve)
        print(f"Alert resolution {'successful' if success else 'failed'}")
    
    elif args.dashboard:
        dashboard = monitoring.get_monitoring_dashboard()
        print(json.dumps(dashboard, indent=2))
    
    elif args.drift:
        drift_score = monitoring.calculate_data_drift(args.drift)
        print(f"Data drift score: {drift_score:.3f}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
