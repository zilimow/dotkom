# database/db_manager.py
import sqlite3
import pandas as pd

DB_PATH = "machinery_records.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. НОВАЯ ТАБЛИЦА: Паспорта/Справочник техники
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS machinery_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            board_number TEXT NOT NULL,
            serial_number TEXT,
            model TEXT NOT NULL,
            prod_year INTEGER,
            tech_type TEXT NOT NULL,
            engine_model TEXT,
            engine_number TEXT,
            linkone_code TEXT
        )
    """)
    
    # 2. Существующая таблица работ
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS work_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            tech_type TEXT NOT NULL,
            model TEXT NOT NULL,
            work_done TEXT NOT NULL,
            hours REAL DEFAULT 0.0,
            driver TEXT,
            status TEXT
        )
    """)
    


    # Добавьте в init_db():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mechanics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            position TEXT,
            crew TEXT, 
            expertise TEXT,
            phone TEXT,
            hire_date TEXT, 
            experience TEXT
        )
    """)
    conn.commit()
    conn.close()

