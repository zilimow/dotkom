import streamlit as st
import pandas as pd
import datetime
from pathlib import Path
import os
import io
from openpyxl.utils import get_column_letter
import logging

# Import the database module
import database.db_manager as db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== CONSTANTS ====================

FLEET_TYPES = [
    "Гусеничный экскаватор", 
    "Колесный экскаватор",
    "Самосвал", 
    "Фронтальный погрузчик", 
    "Гусеничный бульдозер", 
    "Колесный бульдозер",
    "Автогрейдер",
    "Шинный погрузчик",
    "Телескоп",
    "Вилочный погрузчик"
]

# Column mapping for Excel import
EXCEL_COLUMN_MAPPING = {
    "board": "eq_board",
    "type": "eq_type",
    "model": "eq_model",
    "serial": "eq_serial",
    "year": "eq_year",
    "engine_model": "eq_engine",
    "engine_number": "eq_engine_number",
    "code": "eq_code"
}

# Display columns (without ID)
DISPLAY_COLUMNS = ["eq_board", "eq_type", "eq_model", "eq_serial", "eq_year", "eq_engine", "eq_engine_number", "eq_code"]

# Column configuration for dataframe display
EQUIPMENT_CONFIG = {
    "id": None,  # Hide ID from users
    "eq_board": st.column_config.TextColumn("Бортовой номер", width=100),
    "eq_type": st.column_config.SelectboxColumn("Тип", options=FLEET_TYPES, required=True, width=150),
    "eq_model": st.column_config.TextColumn("Модель", width=150),
    "eq_serial": st.column_config.TextColumn("Серийный номер (VIN)", width=180),        
    "eq_year": st.column_config.TextColumn("Год производства", width=110),
    "eq_engine": st.column_config.TextColumn("ДВС", width=150),
    "eq_engine_number": st.column_config.TextColumn("Номер двигателя", width=150),
    "eq_code": st.column_config.TextColumn("Код", width=90)
}

# ==================== HELPER FUNCTIONS ====================

def load_external_css(file_path: str):
    """Load external CSS file for styling."""
    try:
        with open(file_path, "r", encoding="utf-8") as file_stream:
            css_rules = file_stream.read()
            st.markdown(f"<style>{css_rules}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"CSS file not found at: {file_path}")


# def auto_save_equipment():
#     """Auto-save edited rows from the equipment editor."""
#     if "equipment_editor" in st.session_state and st.session_state.role == "admin":
#         editor_state = st.session_state["equipment_editor"]
        
#         # Load current data from database
#         full_df = db.load_equipment()
        
#         if full_df.empty:
#             return
        
#         # Normalize data
#         full_df['eq_type'] = full_df['eq_type'].astype(str).str.strip()
        
#         # Apply current filters to get the exact view
#         filtered_df = full_df.copy()
        
#         if "filter_search" in st.session_state and st.session_state["filter_search"]:
#             q = st.session_state["filter_search"].strip().lower()
#             filtered_df = filtered_df[
#                 filtered_df['eq_board'].astype(str).str.lower().str.contains(q, na=False) | 
#                 filtered_df['eq_model'].astype(str).str.lower().str.contains(q, na=False)
#             ]
        
#         if "filter_type" in st.session_state and st.session_state["filter_type"] != "Все":
#             filtered_df = filtered_df[filtered_df['eq_type'] == st.session_state["filter_type"]]
        
#         # Handle edited rows
#         if editor_state.get("edited_rows"):
#             changed_rows = []
#             for row_idx, updated_columns in editor_state["edited_rows"].items():
#                 if row_idx < len(filtered_df):
#                     real_id = filtered_df.iloc[row_idx]["id"]
#                     row_to_edit = full_df[full_df["id"] == real_id].copy()
                    
#                     for col_name, new_value in updated_columns.items():
#                         if col_name in DISPLAY_COLUMNS:
#                             # Special handling for year: convert string to int or None
#                             if col_name == 'eq_year':
#                                 if new_value and str(new_value).strip():
#                                     try:
#                                         year_value = int(str(new_value).strip())
#                                         # Only accept reasonable years
#                                         if 1900 <= year_value <= 2030:
#                                             row_to_edit[col_name] = year_value
#                                         else:
#                                             row_to_edit[col_name] = None
#                                     except ValueError:
#                                         row_to_edit[col_name] = None
#                                 else:
#                                     row_to_edit[col_name] = None
#                             else:
#                                 row_to_edit[col_name] = new_value if new_value and pd.notna(new_value) else None
                    
#                     changed_rows.append(row_to_edit)
            
#             if changed_rows:
#                 try:
#                     conn = db.get_connection()
#                     cursor = conn.cursor()
                    
#                     for row in changed_rows:
#                         equipment_id = int(row["id"])
#                         cursor.execute("""
#                             UPDATE equipment 
#                             SET eq_board = ?, eq_type = ?, eq_model = ?, eq_serial = ?, 
#                                 eq_year = ?, eq_engine = ?, eq_engine_number = ?, eq_code = ?,
#                                 updated_at = CURRENT_TIMESTAMP
#                             WHERE id = ?
#                         """, (
#                             row["eq_board"] if pd.notna(row["eq_board"]) else None,
#                             row["eq_type"] if pd.notna(row["eq_type"]) else None,
#                             row["eq_model"] if pd.notna(row["eq_model"]) else None,
#                             row["eq_serial"] if pd.notna(row["eq_serial"]) else None,
#                             row["eq_year"] if pd.notna(row["eq_year"]) else None,
#                             row["eq_engine"] if pd.notna(row["eq_engine"]) else None,
#                             row["eq_engine_number"] if pd.notna(row["eq_engine_number"]) else None,
#                             row["eq_code"] if pd.notna(row["eq_code"]) else None,
#                             equipment_id
#                         ))
                    
#                     conn.commit()
#                     conn.close()
#                     logger.info(f"Auto-saved {len(changed_rows)} equipment records")
                    
#                 except Exception as e:
#                     logger.error(f"Auto-save error: {e}")
                    
def create_excel_template():
    """Create empty Excel template on desktop with properly formatted columns."""
    try:
        desktop_path = Path(os.path.expanduser("~")) / "Desktop"
        
        # Handle Russian Windows desktop folder name
        if not desktop_path.exists():
            desktop_path = Path(os.path.expanduser("~")) / "Рабочий стол"
            
        file_path = desktop_path / "Список техники.xlsx"
        
        # Template structure with Latin column headers
        columns = ["code", "bort", "type", "model", "serial", "engine_model", "engine_number", "year"]
        df_template = pd.DataFrame(columns=columns)
        
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df_template.to_excel(writer, index=False, sheet_name='Техника')
            worksheet = writer.sheets['Техника']
            
            # Set uniform column width
            for col in worksheet.columns:
                col_letter = col[0].column_letter
                worksheet.column_dimensions[col_letter].width = 22

        st.toast("Шаблон создан на Рабочем столе!")
        
    except Exception as e:
        st.error(f"Не удалось создать файл: {e}")
        logger.error(f"Template creation failed: {e}")


def process_and_save_excel(file_source):
    """
    Process Excel import with smart merge to preserve existing data.
    
    Args:
        file_source: Uploaded Excel file
    """
    try:
        # Read and map columns
        df_raw = pd.read_excel(file_source)
        df_mapped = df_raw.rename(columns=EXCEL_COLUMN_MAPPING)

        # Clean text fields
        def clean_text(val):
            if pd.isna(val): 
                return ''
            s = str(val).strip()
            return s[:-2] if s.endswith('.0') else s

        # Process each column
        if 'eq_board' in df_mapped.columns:
            df_mapped['eq_board'] = df_mapped['eq_board'].apply(clean_text)
        else:
            df_mapped['eq_board'] = 'Не указан'

        for col in ['eq_model', 'eq_type', 'eq_serial', 'eq_engine', 'eq_engine_number', 'eq_code']:
            if col in df_mapped.columns:
                df_mapped[col] = df_mapped[col].apply(clean_text)
            else:
                df_mapped[col] = '' if col != 'eq_type' else 'Другое'
        
        # Handle year column - keep as None if empty
        if 'eq_year' in df_mapped.columns:
            df_mapped['eq_year'] = pd.to_numeric(df_mapped['eq_year'], errors='coerce')
        else:
            df_mapped['eq_year'] = None

        # Import to database
        affected_rows = db.import_equipment_dataframe(df_mapped)
        st.success(f"Парк техники синхронизирован! Обработано строк: {affected_rows}")
        st.rerun()
        
    except Exception as e:
        st.error(f"Ошибка при обработке Excel: {e}")
        logger.error(f"Excel processing failed: {e}")


def prepare_export_dataframe(df: pd.DataFrame) -> io.BytesIO:
    """
    Prepare DataFrame for Excel export with proper formatting.
    
    Args:
        df: Equipment DataFrame
    
    Returns:
        BytesIO buffer with Excel file
    """
    df_export = df.copy()
    
    # Remove ID column
    if 'id' in df_export.columns:
        df_export = df_export.drop(columns=['id'])
    
    # Keep year as is, don't fill empty values
    if 'eq_year' in df_export.columns:
        df_export['eq_year'] = pd.to_numeric(df_export['eq_year'], errors='coerce')
    
    # Create Excel buffer
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Актуальный парк')
        worksheet = writer.sheets['Актуальный парк']
        for col_idx in range(1, len(df_export.columns) + 1):
            worksheet.column_dimensions[get_column_letter(col_idx)].width = 20
    
    buffer.seek(0)
    return buffer


def render_header():
    """Render application header with metadata."""
    # Задание вида значка приложения для ролей
    gear_class = "icon-admin" if st.session_state.role == "admin" else "icon-guest"
    db_class = "db-icon-base db-online"

    current_date = datetime.date.today().strftime('%d.%m.%Y')
    current_time = datetime.datetime.now().strftime("%H:%M")

    # Имитация данных о погоде (в будущем можно автоматизировать через API)
    weather_icon = ":material/sunny:"  # Иконка переменной облачности
    weather_temp = "+16°C"
    
    # Display database statistics
    stats = db.get_equipment_statistics()

    # Информационная строка под логотипом
    divider = "|"
    base_meta = (
        f":material/calendar_month: {current_date}"
        f"&emsp;{divider}&emsp;"
        f":material/schedule: {current_time}"
        f"&emsp;{divider}&emsp;"
        f":material/satellite_alt: Соединение установлено :green[:material/database:]"
        f"&emsp;{divider}&emsp;"
        f"{weather_icon} Погода: **{weather_temp}**"
        f"&emsp;{divider}&emsp;"
        f":yellow[:material/front_loader:] Всего техники: **{stats.get('total', 0)}**"
    )
    st.caption(base_meta, unsafe_allow_html=True)
    
    st.markdown(f"""
        <div class="header-wrapper">
            <svg class="{gear_class}" width="34" height="34" viewBox="0 0 24 24" xmlns="http://w3.org">
                <path d="M19.43 12.98c.04-.32.07-.64.07-.98s-.03-.66-.07-.98l2.11-1.65c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.3-.61-.22l-2.49 1c-.52-.4-1.08-.73-1.69-.98l-.38-2.65C14.46 2.18 14.25 2 14 2h-4c-.25 0-.46.18-.49.42l-.38 2.65c-.61.25-1.17.59-1.69.98l-2.49-1c-.23-.09-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64l2.11 1.65c-.04.32-.07.65-.07.98s.03.66.07.98l-2.11 1.65c-.19.15-.24.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1c.52.4 1.08.73 1.69.98l.38 2.65c.03.24.24.42.49.42h4c.25 0 .46-.18.49-.42l.38-2.65c.61-.25 1.17-.59 1.69-.98l2.49 1c.23.09.49 0 .61-.22l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.65zM12 15.5c-1.93 0-3.5-1.57-3.5-3.5s1.57-3.5 3.5-3.5 3.5 1.57 3.5 3.5-1.57 3.5-3.5 3.5z"/>
            </svg>
            <h1 style="margin:0; padding:0; font-size:40px; font-weight:800; color:#140A9A; margin-left:10px; display:inline-block; vertical-align:middle;">WORKSHOP</h1>
        </div>
    """, unsafe_allow_html=True)


def render_equipment_tab():
    """Render equipment management tab."""
    
    # Load and prepare data
    df_equipment = db.load_equipment()
    
    # Normalize data types for display
    if not df_equipment.empty:
        df_equipment['eq_type'] = df_equipment['eq_type'].astype(str).str.strip()
        # Keep year as is, don't fill with default
        if 'eq_year' in df_equipment.columns:
            df_equipment['eq_year'] = pd.to_numeric(df_equipment['eq_year'], errors='coerce')
    
    # Prepare export buffer
    export_buffer = prepare_export_dataframe(df_equipment)
    
    # Admin panel - for adding new equipment
    if st.session_state.role == "admin":
        render_admin_panel(export_buffer)
    
    # Check if database is empty
    if df_equipment.empty:
        st.info("База данных пуста. Добавьте технику через панель администратора.")
        return
    
    # Apply filters
    render_filters(df_equipment)
    
    # Display equipment table with auto-save
    render_equipment_table(df_equipment)


def render_admin_panel(export_buffer: io.BytesIO):
    """Render admin panel with add, import, export functionality."""
    with st.expander("Добавить технику", expanded=False):
        tab1, tab2, tab3 = st.tabs(["Ручной ввод", "Импорт из Excel", "Выгрузка в Excel"])
        
        with tab1:
            render_manual_add_form()
        
        with tab2:
            render_import_form()
        
        with tab3:
            render_export_forms(export_buffer)


def render_manual_add_form():
    """Render manual equipment addition form."""
    with st.form("add_equipment_form", clear_on_submit=False):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            eq_board = st.text_input("Бортовой номер *")
            eq_model = st.text_input("Модель *")              
        with col2:
            eq_type = st.selectbox("Тип", FLEET_TYPES)
            eq_serial = st.text_input("Серийный номер")
        with col3:
            eq_year = st.text_input("Год производства", placeholder="например: 2020")
            eq_code = st.text_input("Код")                    
        with col4:
            eq_engine = st.text_input("ДВС")     
            eq_engine_number = st.text_input("Номер двигателя")

        submitted = st.form_submit_button("Сохранить", width='stretch')
        
        if submitted:
            if not eq_board or not eq_model:
                st.error("Бортовой номер и Модель являются обязательными полями!")
            else:
                try:
                    db.add_equipment(
                        eq_board=eq_board,
                        eq_type=eq_type,
                        eq_model=eq_model,
                        eq_serial=eq_serial,
                        eq_year=eq_year,
                        eq_engine=eq_engine,
                        eq_engine_number=eq_engine_number,
                        eq_code=eq_code
                    )
                    st.success("Машина успешно добавлена!")
                    st.rerun() 
                except Exception as e:
                    st.error(f"Ошибка при сохранении: {e}")
                    logger.error(f"Failed to add equipment: {e}")


def render_import_form():
    """Render Excel import form."""
    uploaded_file = st.file_uploader(
        "Загрузить файл XLSX для обновления/импорта:", 
        type=["xlsx"], 
        key="excel_uploader"
    )
    if uploaded_file is not None:
        if st.button("Импортировать", type="primary", width='stretch'):
            process_and_save_excel(uploaded_file)


def render_export_forms(export_buffer: io.BytesIO):
    """Render Excel export forms."""
    st.write("Создать шаблон для заполнения")
    if st.button("Создать шаблон", type="secondary", width='stretch'):
        create_excel_template()
    
    st.divider()
    
    st.write("Скачать текущий список техники")
    st.download_button(
        label="Скачать Excel",
        data=export_buffer.getvalue(),
        file_name=f"fleet_export_{datetime.date.today().strftime('%Y-%m-%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="secondary",
        width='stretch'
    )


def render_filters(df_equipment: pd.DataFrame):
    """Render filter interface for equipment list."""
    st.caption("Поиск техники")
    
    col1, col2 = st.columns(2)
    
    with col1:
        search_query = st.text_input(
            "Поиск", 
            placeholder="Бортовой номер, модель...", 
            key="filter_search"
        )
    with col2:
        type_options = ["Все"] + FLEET_TYPES
        selected_type = st.selectbox("Тип техники", type_options, key="filter_type")
    
    # Apply filters
    filtered_df = df_equipment.copy()
    
    if search_query:
        q = search_query.strip().lower()
        mask = (
            filtered_df['eq_board'].astype(str).str.lower().str.contains(q, na=False) |
            filtered_df['eq_model'].astype(str).str.lower().str.contains(q, na=False) |
            filtered_df['eq_serial'].astype(str).str.lower().str.contains(q, na=False)
        )
        filtered_df = filtered_df[mask]
    
    if selected_type != "Все":
        filtered_df = filtered_df[filtered_df['eq_type'] == selected_type]
    
    st.session_state.filtered_df = filtered_df.reset_index(drop=True)


def render_equipment_table(df_equipment: pd.DataFrame):
    """Render equipment data table with auto-save for admin."""
    st.caption("Список техники")
    
    column_config={
                "eq_board": st.column_config.TextColumn("Бортовой номер", required=True),
                "eq_type": st.column_config.SelectboxColumn("Тип", options=FLEET_TYPES, required=True),
                "eq_model": st.column_config.TextColumn("Модель", required=True),
                "eq_serial": st.column_config.TextColumn("Серийный номер"),
                "eq_year": st.column_config.TextColumn("Год производства"),
                "eq_engine": st.column_config.TextColumn("ДВС"),
                "eq_engine_number": st.column_config.TextColumn("Номер двигателя"),
                "eq_code": st.column_config.TextColumn("Код"),
            }
    
    filtered_df = st.session_state.get('filtered_df', df_equipment)
    
    if filtered_df.empty:
        st.info("Техника с такими параметрами не найдена. Попробуйте изменить фильтры.")
        return
    
    # Prepare display dataframe (without ID)
    display_df = filtered_df[DISPLAY_COLUMNS].copy()
    
     

    st.dataframe(display_df, column_config=column_config, width='stretch', height="content", hide_index=True )
    


def render_settings_tab():
    """Render settings and authentication tab."""
    col1, col2 = st.columns([3.5, 1.8])
    
    with col1:
        st.write("Настройки приложения")
        

    
    with col2:
        render_authentication()


def render_authentication():
    """Render authentication controls."""
    if st.session_state.role == "admin":
        if st.button("Завершить сеанс", type="primary", width='stretch'):
            st.session_state.role = "guest"
            st.rerun()
    else:
        password = st.text_input( "Пароль", type="password", placeholder="Введите пароль", label_visibility="collapsed")
        if password:
            try:
                if password.strip() == st.secrets["credentials"]["admin_password"]:
                    st.session_state.role = "admin"
                    st.rerun()
                else:
                    st.error("Неверный пароль")
            except KeyError:
                st.error("Ошибка конфигурации. Обратитесь к администратору.")
                logger.error("Secrets configuration missing admin_password")


# ==================== MAIN APPLICATION ====================

def main():
    """Main application entry point."""
    # Page configuration
    st.set_page_config(page_title="WORKSHOP | WERKSTATT", layout="wide", page_icon="assets/hardware.svg")
    
    # Initialize session state
    if "role" not in st.session_state:
        st.session_state.role = "guest"
    
    if "filtered_df" not in st.session_state:
        st.session_state.filtered_df = pd.DataFrame()
    
    # Load styles
    load_external_css(".streamlit/style.css")
    
    # Initialize database
    try:
        db.init_db()
    except Exception as e:
        st.error(f"Ошибка подключения к базе данных: {e}")
        logger.error(f"Database initialization failed: {e}")
        st.stop()
    
    # Render header
    render_header()
    
    # Create tabs
    tab_titles = ["ТЕХНИКА", "РАБОТЫ", "ИНСТРУМЕНТЫ", "ДОКУМЕНТЫ", "НАСТРОЙКИ"]
    tabs = st.tabs(tab_titles)
    
    # Equipment tab
    with tabs[0]:
        render_equipment_tab()
    
    # Settings tab
    with tabs[4]:
        render_settings_tab()
    
    # Placeholder for other tabs
    with tabs[1]:
        st.info("Раздел в разработке")
    with tabs[2]:
        st.info("Раздел в разработке")
    with tabs[3]:
        st.info("Раздел в разработке")


if __name__ == "__main__":
    main()