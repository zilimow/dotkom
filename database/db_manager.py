import sqlite3
import pandas as pd

DB_FILE = "fleet.db"

def get_connection():
    """Создает безопасное подключение к файлу базы данных."""
    return sqlite3.connect(DB_FILE)

def init_db():
    """Инициализация базы данных и создание необходимых таблиц."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            eq_board TEXT NOT NULL,
            eq_type TEXT NOT NULL,
            eq_model TEXT NOT NULL,
            eq_serial TEXT NOT NULL,
            eq_year INTEGER,
            eq_engine TEXT,
            eq_engine_number TEXT,
            eq_code TEXT,
            eq_last_hours TEXT,
            eq_hours INTEGER,
            eq_status TEXT,
            UNIQUE(eq_board, eq_model)
        )
    """)   
    conn.commit()
    conn.close()

# ФУНКЦИИ ДЛЯ РАБОТЫ С ТЕХНИКОЙ
def load_equipment():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM equipment", conn)
    conn.close()
    return df

def add_equipment(eq_board, eq_type, eq_model, eq_serial, eq_year, eq_engine, eq_engine_number, eq_code, eq_last_hours, eq_hours, eq_status):
    """Добавление новой единицы в базу техники"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO equipment (eq_board, eq_type, eq_model, eq_serial, eq_year, eq_engine, eq_engine_number, eq_code, eq_last_hours, eq_hours, eq_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (eq_board, eq_type, eq_model, eq_serial, eq_year, eq_engine, eq_engine_number, eq_code, eq_last_hours, eq_hours, eq_status))
    conn.commit()
    conn.close()

def update_equipment(df):
    """Обновляет записи в базе данных на основе переданного DataFrame."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Подготавливаем запрос для массового обновления
    query = """
        UPDATE equipment 
        SET eq_board = ?, eq_type = ?, eq_model = ?, eq_serial = ?, eq_year = ?, 
            eq_engine = ?, eq_engine_number = ?, eq_code = ?, eq_last_hours = ?, 
            eq_hours = ?, eq_status = ?
        WHERE id = ?
    """
    
    # Собираем данные из DataFrame в нужном порядке колонок
    # Порядок: сначала новые значения полей, в самом конце — id для условия WHERE
    data_to_update = df[[
        'eq_board', 'eq_type', 'eq_model', 'eq_serial', 'eq_year', 
        'eq_engine', 'eq_engine_number', 'eq_code', 'eq_last_hours', 
        'eq_hours', 'eq_status', 'id'
    ]].values.tolist()
    
    # Исполняем массовое обновление через executemany (это быстрее, чем цикл в Python)
    cursor.executemany(query, data_to_update)
    
    conn.commit()
    conn.close()
    
def get_unique_types():
    """Возвращает список всех уникальных типов техники, сохраненных в БД."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT eq_type FROM equipment WHERE eq_type IS NOT NULL AND eq_type != ''")
    # Fetch all, unpack tuples, and convert to a plain list
    types = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    # Fallback to defaults if the database is brand new and empty
    if not types:
        types = ["Excavator", "Truck", "Loader", "Bulldozer", "Other"]
    return types


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

# JOBS
# def add_record(date, tech_type, model, фцвфв, hours, driver, status):
#     conn = get_connection()
#     cursor = conn.cursor()
#     cursor.execute("""
#         INSERT INTO work_logs (date, tech_type, model, work_done, hours, driver, status)
#         VALUES (?, ?, ?, ?, ?, ?, ?)
#     """, (date, tech_type, model, work_done, hours, driver, status))
#     conn.commit()
#     conn.close()

# def load_data_as_df():
#     conn = get_connection()
#     df = pd.read_sql_query("SELECT * FROM work_logs", conn)
#     conn.close()
#     return df

# def update_db_from_df(df):
#     conn = get_connection()
#     df.to_sql("work_logs", conn, if_exists="replace", index=False)
#     conn.commit()
#     conn.close()




# MECHANICS
# def add_mechanic(name, position, crew, expertise, phone, hire_date, experience):
#     conn = get_connection()
#     cursor = conn.cursor()
#     cursor.execute("""
#         INSERT INTO mechanics (name, position, crew, expertise, phone, hire_date, experience)
#         VALUES (?, ?, ?, ?, ?, ?, ?)
#     """, (name, position, crew, expertise, phone, hire_date, experience))
#     conn.commit()
#     conn.close()

# def load_mechanics():
#     conn = get_connection()
#     df = pd.read_sql_query("SELECT * FROM mechanics", conn)
#     conn.close()
#     return df

# def update_mechanics(df):
#     conn = get_connection()
#     df.to_sql("mechanics", conn, if_exists="replace", index=False)
#     conn.commit()
#     conn.close()