import json
import logging
from datetime import datetime, date
from typing import Any, Dict, Optional

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
