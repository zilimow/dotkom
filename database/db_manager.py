import duckdb

DB_FILE = "fleet_duck.db"

def init_db():
    """Инициализация базы данных и создание таблиц"""
    with duckdb.connect(DB_FILE) as conn:
        conn.execute("CREATE SEQUENCE IF NOT EXISTS eq_id_seq START 1")
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS equpment (
                id INTEGER PRIMARY KEY DEFAULT nextval('eq_id_seq'),
                board VARCHAR NOT NULL,
                type VARCHAR NOT NULL,
                model VARCHAR NOT NULL,
                serial VARCHAR NOT NULL,
                year INTEGER,
                engine VARCHAR NOT NULL,
                engine_number VARCHAR NOT NULL,
                code VARCHAR,
                last_hours VARCHAR,
                hours INTEGER,
                status VARCHAR,
                UNIQUE (board, model)
            )
        """)

def get_fleet():
    with duckdb.connect(DB_FILE) as conn:
        return conn.execute("SELECT * FROM equipment").df()

def add_new_equipment(board, type, model, serial, year, engine, eng_number, code, last_hours, hours, status):
    """Добавление новой машины"""
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    with duckdb.connect(DB_FILE) as conn:
        conn.execute("""
            INSERT INTO equipment (board, type, model, serial, year, engine, engine_number, code, last_hours, hours, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (board, model) DO UPDATE SET
                type = EXCLUDED.type,
                serial = EXCLUDED.serial,
                year = EXCLUDED.year,
                engine = EXCLUDED.engine,
                engine_number = EXCLUDED.engine_number,
                code = EXCLUDED.code,
                last_hours = EXCLUDED.last_hours,
                hours = EXCLUDED.hours,
                status = EXCLUDED.status
        """, (board, type, model, serial, year, engine, eng_numиук, code, last_hours, hours, status))
















# # db_manager.py
# import sqlite3
# import os

# DB_FILE = "fleet.db"

# def init_db():
#     """Инициализация базы данных и создание необходимых таблиц."""
#     conn = sqlite3.connect(DB_FILE)
#     cursor = conn.cursor()
    
#     # Создаем таблицу ТЕХНИКА (equipment) со всеми полями из вашего эскиза
#     cursor.execute("""
#         CREATE TABLE IF NOT EXISTS equipment (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             board TEXT UNIQUE NOT NULL,       -- Бортовой номер (уникальный)
#             type TEXT NOT NULL,               -- Тип (Самосвал, Экскаватор...)
#             model TEXT NOT NULL,              -- Модель (HD785-7)
#             serial TEXT,                      -- Серийный номер (VIN)
#             year INTEGER,                     -- Год производства
#             engine TEXT,                      -- Модель ДВС
#             engine_number TEXT,               -- Номер ДВС
#             code TEXT,                        -- Системный КОД
#             last_hours TEXT,                  -- Последняя дата показаний м/ч
#             hours INTEGER DEFAULT 0,          -- Текущие Моточасы
#             status TEXT DEFAULT 'В работе'    -- Статус (В работе, В ремонте...)
#         )
#     """)
    
#     # Создаем таблицу РАБОТЫ (maintenance_logs) для истории ремонтов и ТО
#     cursor.execute("""
#         CREATE TABLE IF NOT EXISTS maintenance_logs (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             equipment_board TEXT NOT NULL,    -- Ссылка на бортовой номер техники
#             work_type TEXT NOT NULL,          -- ТО, Аварийный ремонт...
#             description TEXT NOT NULL,        -- Что конкретно сделано
#             downtime_hours REAL DEFAULT 0.0,  -- Время простоя в часах
#             created_at TEXT NOT NULL,         -- Дата и время фиксации
#             performed_by TEXT NOT NULL,       -- Кто выполнил (скрытое поле)
#             FOREIGN KEY (equipment_board) REFERENCES equipment (board)
#         )
#     """)
    
#     conn.commit()
#     conn.close()

# def run_query(query, params=()):
#     """Универсальная функция для выполнения команд записи/изменения (INSERT, UPDATE, DELETE)."""
#     with sqlite3.connect(DB_FILE) as conn:
#         cursor = conn.cursor()
#         cursor.execute(query, params)
#         conn.commit()
#         return cursor

# def get_data(query, params=()):
#     """Универсальная функция для безопасного чтения данных (SELECT)."""
#     with sqlite3.connect(DB_FILE) as conn:
#         cursor = conn.cursor()
#         cursor.execute(query, params)
#         columns = [column[0] for column in cursor.description]
#         data = cursor.fetchall()
#         # Возвращаем список словарей, чтобы легко конвертировать в Pandas DataFrame
#         return [dict(zip(columns, row)) for row in data]
