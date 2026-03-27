import logging
import os
import time
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BASE_DELAY = 1  # seconds
RETRY_BACKOFF_FACTOR = 2
CONNECTION_TIMEOUT = 5  # seconds


def get_database_url() -> Optional[str]:
    url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_DSN")
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def get_connection(retries: int = MAX_RETRIES):
    url = get_database_url()
    if not url:
        logger.warning("No database URL configured (DATABASE_URL / POSTGRES_DSN)")
        return None

    import psycopg2

    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            conn = psycopg2.connect(url, connect_timeout=CONNECTION_TIMEOUT)
            return conn
        except psycopg2.OperationalError as exc:
            last_exc = exc
            if attempt < retries:
                delay = RETRY_BASE_DELAY * (RETRY_BACKOFF_FACTOR ** (attempt - 1))
                logger.warning(
                    "Database connection attempt %d/%d failed: %s — retrying in %.1fs",
                    attempt, retries, exc, delay,
                )
                time.sleep(delay)
            else:
                logger.error(
                    "Database connection failed after %d attempts: %s",
                    retries, last_exc,
                )
        except Exception as exc:
            logger.error("Unexpected error connecting to database: %s", exc)
            return None
    return None


def is_db_available() -> bool:
    conn = get_connection(retries=1)
    if conn is None:
        return False
    try:
        conn.close()
    except Exception:
        pass
    return True


def execute_sql(sql: str, params: Optional[Tuple] = None):
    conn = get_connection()
    if not conn:
        return None
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                try:
                    return cur.fetchall()
                except Exception:
                    return None
    except Exception as exc:
        logger.error("Error executing SQL: %s", exc)
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass
