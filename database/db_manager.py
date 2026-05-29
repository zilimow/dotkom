# database/db_manager.py
import sqlite3
import pandas as pd

DB_PATH = "machinery_records.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Существующая таблица работ
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
    
    # 2. НОВАЯ ТАБЛИЦА: Паспорта/Справочник техники
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
    conn.commit()
    conn.close()

# --- ФУНКЦИИ ДЛЯ ТАБЛИЦЫ РАБОТ ---
def add_record(date, tech_type, model, work_done, hours, driver, status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO work_logs (date, tech_type, model, work_done, hours, driver, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (date, tech_type, model, work_done, hours, driver, status))
    conn.commit()
    conn.close()

def load_data_as_df():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM work_logs", conn)
    conn.close()
    return df

def update_db_from_df(df):
    conn = get_connection()
    df.to_sql("work_logs", conn, if_exists="replace", index=False)
    conn.commit()
    conn.close()

# --- НОВЫЕ ФУНКЦИИ ДЛЯ СПРАВОЧНИКА ТЕХНИКИ ---
def add_machine(board_number, serial_number, model, prod_year, tech_type, engine_model, engine_number, linkone_code):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO machinery_registry (board_number, serial_number, model, prod_year, tech_type, engine_model, engine_number, linkone_code)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (board_number, serial_number, model, prod_year, tech_type, engine_model, engine_number, linkone_code))
    conn.commit()
    conn.close()

def load_machinery_registry():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM machinery_registry", conn)
    conn.close()
    return df

def update_machinery_registry(df):
    conn = get_connection()
    df.to_sql("machinery_registry", conn, if_exists="replace", index=False)
    conn.commit()
    conn.close()
