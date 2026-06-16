"""
Database module for heavy equipment fleet management.
"""

import sqlite3
import logging
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
import pandas as pd

DB_FILE = "fleet.db"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    pass


def get_connection():
    """Return database connection."""
    return sqlite3.connect(DB_FILE)


@contextmanager
def get_connection_context():
    """Context manager for database connections."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise DatabaseError(f"Database operation failed: {e}") from e
    finally:
        if conn:
            conn.close()


def init_db():
    """Initialize database with all required tables and indexes."""
    with get_connection_context() as conn:
        cursor = conn.cursor()
        
        # 🚨 ИСПРАВЛЕНИЕ: Изменили UNIQUE(eq_board, eq_model) на композитный ключ из 3 колонок!
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS equipment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                eq_board TEXT NOT NULL,
                eq_type TEXT NOT NULL,
                eq_model TEXT,
                eq_serial TEXT,
                eq_year TEXT,
                eq_engine TEXT,
                eq_engine_number TEXT,
                eq_code TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(eq_board, eq_model, eq_type)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_equipment_board ON equipment(eq_board)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_equipment_type ON equipment(eq_type)
        """)
        
        logger.info("Database initialized successfully")


def load_equipment():
    """Load all equipment from database."""
    with get_connection_context() as conn:
        df = pd.read_sql_query("SELECT * FROM equipment ORDER BY eq_board", conn)
        return df

def add_equipment(eq_board, eq_type, eq_model, eq_serial, eq_year, eq_engine, eq_engine_number, eq_code):
    """Add new equipment to database safely without erasing different types."""
    with get_connection_context() as conn:
        cursor = conn.cursor()
        # 🚨 ИСПРАВЛЕНИЕ: Безопасный INSERT. Если связка Борт+Модель+Тип уже есть — СУБД выдаст ошибку,
        # а не сотрет данные молча, как делал OR REPLACE. Валидация контролируется в Streamlit.
        cursor.execute("""
            INSERT INTO equipment (eq_board, eq_type, eq_model, eq_serial, eq_year, eq_engine, eq_engine_number, eq_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (eq_board, eq_type, eq_model, eq_serial, eq_year, eq_engine, eq_engine_number, eq_code))


def update_equipment(equipment_id, **kwargs):
    """Update existing equipment."""
    if not kwargs:
        return True
    
    set_clause = ', '.join([f"{key} = ?" for key in kwargs.keys()])
    query = f"UPDATE equipment SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
    
    with get_connection_context() as conn:
        cursor = conn.cursor()
        values = list(kwargs.values()) + [equipment_id]
        cursor.execute(query, values)
        return cursor.rowcount > 0


def delete_equipment(equipment_id):
    """Delete equipment permanently."""
    with get_connection_context() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM equipment WHERE id = ?", (equipment_id,))
        return cursor.rowcount > 0


def get_unique_types():
    """Return list of unique equipment types."""
    with get_connection_context() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT eq_type FROM equipment WHERE eq_type IS NOT NULL AND eq_type != ''")
        types = [row[0] for row in cursor.fetchall()]
        
        if not types:
            types = ["Гусеничный экскаватор", "Самосвал", "Фронтальный погрузчик", "Автогрейдер"]
        return types


def get_equipment_statistics():
    """Get statistics about equipment fleet."""
    with get_connection_context() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM equipment")
        total = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT eq_type, COUNT(*) FROM equipment GROUP BY eq_type ORDER BY COUNT(*) DESC
        """)
        by_type = dict(cursor.fetchall())
        
        return {'total': total, 'by_type': by_type}
