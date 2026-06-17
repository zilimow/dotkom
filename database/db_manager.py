import sqlite3
import logging
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
import pandas as pd
import io
from datetime import datetime
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

COLUMNS_EQUIPMENT = [
    "Бортовой номер",   # A (eq_board)
    "Тип техники",      # B (eq_type)
    "Модель",           # C (eq_model)
    "Серийный номер",   # D (eq_serial)
    "Год производства", # E (eq_year)
    "ДВС",              # F (eq_engine)
    "Номер двигателя",  # G (eq_engine_number)
    "Код"               # H (eq_code)
]

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


def generate_equipment_blank_template() -> io.BytesIO:
    """Генерация чистого Excel-шаблона с готовой шириной столбцов для импорта техники."""
    output = io.BytesIO()
    
    df_blank = pd.DataFrame(columns=COLUMNS_EQUIPMENT)
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_blank.to_excel(writer, sheet_name="Шаблон_Техники", index=False)
        worksheet = writer.sheets["Шаблон_Техники"]
        
        # Выставляем фиксированную ширину ячеек (F, G, H скорректированы под новый порядок)
        column_widths = {
            "A": 20, "B": 28, "C": 22, "D": 25, 
            "E": 20, "F": 28, "G": 25, "H": 18
        }
        
        for col, width in column_widths.items():
            worksheet.column_dimensions[col].width = width

    output.seek(0)
    return output


def import_equipment_from_excel(uploaded_file) -> tuple[bool, str]:
    """Чтение Excel-файла, жесткая очистка от None/float и импорт в SQLite."""
    try:
        # Шаг 1: Чтение файла (загружаем всё как текст, чтобы избежать автоматического float)
        df = pd.read_excel(uploaded_file, sheet_name=0, dtype=str)
        
        if df.empty:
            return False, "Файл пуст. Заполните шаблон данными."
            
        # Шаг 2: Проверка структуры колонок
        missing_cols = [col for col in COLUMNS_EQUIPMENT if col not in df.columns]
        if missing_cols:
            return False, f"Неверная структура шаблона. Отсутствуют колонки: {', '.join(missing_cols)}"
        
        # Заменяем реальные NaN/None от pandas на пустые строки
        df = df.fillna("")
        
        # Удаляем только те строки, где ВООБЩЕ нет никаких данных (полностью пустые строки в Excel)
        df = df[df["Тип техники"].astype(str).str.strip() != ""]
        
        if df.empty:
            return False, "В файле нет валидных строк (пропущен Тип техники)."

        # Шаг 3: Точечная очистка каждой ячейки и генерация бортового номера, если его нет
        bn_counter = 1
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace({"None": "", "nan": "", "None.0": "", "nan.0": ""})
            df[col] = df[col].str.replace(r"\.0$", "", regex=True)

        # Отдельно обрабатываем Бортовой номер ПОСЛЕ очистки от грязи
        for index, row in df.iterrows():
            if row["Бортовой номер"] == "":
                # Если номера нет, пишем "б/н" и добавляем индекс строки, чтобы избежать дублирования в UNIQUE
                df.at[index, "Бортовой номер"] = f"б/н-{bn_counter}"
                bn_counter += 1

        # Шаг 4: Запись в базу данных
        inserted_count = 0
        with get_connection_context() as conn:
            cursor = conn.cursor()
            
            for _, row in df.iterrows():
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO equipment (
                            eq_board, eq_type, eq_model, eq_serial, eq_year, 
                            eq_engine, eq_engine_number, eq_code
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        row["Бортовой номер"],   # eq_board
                        row["Тип техники"],      # eq_type
                        row["Модель"],           # eq_model
                        row["Серийный номер"],   # eq_serial
                        row["Год производства"], # eq_year
                        row["ДВС"],              # eq_engine
                        row["Номер двигателя"],  # eq_engine_number
                        row["Код"]               # eq_code
                    ))
                    if cursor.rowcount > 0:
                        inserted_count += 1
                except sqlite3.Error as e:
                    logger.warning(f"Ошибка импорта строки {row['Бортовой номер']}: {e}")
                    continue
                    
        if inserted_count == 0:
            return True, "Новых записей не добавлено. Вся техника из файла уже присутствует в базе."
            
        return True, f"Успешно импортировано новых записей: {inserted_count} из {len(df)}."
        
    except Exception as e:
        logger.error(f"Ошибка импорта: {e}")
        return False, f"Ошибка при обработке файла: {str(e)}"


def export_equipment_to_excel() -> io.BytesIO:
    """Выгрузка записей из таблицы equipment в Excel с полосами, жирным бортовым номером,
    увеличенной высотой строк, 10 пустыми строками и преднастройкой печати.
    """
    output = io.BytesIO()

    with get_connection_context() as conn:
        query = """
            SELECT 
                eq_board AS [Бортовой номер], 
                eq_type AS [Тип техники], 
                eq_model AS [Модель], 
                eq_serial AS [Серийный номер], 
                eq_year AS [Год производства], 
                eq_engine AS [ДВС], 
                eq_engine_number AS [Номер двигателя],
                eq_code AS [Код]
            FROM equipment 
            ORDER BY eq_type ASC, eq_board ASC
        """
        df_export = pd.read_sql_query(query, conn)

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_export.to_excel(writer, sheet_name="Список_Техники", index=False)
        worksheet = writer.sheets["Список_Техники"]

        # 1. Настройка стилей текста, выравнивания и границ
        font_header = Font(name="Calibri", size=13, bold=True)
        font_data = Font(name="Calibri", size=12, bold=False)
        font_board = Font(name="Calibri", size=13, bold=True)  # Жирный бортовой

        center_alignment = Alignment(horizontal="center", vertical="center")
        gray_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")

        # Тонкая серая сетка границ ячеек
        thin_side = Side(border_style="thin", color="CCCCCC")
        thin_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

        # Устанавливаем высоту для ШАПКИ таблицы (первая строка)
        worksheet.row_dimensions[1].height = 26
        
        # Применяем стиль к шапке таблицы (первая строка)
        for col_idx in range(1, len(COLUMNS_EQUIPMENT) + 1):
            cell = worksheet.cell(row=1, column=col_idx)
            cell.font = font_header
            cell.alignment = center_alignment

        # Применяем стиль и увеличиваем высоту строк для данных из базы
        for row_idx, row in enumerate(
            worksheet.iter_rows(
                min_row=2,
                max_row=worksheet.max_row,
                min_col=1,
                max_col=worksheet.max_column,
            ),
            start=2,
        ):
            # Устанавливаем увеличенную высоту строки с данными
            worksheet.row_dimensions[row_idx].height = 22
            
            for col_idx, cell in enumerate(row, start=1):
                cell.alignment = center_alignment
                cell.border = thin_border

                # Окрашиваем каждую вторую строку данных в серый
                if row_idx % 2 == 0:
                    cell.fill = gray_fill

                # Первая колонка (Бортовой номер) — ЖИРНЫЙ шрифт
                if col_idx == 1:
                    cell.font = font_board
                else:
                    cell.font = font_data

        # 2. Добавление 10 пустых строк для заполнения от руки
        start_empty_row = worksheet.max_row + 1
        for row_idx in range(start_empty_row, start_empty_row + 10):
            # Большая высота строки, чтобы было удобно писать ручкой
            worksheet.row_dimensions[row_idx].height = 24

            for col_idx in range(1, len(COLUMNS_EQUIPMENT) + 1):
                cell = worksheet.cell(row=row_idx, column=col_idx)
                cell.border = thin_border
                cell.alignment = center_alignment

                # Продолжаем красить полосы даже на пустых строках
                if row_idx % 2 == 0:
                    cell.fill = gray_fill

        # 3. Подготовка к печати: альбомный лист и подгонка по ширине страницы
        worksheet.page_setup.orientation = worksheet.ORIENTATION_LANDSCAPE
        worksheet.page_setup.fitToWidth = 1
        worksheet.page_setup.fitToHeight = 0
        worksheet.sheet_properties.pageSetUpPr.fitToPage = True

        # Применяем ширину столбцов
        column_widths = {
            "A": 22, "B": 28, "C": 22, "D": 25, 
            "E": 25, "F": 28, "G": 25, "H": 18
        }
        for col, width in column_widths.items():
            worksheet.column_dimensions[col].width = width

    output.seek(0)
    return output
