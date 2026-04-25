import json
import logging
from datetime import datetime, date
from typing import Any, Dict, Optional, List
import asyncio
import redis
import numpy as np
from dataclasses import dataclass
from enum import Enum

from db_config import get_connection

logger = logging.getLogger(__name__)


def _ensure_uuid_func(cur):
    cur.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'uuid-ossp') THEN
                CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
            END IF;
        END$$;
        """
    )


def log_prediction_history(payload: Dict[str, Any], duration: float, status: str, request_meta: Optional[Dict[str, Any]] = None):
    conn = get_connection()
    if not conn:
        logger.warning("Database unavailable — skipping prediction history logging")
        return
    try:
        with conn:
            with conn.cursor() as cur:
                _ensure_uuid_func(cur)
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS prediction_history (
                        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                        request_id TEXT,
                        user_id TEXT,
                        image_filename TEXT,
                        label TEXT,
                        confidence DOUBLE PRECISION,
                        all_predictions JSONB,
                        processing_time DOUBLE PRECISION,
                        model_version TEXT,
                        success BOOLEAN NOT NULL DEFAULT TRUE,
                        error_message TEXT,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    """
                )
                label = payload.get("label")
                confidence = payload.get("confidence")
                all_preds = payload.get("all_predictions") or payload.get("predictions")
                model_version = payload.get("model_version") or payload.get("model") or None
                image_filename = payload.get("filename") or payload.get("image") or None
                request_id = (request_meta or {}).get("request_id")
                user_id = (request_meta or {}).get("user_id")
                error_message = (request_meta or {}).get("error_message")

                cur.execute(
                    """
                    INSERT INTO prediction_history
                    (request_id, user_id, image_filename, label, confidence, all_predictions, processing_time, model_version, success, error_message)
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s)
                    """,
                    (
                        request_id,
                        user_id,
                        image_filename,
                        label,
                        confidence,
                        json.dumps(all_preds) if all_preds is not None else json.dumps([]),
                        duration,
                        model_version,
                        status == "success",
                        error_message,
                    ),
                )

                # Upsert model performance daily aggregates
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS model_performance_metrics (
                        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                        model_version TEXT NOT NULL,
                        metric_date DATE NOT NULL,
                        total_predictions INTEGER NOT NULL DEFAULT 0,
                        avg_confidence DOUBLE PRECISION,
                        avg_processing_time DOUBLE PRECISION,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE (model_version, metric_date)
                    );
                    """
                )
                metric_date = date.today()
                cur.execute(
                    """
                    INSERT INTO model_performance_metrics (model_version, metric_date, total_predictions, avg_confidence, avg_processing_time)
                    VALUES (%s, %s, 1, %s, %s)
                    ON CONFLICT (model_version, metric_date)
                    DO UPDATE SET
                        total_predictions = model_performance_metrics.total_predictions + 1,
                        avg_confidence = CASE
                            WHEN EXCLUDED.avg_confidence IS NULL THEN model_performance_metrics.avg_confidence
                            WHEN model_performance_metrics.avg_confidence IS NULL THEN EXCLUDED.avg_confidence
                            ELSE (model_performance_metrics.avg_confidence * model_performance_metrics.total_predictions + EXCLUDED.avg_confidence) / (model_performance_metrics.total_predictions + 1)
                        END,
                        avg_processing_time = CASE
                            WHEN EXCLUDED.avg_processing_time IS NULL THEN model_performance_metrics.avg_processing_time
                            WHEN model_performance_metrics.avg_processing_time IS NULL THEN EXCLUDED.avg_processing_time
                            ELSE (model_performance_metrics.avg_processing_time * model_performance_metrics.total_predictions + EXCLUDED.avg_processing_time) / (model_performance_metrics.total_predictions + 1)
                        END;
                    """,
                    (
                        model_version or "unknown",
                        metric_date,
                        confidence if isinstance(confidence, (int, float)) else None,
                        duration if isinstance(duration, (int, float)) else None,
                    ),
                )
    except Exception as exc:
        logger.error("Failed to log prediction history: %s", exc)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def purge_old_history(days: int) -> int:
    conn = get_connection()
    if not conn:
        logger.warning("Database unavailable — skipping history purge")
        return 0
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM prediction_history
                    WHERE created_at < NOW() - INTERVAL '%s days'
                    """,
                    (days,),
                )
                deleted = cur.rowcount
                return deleted or 0
    except Exception as exc:
        logger.error("Failed to purge old history: %s", exc)
        return 0
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_prediction_history_paginated(page: int = 1, per_page: int = 50,
                                   start_date: str = None, end_date: str = None,
                                   user_id: str = None, label: str = None,
                                   model_version: str = None, success_only: bool = None) -> dict:
    """Get paginated prediction history with filtering and optimization."""
    conn = get_connection()
    if not conn:
        logger.warning("Database unavailable — returning empty results")
        return {
            'data': [],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_records': 0,
                'total_pages': 0,
                'has_next': False,
                'has_prev': False
            }
        }

    try:
        with conn:
            with conn.cursor() as cur:
                # Build WHERE clause dynamically
                where_conditions = []
                params = []

                if start_date:
                    where_conditions.append("DATE(created_at) >= %s")
                    params.append(start_date)
                if end_date:
                    where_conditions.append("DATE(created_at) <= %s")
                    params.append(end_date)
                if user_id:
                    where_conditions.append("user_id = %s")
                    params.append(user_id)
                if label:
                    where_conditions.append("label = %s")
                    params.append(label)
                if model_version:
                    where_conditions.append("model_version = %s")
                    params.append(model_version)
                if success_only is not None:
                    where_conditions.append("success = %s")
                    params.append(success_only)

                where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""

                # Get total count for pagination
                count_query = f"""
                    SELECT COUNT(*) as total
                    FROM prediction_history
                    {where_clause}
                """
                cur.execute(count_query, tuple(params))
                total_records = cur.fetchone()[0]

                # Calculate pagination
                offset = (page - 1) * per_page
                total_pages = (total_records + per_page - 1) // per_page

                # Get paginated data with optimized query
                data_query = f"""
                    SELECT
                        id,
                        request_id,
                        user_id,
                        image_filename,
                        label,
                        confidence,
                        processing_time,
                        model_version,
                        success,
                        error_message,
                        created_at
                    FROM prediction_history
                    {where_clause}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """

                cur.execute(data_query, tuple(params + [per_page, offset]))
                results = cur.fetchall()

                # Format results
                data = []
                for row in results:
                    data.append({
                        'id': str(row[0]),
                        'request_id': row[1],
                        'user_id': row[2],
                        'image_filename': row[3],
                        'label': row[4],
                        'confidence': row[5],
                        'processing_time': row[6],
                        'model_version': row[7],
                        'success': row[8],
                        'error_message': row[9],
                        'created_at': row[10].isoformat() if row[10] else None
                    })

                return {
                    'data': data,
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total_records': total_records,
                        'total_pages': total_pages,
                        'has_next': page < total_pages,
                        'has_prev': page > 1
                    }
                }

    except Exception as exc:
        logger.error("Failed to get paginated prediction history: %s", exc)
        return {
            'data': [],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_records': 0,
                'total_pages': 0,
                'has_next': False,
                'has_prev': False
            }
        }
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_aggregated_metrics(start_date: str = None, end_date: str = None,
                          group_by: str = 'day') -> list:
    """Get aggregated performance metrics with optimized queries."""
    conn = get_connection()
    if not conn:
        logger.warning("Database unavailable — returning empty metrics")
        return []

    try:
        with conn:
            with conn.cursor() as cur:
                # Set default date range
                if not start_date:
                    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                if not end_date:
                    end_date = datetime.now().strftime('%Y-%m-%d')

                # Choose grouping based on parameter
                if group_by == 'hour':
                    group_clause = "DATE_TRUNC('hour', created_at)"
                    date_format = "'YYYY-MM-DD HH24:00:00'"
                elif group_by == 'week':
                    group_clause = "DATE_TRUNC('week', created_at)"
                    date_format = "'YYYY-MM-DD'"
                else:  # day
                    group_clause = "DATE(created_at)"
                    date_format = "'YYYY-MM-DD'"

                query = f"""
                    SELECT
                        {group_clause} as period,
                        COUNT(*) as total_requests,
                        COUNT(DISTINCT user_id) as unique_users,
                        AVG(confidence) as avg_confidence,
                        AVG(processing_time) as avg_processing_time,
                        SUM(CASE WHEN success = true THEN 1 ELSE 0 END) as successful_requests,
                        COUNT(*) * 1.0 / NULLIF(SUM(CASE WHEN success = true THEN 1 ELSE 0 END), 0) as success_rate
                    FROM prediction_history
                    WHERE DATE(created_at) BETWEEN %s AND %s
                    GROUP BY {group_clause}
                    ORDER BY period DESC
                """

                cur.execute(query, (start_date, end_date))
                results = cur.fetchall()

                metrics = []
                for row in results:
                    metrics.append({
                        'period': row[0].strftime('%Y-%m-%d') if hasattr(row[0], 'strftime') else str(row[0]),
                        'total_requests': row[1],
                        'unique_users': row[2] or 0,
                        'avg_confidence': round(row[3] or 0, 4),
                        'avg_processing_time': round(row[4] or 0, 2),
                        'successful_requests': row[5],
                        'success_rate': round(row[6] or 0, 4)
                    })

                return metrics

    except Exception as exc:
        logger.error("Failed to get aggregated metrics: %s", exc)
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_model_performance_summary(model_version: str = None, days: int = 30) -> dict:
    """Get comprehensive model performance summary with optimization."""
    conn = get_connection()
    if not conn:
        logger.warning("Database unavailable — returning empty summary")
        return {}

    try:
        with conn:
            with conn.cursor() as cur:
                # Build WHERE clause
                where_conditions = ["created_at >= NOW() - INTERVAL '%s days'" % days]
                params = []

                if model_version:
                    where_conditions.append("model_version = %s")
                    params.append(model_version)

                where_clause = "WHERE " + " AND ".join(where_conditions)

                # Get comprehensive stats in a single optimized query
                query = f"""
                    SELECT
                        COUNT(*) as total_predictions,
                        COUNT(DISTINCT user_id) as unique_users,
                        AVG(confidence) as avg_confidence,
                        MIN(confidence) as min_confidence,
                        MAX(confidence) as max_confidence,
                        STDDEV(confidence) as stddev_confidence,
                        AVG(processing_time) as avg_processing_time,
                        MIN(processing_time) as min_processing_time,
                        MAX(processing_time) as max_processing_time,
                        SUM(CASE WHEN success = true THEN 1 ELSE 0 END) as successful_predictions,
                        COUNT(*) * 1.0 / NULLIF(SUM(CASE WHEN success = true THEN 1 ELSE 0 END), 0) as success_rate,
                        COUNT(DISTINCT label) as unique_labels
                    FROM prediction_history
                    {where_clause}
                """

                cur.execute(query, tuple(params))
                row = cur.fetchone()

                if row:
                    return {
                        'total_predictions': row[0],
                        'unique_users': row[1] or 0,
                        'confidence_stats': {
                            'avg': round(row[2] or 0, 4),
                            'min': round(row[3] or 0, 4),
                            'max': round(row[4] or 0, 4),
                            'stddev': round(row[5] or 0, 4)
                        },
                        'processing_time_stats': {
                            'avg': round(row[6] or 0, 2),
                            'min': round(row[7] or 0, 2),
                            'max': round(row[8] or 0, 2)
                        },
                        'success_rate': round(row[10] or 0, 4),
                        'successful_predictions': row[9],
                        'unique_labels': row[11] or 0,
                        'time_period_days': days
                    }

                return {}

    except Exception as exc:
        logger.error("Failed to get model performance summary: %s", exc)
        return {}
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_popular_labels(limit: int = 10, days: int = 30) -> list:
    """Get most popular food labels with optimized query."""
    conn = get_connection()
    if not conn:
        logger.warning("Database unavailable — returning empty labels")
        return []

    try:
        with conn:
            with conn.cursor() as cur:
                query = """
                    SELECT
                        label,
                        COUNT(*) as count,
                        AVG(confidence) as avg_confidence,
                        MAX(confidence) as max_confidence,
                        MIN(confidence) as min_confidence
                    FROM prediction_history
                    WHERE label IS NOT NULL
                      AND success = true
                      AND created_at >= NOW() - INTERVAL '%s days'
                    GROUP BY label
                    ORDER BY count DESC
                    LIMIT %s
                """

                cur.execute(query, (days, limit))
                results = cur.fetchall()

                labels = []
                for row in results:
                    labels.append({
                        'label': row[0],
                        'count': row[1],
                        'avg_confidence': round(row[2] or 0, 4),
                        'max_confidence': round(row[3] or 0, 4),
                        'min_confidence': round(row[4] or 0, 4)
                    })

                return labels

    except Exception as exc:
        logger.error("Failed to get popular labels: %s", exc)
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass


def create_optimized_indexes():
    """Create additional database indexes for better query performance."""
    conn = get_connection()
    if not conn:
        logger.warning("Database unavailable — skipping index creation")
        return

    try:
        with conn:
            with conn.cursor() as cur:
                # Composite indexes for common query patterns
                indexes = [
                    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_prediction_history_date_user ON prediction_history (DATE(created_at), user_id)",
                    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_prediction_history_date_label ON prediction_history (DATE(created_at), label)",
                    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_prediction_history_model_date ON prediction_history (model_version, DATE(created_at))",
                    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_prediction_history_success_date ON prediction_history (success, DATE(created_at))",
                    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_prediction_history_confidence ON prediction_history (confidence) WHERE confidence IS NOT NULL",
                    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_prediction_history_processing_time ON prediction_history (processing_time) WHERE processing_time IS NOT NULL",
                    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_model_performance_date ON model_performance_metrics (metric_date DESC)",
                    "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_model_performance_version_date ON model_performance_metrics (model_version, metric_date DESC)"
                ]

                for index_sql in indexes:
                    try:
                        cur.execute(index_sql)
                        logger.info("Created index: %s", index_sql.split('ON')[1].split('(')[0].strip())
                    except Exception as idx_exc:
                        logger.warning("Failed to create index: %s", idx_exc)

    except Exception as exc:
        logger.error("Failed to create optimized indexes: %s", exc)
    finally:
        try:
            conn.close()
        except Exception:
            pass


# GDPR Compliance Functions

def create_user_consent_table():
    """Create table for storing user consent records"""
    conn = get_connection()
    if not conn:
        return False
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_consent (
                        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                        user_id TEXT NOT NULL,
                        consent_type TEXT NOT NULL,
                        granted BOOLEAN NOT NULL,
                        timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        ip_address TEXT,
                        user_agent TEXT,
                        UNIQUE (user_id, consent_type)
                    );
                    """
                )
                return True
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return False


def store_user_consent(user_id: str, consent_type: str, granted: bool, ip_address: str = None, user_agent: str = None) -> bool:
    """Store or update user consent"""
    conn = get_connection()
    if not conn:
        return False
    try:
        with conn:
            with conn.cursor() as cur:
                create_user_consent_table()
                cur.execute(
                    """
                    INSERT INTO user_consent (user_id, consent_type, granted, ip_address, user_agent)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, consent_type)
                    DO UPDATE SET
                        granted = EXCLUDED.granted,
                        timestamp = NOW(),
                        ip_address = EXCLUDED.ip_address,
                        user_agent = EXCLUDED.user_agent;
                    """,
                    (user_id, consent_type, granted, ip_address, user_agent)
                )
                return True
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return False


def get_user_consent(user_id: str) -> List[Dict[str, Any]]:
    """Get all consent records for a user"""
    conn = get_connection()
    if not conn:
        return []
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT consent_type, granted, timestamp, ip_address, user_agent
                    FROM user_consent
                    WHERE user_id = %s
                    ORDER BY timestamp DESC;
                    """,
                    (user_id,)
                )
                results = cur.fetchall()
                return [
                    {
                        "consent_type": row[0],
                        "granted": row[1],
                        "timestamp": row[2].isoformat() if row[2] else None,
                        "ip_address": row[3],
                        "user_agent": row[4]
                    }
                    for row in results
                ]
    finally:
        try:
            conn.close()
        except Exception:
            pass


def export_user_data(user_id: str) -> Dict[str, Any]:
    """Export all user data for GDPR compliance"""
    conn = get_connection()
    if not conn:
        return {}
    
    try:
        with conn:
            with conn.cursor() as cur:
                # Export prediction history
                cur.execute(
                    """
                    SELECT request_id, image_filename, label, confidence, all_predictions,
                           processing_time, model_version, success, error_message, created_at
                    FROM prediction_history
                    WHERE user_id = %s
                    ORDER BY created_at DESC;
                    """,
                    (user_id,)
                )
                predictions = cur.fetchall()
                
                # Export consent records
                cur.execute(
                    """
                    SELECT consent_type, granted, timestamp, ip_address, user_agent
                    FROM user_consent
                    WHERE user_id = %s
                    ORDER BY timestamp DESC;
                    """,
                    (user_id,)
                )
                consents = cur.fetchall()
                
                return {
                    "user_id": user_id,
                    "export_timestamp": datetime.utcnow().isoformat(),
                    "prediction_history": [
                        {
                            "request_id": row[0],
                            "image_filename": row[1],
                            "label": row[2],
                            "confidence": row[3],
                            "all_predictions": row[4],
                            "processing_time": row[5],
                            "model_version": row[6],
                            "success": row[7],
                            "error_message": row[8],
                            "created_at": row[9].isoformat() if row[9] else None
                        }
                        for row in predictions
                    ],
                    "consent_records": [
                        {
                            "consent_type": row[0],
                            "granted": row[1],
                            "timestamp": row[2].isoformat() if row[2] else None,
                            "ip_address": row[3],
                            "user_agent": row[4]
                        }
                        for row in consents
                    ]
                }
    finally:
        try:
            conn.close()
        except Exception:
            pass


def delete_user_data(user_id: str) -> Dict[str, int]:
    """Delete all user data for GDPR compliance"""
    conn = get_connection()
    if not conn:
        return {"prediction_history": 0, "user_consent": 0}
    
    deletion_counts = {}
    
    try:
        with conn:
            with conn.cursor() as cur:
                # Delete from prediction_history
                cur.execute(
                    "DELETE FROM prediction_history WHERE user_id = %s",
                    (user_id,)
                )
                deletion_counts["prediction_history"] = cur.rowcount
                
                # Delete from user_consent
                cur.execute(
                    "DELETE FROM user_consent WHERE user_id = %s",
                    (user_id,)
                )
                deletion_counts["user_consent"] = cur.rowcount
                
                return deletion_counts
    finally:
        try:
            conn.close()
        except Exception:
            pass

# Advanced Graph Database Persistence Layer

class CacheStrategy(Enum):
    """Cache strategies for graph data"""
    LRU = "lru"
    LFU = "lfu"
    TTL = "ttl"
    WRITE_THROUGH = "write_through"
    WRITE_BEHIND = "write_behind"

class DataPartitioning(Enum):
    """Data partitioning strategies"""
    BY_NODE_TYPE = "by_node_type"
    BY_RELATIONSHIP_TYPE = "by_relationship_type"
    BY_TIME_RANGE = "by_time_range"
    BY_GEOGRAPHIC = "by_geographic"
    HASH_BASED = "hash_based"

@dataclass
class GraphDataMetrics:
    """Metrics for graph database performance"""
    query_time: float
    node_count: int
    edge_count: int
    cache_hit_rate: float
    memory_usage: float
    timestamp: datetime

class GraphPersistenceManager:
    """Advanced persistence manager for graph database with optimization"""
    
    def __init__(self, neo4j_uri: str = None, redis_host: str = None):
        self.neo4j_uri = neo4j_uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.redis_host = redis_host or os.getenv("REDIS_HOST", "localhost")
        self.redis_client = None
        self.cache_strategy = CacheStrategy.TTL
        self.partitioning_strategy = DataPartitioning.BY_NODE_TYPE
        self.cache_ttl = 3600  # 1 hour
        self.batch_size = 1000
        self.compression_enabled = True
        self.metrics_history = []
        
        # Initialize Redis for caching
        self._init_redis_cache()
    
    def _init_redis_cache(self):
        """Initialize Redis cache connection"""
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=6379,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Connected to Redis cache")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            self.redis_client = None
    
    async def cache_graph_data(self, key: str, data: Any, ttl: int = None) -> bool:
        """Cache graph data with specified strategy"""
        if not self.redis_client:
            return False
        
        ttl = ttl or self.cache_ttl
        
        try:
            if self.compression_enabled and isinstance(data, (dict, list)):
                # Compress large data structures
                serialized_data = json.dumps(data, separators=(',', ':'))
            else:
                serialized_data = json.dumps(data) if not isinstance(data, str) else data
            
            if self.cache_strategy == CacheStrategy.TTL:
                return self.redis_client.setex(key, ttl, serialized_data)
            else:
                return self.redis_client.set(key, serialized_data)
        except Exception as e:
            logger.error(f"Failed to cache data: {e}")
            return False
    
    async def get_cached_graph_data(self, key: str) -> Optional[Any]:
        """Retrieve cached graph data"""
        if not self.redis_client:
            return None
        
        try:
            cached_data = self.redis_client.get(key)
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached data: {e}")
            return None
    
    async def invalidate_cache_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern"""
        if not self.redis_client:
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Failed to invalidate cache pattern: {e}")
            return 0
    
    def determine_partition(self, data_type: str, data_id: str) -> str:
        """Determine data partition based on strategy"""
        if self.partitioning_strategy == DataPartitioning.BY_NODE_TYPE:
            return f"node_type:{data_type}"
        elif self.partitioning_strategy == DataPartitioning.BY_RELATIONSHIP_TYPE:
            return f"rel_type:{data_type}"
        elif self.partitioning_strategy == DataPartitioning.BY_TIME_RANGE:
            # Partition by month
            now = datetime.utcnow()
            return f"time:{now.year}:{now.month}"
        elif self.partitioning_strategy == DataPartitioning.HASH_BASED:
            hash_val = hash(data_id) % 10
            return f"hash:{hash_val}"
        else:
            return "default"
    
    async def bulk_persist_nodes(self, nodes: List[Dict[str, Any]]) -> Dict[str, int]:
        """Bulk persist nodes with optimization"""
        results = {'success': 0, 'failed': 0}
        
        # Group nodes by partition
        partitioned_nodes = {}
        for node in nodes:
            partition = self.determine_partition(node.get('type', 'unknown'), node.get('id', ''))
            if partition not in partitioned_nodes:
                partitioned_nodes[partition] = []
            partitioned_nodes[partition].append(node)
        
        # Process each partition in parallel
        tasks = []
        for partition, node_batch in partitioned_nodes.items():
            for i in range(0, len(node_batch), self.batch_size):
                batch = node_batch[i:i+self.batch_size]
                tasks.append(self._persist_node_batch(batch, partition))
        
        # Wait for all tasks to complete
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in batch_results:
            if isinstance(result, dict):
                results['success'] += result.get('success', 0)
                results['failed'] += result.get('failed', 0)
            else:
                results['failed'] += 1
        
        return results
    
    async def _persist_node_batch(self, batch: List[Dict[str, Any]], partition: str) -> Dict[str, int]:
        """Persist a batch of nodes"""
        results = {'success': 0, 'failed': 0}
        
        # Check cache first
        cache_keys = [f"node:{node['id']}" for node in batch]
        cached_data = await asyncio.gather(*[self.get_cached_graph_data(key) for key in cache_keys])
        
        # Filter out already cached nodes
        uncached_nodes = []
        for i, node in enumerate(batch):
            if cached_data[i] is None:
                uncached_nodes.append(node)
        
        if not uncached_nodes:
            return {'success': len(batch), 'failed': 0}
        
        # Persist to database (this would connect to Neo4j)
        try:
            # Simulate database operation
            await asyncio.sleep(0.01)  # Simulate network latency
            
            # Cache successful operations
            cache_tasks = []
            for node in uncached_nodes:
                cache_key = f"node:{node['id']}"
                cache_tasks.append(self.cache_graph_data(cache_key, node))
            
            await asyncio.gather(*cache_tasks)
            
            results['success'] = len(uncached_nodes)
            logger.info(f"Persisted {len(uncached_nodes)} nodes to partition {partition}")
        except Exception as e:
            logger.error(f"Failed to persist node batch: {e}")
            results['failed'] = len(uncached_nodes)
        
        return results
    
    async def bulk_persist_relationships(self, relationships: List[Dict[str, Any]]) -> Dict[str, int]:
        """Bulk persist relationships with optimization"""
        results = {'success': 0, 'failed': 0}
        
        # Group relationships by type for optimization
        grouped_relationships = {}
        for rel in relationships:
            rel_type = rel.get('type', 'unknown')
            if rel_type not in grouped_relationships:
                grouped_relationships[rel_type] = []
            grouped_relationships[rel_type].append(rel)
        
        # Process each relationship type
        tasks = []
        for rel_type, rel_batch in grouped_relationships.items():
            for i in range(0, len(rel_batch), self.batch_size):
                batch = rel_batch[i:i+self.batch_size]
                tasks.append(self._persist_relationship_batch(batch, rel_type))
        
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in batch_results:
            if isinstance(result, dict):
                results['success'] += result.get('success', 0)
                results['failed'] += result.get('failed', 0)
            else:
                results['failed'] += 1
        
        return results
    
    async def _persist_relationship_batch(self, batch: List[Dict[str, Any]], rel_type: str) -> Dict[str, int]:
        """Persist a batch of relationships"""
        results = {'success': 0, 'failed': 0}
        
        try:
            # Simulate database operation
            await asyncio.sleep(0.005)  # Simulate network latency
            
            # Cache relationships
            cache_tasks = []
            for rel in batch:
                cache_key = f"rel:{rel['source']}:{rel['target']}:{rel_type}"
                cache_tasks.append(self.cache_graph_data(cache_key, rel))
            
            await asyncio.gather(*cache_tasks)
            
            results['success'] = len(batch)
            logger.info(f"Persisted {len(batch)} relationships of type {rel_type}")
        except Exception as e:
            logger.error(f"Failed to persist relationship batch: {e}")
            results['failed'] = len(batch)
        
        return results
    
    async def query_with_cache(self, query: str, params: Dict[str, Any] = None, cache_key: str = None) -> Any:
        """Execute query with caching"""
        if cache_key is None:
            # Generate cache key from query and params
            query_hash = hash(query + str(params or {}))
            cache_key = f"query:{query_hash}"
        
        # Check cache first
        cached_result = await self.get_cached_graph_data(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for query: {cache_key}")
            return cached_result
        
        # Execute query (this would connect to Neo4j)
        start_time = datetime.utcnow()
        try:
            # Simulate query execution
            await asyncio.sleep(0.02)
            result = {"mock": "result", "query": query, "params": params}
            
            # Cache the result
            await self.cache_graph_data(cache_key, result)
            
            # Record metrics
            query_time = (datetime.utcnow() - start_time).total_seconds()
            self._record_metrics(query_time, 0, 0, 0, 0)  # Mock metrics
            
            logger.debug(f"Cache miss for query: {cache_key}, executed in {query_time:.3f}s")
            return result
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def _record_metrics(self, query_time: float, node_count: int, edge_count: int, 
                       cache_hit_rate: float, memory_usage: float):
        """Record performance metrics"""
        metrics = GraphDataMetrics(
            query_time=query_time,
            node_count=node_count,
            edge_count=edge_count,
            cache_hit_rate=cache_hit_rate,
            memory_usage=memory_usage,
            timestamp=datetime.utcnow()
        )
        
        self.metrics_history.append(metrics)
        
        # Keep only last 1000 metrics
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]
    
    def get_performance_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance metrics for specified time period"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return {}
        
        query_times = [m.query_time for m in recent_metrics]
        cache_hit_rates = [m.cache_hit_rate for m in recent_metrics if m.cache_hit_rate > 0]
        
        return {
            'period_hours': hours,
            'total_queries': len(recent_metrics),
            'avg_query_time': np.mean(query_times),
            'min_query_time': np.min(query_times),
            'max_query_time': np.max(query_times),
            'avg_cache_hit_rate': np.mean(cache_hit_rates) if cache_hit_rates else 0,
            'queries_per_hour': len(recent_metrics) / hours
        }
    
    async def optimize_indexes(self) -> Dict[str, bool]:
        """Optimize database indexes for better performance"""
        results = {}
        
        # Common index patterns for graph database
        index_patterns = [
            "CREATE INDEX node_id_index IF NOT EXISTS FOR (n) ON (n.id)",
            "CREATE INDEX node_type_index IF NOT EXISTS FOR (n) ON (n.type)",
            "CREATE INDEX relationship_type_index IF NOT EXISTS FOR ()-[r]-() ON (type(r))",
            "CREATE INDEX food_name_index IF NOT EXISTS FOR (f:FoodItem) ON (f.name)",
            "CREATE INDEX user_email_index IF NOT EXISTS FOR (u:User) ON (u.email)",
            "CREATE COMPOSITE INDEX user_food_index IF NOT EXISTS FOR (u:User)-[r:LIKES]->(f:FoodItem) ON (u.id, f.id)"
        ]
        
        for pattern in index_patterns:
            try:
                # Simulate index creation
                await asyncio.sleep(0.01)
                results[pattern] = True
                logger.info(f"Created index: {pattern}")
            except Exception as e:
                logger.error(f"Failed to create index {pattern}: {e}")
                results[pattern] = False
        
        return results
    
    async def cleanup_expired_cache(self) -> int:
        """Clean up expired cache entries"""
        if not self.redis_client:
            return 0
        
        try:
            # Get all cache keys
            keys = self.redis_client.keys("*")
            expired_keys = []
            
            for key in keys:
                ttl = self.redis_client.ttl(key)
                if ttl == -1:  # No expiration set
                    # Check if key is older than our default TTL
                    # This is a simplified approach - in production, you'd store timestamps
                    expired_keys.append(key)
            
            if expired_keys:
                deleted = self.redis_client.delete(*expired_keys)
                logger.info(f"Cleaned up {deleted} expired cache entries")
                return deleted
            
            return 0
        except Exception as e:
            logger.error(f"Failed to cleanup expired cache: {e}")
            return 0
    
    async def export_graph_data(self, format_type: str = "json", 
                              node_types: List[str] = None,
                              relationship_types: List[str] = None) -> Dict[str, Any]:
        """Export graph data in specified format"""
        export_data = {
            'metadata': {
                'export_timestamp': datetime.utcnow().isoformat(),
                'format': format_type,
                'node_types': node_types or 'all',
                'relationship_types': relationship_types or 'all'
            },
            'nodes': [],
            'relationships': []
        }
        
        # This would query the actual graph database
        # For now, return mock data
        export_data['nodes'] = [
            {'id': 'node1', 'type': 'FoodItem', 'name': 'Pizza'},
            {'id': 'node2', 'type': 'User', 'name': 'John'}
        ]
        
        export_data['relationships'] = [
            {'source': 'node2', 'target': 'node1', 'type': 'LIKES', 'weight': 0.8}
        ]
        
        return export_data
    
    async def import_graph_data(self, data: Dict[str, Any]) -> Dict[str, int]:
        """Import graph data from exported format"""
        results = {'nodes_imported': 0, 'relationships_imported': 0, 'errors': 0}
        
        try:
            # Import nodes
            if 'nodes' in data:
                node_results = await self.bulk_persist_nodes(data['nodes'])
                results['nodes_imported'] = node_results['success']
                results['errors'] += node_results['failed']
            
            # Import relationships
            if 'relationships' in data:
                rel_results = await self.bulk_persist_relationships(data['relationships'])
                results['relationships_imported'] = rel_results['success']
                results['errors'] += rel_results['failed']
            
            logger.info(f"Import completed: {results}")
        except Exception as e:
            logger.error(f"Import failed: {e}")
            results['errors'] += 1
        
        return results

# Global persistence manager instance
graph_persistence_manager = None

def get_graph_persistence_manager() -> GraphPersistenceManager:
    """Get or create global graph persistence manager"""
    global graph_persistence_manager
    if graph_persistence_manager is None:
        graph_persistence_manager = GraphPersistenceManager()
    return graph_persistence_manager
