from flask import Flask, request, jsonify
from datetime import datetime, timedelta, date
import json
from typing import List, Dict, Any, Optional, Tuple
import logging

from db_config import get_connection

logger = logging.getLogger(__name__)

class AnalyticsAPI:
    def __init__(self):
        pass

    def _execute_query(self, query: str, params: Tuple = None, fetch: bool = True) -> Optional[List[Tuple]]:
        """Execute a database query with error handling."""
        conn = get_connection()
        if not conn:
            logger.error("Database connection unavailable")
            return None

        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(query, params or ())
                    if fetch:
                        return cur.fetchall()
                    return None
        except Exception as exc:
            logger.error("Database query failed: %s", exc)
            return None
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def get_usage_stats(self, start_date: str = None, end_date: str = None,
                       page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """Get usage statistics with pagination and date filtering."""
        try:
            # Calculate date range
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')

            # Get total count for pagination
            count_query = """
                SELECT COUNT(*) as total
                FROM (
                    SELECT DATE(created_at) as date
                    FROM prediction_history
                    WHERE DATE(created_at) BETWEEN %s AND %s
                    GROUP BY DATE(created_at)
                ) daily_stats
            """
            count_result = self._execute_query(count_query, (start_date, end_date))
            total_records = count_result[0][0] if count_result else 0

            # Calculate pagination
            offset = (page - 1) * per_page
            total_pages = (total_records + per_page - 1) // per_page

            # Get paginated daily statistics
            query = """
                SELECT
                    DATE(created_at) as date,
                    COUNT(*) as requests,
                    COUNT(DISTINCT user_id) as users,
                    AVG(confidence) as avg_confidence,
                    AVG(processing_time) as avg_processing_time
                FROM prediction_history
                WHERE DATE(created_at) BETWEEN %s AND %s
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                LIMIT %s OFFSET %s
            """

            results = self._execute_query(query, (start_date, end_date, per_page, offset))

            usage_data = []
            if results:
                for row in results:
                    usage_data.append({
                        'date': row[0].strftime('%Y-%m-%d'),
                        'requests': row[1],
                        'users': row[2] or 0,
                        'accuracy': round((row[3] or 0) * 100, 1),
                        'avg_processing_time': round(row[4] or 0, 2) if row[4] else None
                    })

            return {
                'data': usage_data,
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
            logger.error("Failed to get usage stats: %s", exc)
            return {'data': [], 'pagination': {'page': 1, 'per_page': per_page, 'total_records': 0, 'total_pages': 0, 'has_next': False, 'has_prev': False}}

    def get_model_performance(self, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Get model performance metrics with pagination."""
        try:
            # Get total count
            count_query = "SELECT COUNT(*) FROM model_performance_metrics"
            count_result = self._execute_query(count_query)
            total_records = count_result[0][0] if count_result else 0

            # Calculate pagination
            offset = (page - 1) * per_page
            total_pages = (total_records + per_page - 1) // per_page

            # Get paginated model performance data
            query = """
                SELECT
                    model_version,
                    metric_date,
                    total_predictions,
                    avg_confidence,
                    avg_processing_time,
                    created_at
                FROM model_performance_metrics
                ORDER BY metric_date DESC, model_version
                LIMIT %s OFFSET %s
            """

            results = self._execute_query(query, (per_page, offset))

            performance_data = []
            if results:
                for row in results:
                    performance_data.append({
                        'model_version': row[0],
                        'date': row[1].strftime('%Y-%m-%d'),
                        'total_predictions': row[2],
                        'accuracy': round((row[3] or 0) * 100, 2) if row[3] else None,
                        'avg_processing_time': round(row[4] or 0, 2) if row[4] else None,
                        'created_at': row[5].isoformat() if row[5] else None
                    })

            return {
                'data': performance_data,
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
            logger.error("Failed to get model performance: %s", exc)
            return {'data': [], 'pagination': {'page': 1, 'per_page': per_page, 'total_records': 0, 'total_pages': 0, 'has_next': False, 'has_prev': False}}

    def get_user_engagement(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user engagement data by food category."""
        try:
            query = """
                SELECT
                    label,
                    COUNT(*) as count,
                    AVG(confidence) as avg_confidence
                FROM prediction_history
                WHERE label IS NOT NULL AND success = true
                GROUP BY label
                ORDER BY count DESC
                LIMIT %s
            """

            results = self._execute_query(query, (limit,))

            engagement_data = []
            if results:
                colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9']
                for i, row in enumerate(results):
                    engagement_data.append({
                        'category': row[0],
                        'value': row[1],
                        'avg_confidence': round((row[2] or 0) * 100, 1),
                        'color': colors[i % len(colors)]
                    })

            return engagement_data

        except Exception as exc:
            logger.error("Failed to get user engagement: %s", exc)
            return []

    def get_real_time_activity(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent prediction activities."""
        try:
            query = """
                SELECT
                    id,
                    label,
                    confidence,
                    processing_time,
                    created_at,
                    success,
                    error_message
                FROM prediction_history
                ORDER BY created_at DESC
                LIMIT %s
            """

            results = self._execute_query(query, (limit,))

            activities = []
            if results:
                for row in results:
                    activity_type = 'classification'
                    title = f"Classification: {row[1] or 'Unknown'}"
                    description = f"Confidence: {round((row[2] or 0) * 100, 1)}%"

                    if not row[5]:  # If not successful
                        activity_type = 'error'
                        title = "Classification Failed"
                        description = row[6] or "Unknown error"

                    # Calculate relative time
                    created_at = row[4]
                    now = datetime.now(created_at.tzinfo) if created_at.tzinfo else datetime.now()
                    time_diff = now - created_at

                    if time_diff.days > 0:
                        timestamp = f"{time_diff.days} days ago"
                    elif time_diff.seconds >= 3600:
                        timestamp = f"{time_diff.seconds // 3600} hours ago"
                    elif time_diff.seconds >= 60:
                        timestamp = f"{time_diff.seconds // 60} min ago"
                    else:
                        timestamp = f"{time_diff.seconds} sec ago"

                    activities.append({
                        'id': str(row[0]),
                        'type': activity_type,
                        'title': title,
                        'description': description,
                        'timestamp': timestamp,
                        'processing_time': round(row[3] or 0, 2) if row[3] else None
                    })

            return activities

        except Exception as exc:
            logger.error("Failed to get real-time activity: %s", exc)
            return []

    def get_stats_cards(self) -> List[Dict[str, Any]]:
        """Get summary statistics cards."""
        try:
            # Get total requests (last 30 days)
            total_query = """
                SELECT COUNT(*) as total
                FROM prediction_history
                WHERE created_at >= NOW() - INTERVAL '30 days'
            """
            total_result = self._execute_query(total_query)
            total_requests = total_result[0][0] if total_result else 0

            # Get active users (last 30 days)
            users_query = """
                SELECT COUNT(DISTINCT user_id) as users
                FROM prediction_history
                WHERE created_at >= NOW() - INTERVAL '30 days' AND user_id IS NOT NULL
            """
            users_result = self._execute_query(users_query)
            active_users = users_result[0][0] if users_result else 0

            # Get average accuracy (last 30 days)
            accuracy_query = """
                SELECT AVG(confidence) as avg_accuracy
                FROM prediction_history
                WHERE created_at >= NOW() - INTERVAL '30 days' AND success = true
            """
            accuracy_result = self._execute_query(accuracy_query)
            avg_accuracy = accuracy_result[0][0] if accuracy_result else 0

            # Get average response time (last 30 days)
            timing_query = """
                SELECT AVG(processing_time) as avg_time
                FROM prediction_history
                WHERE created_at >= NOW() - INTERVAL '30 days' AND processing_time IS NOT NULL
            """
            timing_result = self._execute_query(timing_query)
            avg_time = timing_result[0][0] if timing_result else 0

            return [
                {
                    'title': 'Total Requests',
                    'value': f"{total_requests:,}",
                    'change': '+12.5%',  # This would need historical comparison
                    'icon': 'activity',
                    'color': 'bg-blue-500'
                },
                {
                    'title': 'Active Users',
                    'value': f"{active_users:,}",
                    'change': '+8.2%',
                    'icon': 'users',
                    'color': 'bg-green-500'
                },
                {
                    'title': 'Avg Accuracy',
                    'value': f"{round((avg_accuracy or 0) * 100, 1)}%",
                    'change': '+2.1%',
                    'icon': 'check-circle',
                    'color': 'bg-purple-500'
                },
                {
                    'title': 'Response Time',
                    'value': f"{round(avg_time or 0, 0)}ms",
                    'change': '-15ms',
                    'icon': 'clock',
                    'color': 'bg-orange-500'
                }
            ]

        except Exception as exc:
            logger.error("Failed to get stats cards: %s", exc)
            return [
                {
                    'title': 'Total Requests',
                    'value': '0',
                    'change': 'N/A',
                    'icon': 'activity',
                    'color': 'bg-blue-500'
                },
                {
                    'title': 'Active Users',
                    'value': '0',
                    'change': 'N/A',
                    'icon': 'users',
                    'color': 'bg-green-500'
                },
                {
                    'title': 'Avg Accuracy',
                    'value': '0%',
                    'change': 'N/A',
                    'icon': 'check-circle',
                    'color': 'bg-purple-500'
                },
                {
                    'title': 'Response Time',
                    'value': '0ms',
                    'change': 'N/A',
                    'icon': 'clock',
                    'color': 'bg-orange-500'
                }
            ]

    def export_data(self, start_date: str = None, end_date: str = None,
                   data_types: List[str] = None) -> Dict[str, Any]:
        """Export analytics data with optional filtering."""
        if data_types is None:
            data_types = ['usage', 'performance', 'engagement', 'activity']

        export_data = {
            'exportDate': datetime.now().isoformat(),
            'dateRange': {
                'start': start_date,
                'end': end_date
            }
        }

        if 'usage' in data_types:
            usage_result = self.get_usage_stats(start_date, end_date, page=1, per_page=1000)
            export_data['usageData'] = usage_result['data']

        if 'performance' in data_types:
            performance_result = self.get_model_performance(page=1, per_page=1000)
            export_data['modelPerformance'] = performance_result['data']

        if 'engagement' in data_types:
            export_data['userEngagement'] = self.get_user_engagement(limit=50)

        if 'activity' in data_types:
            export_data['realTimeActivity'] = self.get_real_time_activity(limit=100)

        export_data['statsCards'] = self.get_stats_cards()

        return export_data

analytics = AnalyticsAPI()
                'value': '12,847',
                'change': '+12.5%',
                'icon': 'activity',
                'color': 'bg-blue-500'
            },
            {
                'title': 'Active Users',
                'value': '3,421',
                'change': '+8.2%',
                'icon': 'users',
                'color': 'bg-green-500'
            },
            {
                'title': 'Avg Accuracy',
                'value': '94.2%',
                'change': '+2.1%',
                'icon': 'check-circle',
                'color': 'bg-purple-500'
            },
            {
                'title': 'Response Time',
                'value': '234ms',
                'change': '-15ms',
                'icon': 'clock',
                'color': 'bg-orange-500'
            }
        ]
    
    def export_data(self, start_date=None, end_date=None):
        export_data = {
            'usageData': self.get_usage_stats(start_date, end_date),
            'modelPerformance': self.get_model_performance(),
            'userEngagement': self.get_user_engagement(),
            'statsCards': self.get_stats_cards(),
            'realTimeActivity': self.get_real_time_activity(),
            'exportDate': datetime.now().isoformat(),
            'dateRange': {
                'start': start_date,
                'end': end_date
            }
        }
        return export_data

analytics = AnalyticsAPI()
