import database.db_manager as db
from pathlib import Path
import streamlit as st
import pandas as pd
import datetime
import pathlib
import sqlite3
import time
import glob
import os
import io

# Определение типов техники
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

FLEET_STATUSES = [
    "В работе",
    "В ремонте"
]

def auto_save_equipment():
    """Тихо и безопасно сохраняет измененные строки и удаляет записи из БД в бэкграунде."""
    if "equipment_editor" in st.session_state:
        editor_state = st.session_state["equipment_editor"]
        
        # 1. Загружаем полный актуальный срез данных из базы
        full_df = db.load_equipment()
        
        # 2. Воспроизводим срез фильтрации для точного вычисления индексов UI
        filtered_df = full_df.copy()
        filtered_df['eq_type'] = filtered_df['eq_type'].astype(str).str.strip()
        filtered_df['eq_status'] = filtered_df['eq_status'].astype(str).str.strip()
        
        if "filter_type" in st.session_state and st.session_state["filter_type"] != "Все":
            filtered_df = filtered_df[filtered_df['eq_type'] == st.session_state["filter_type"]]
            
        if "filter_status" in st.session_state and st.session_state["filter_status"] != "Все":
            filtered_df = filtered_df[filtered_df['eq_status'] == st.session_state["filter_status"]]
            
        if "filter_search" in st.session_state and st.session_state["filter_search"]:
            q = st.session_state["filter_search"].strip().lower()
            filtered_df = filtered_df[
                filtered_df['eq_board'].astype(str).str.lower().str.contains(q) | 
                filtered_df['eq_model'].astype(str).str.lower().str.contains(q)
            ]

        # --- ШАГ 1: ОБРАБОТКА УДАЛЕНИЯ СТРОК ---
        if editor_state.get("deleted_rows"):
            conn = db.get_connection()
            cursor = conn.cursor()
            try:
                for row_idx in editor_state["deleted_rows"]:
                    real_id = int(filtered_df.iloc[row_idx]["id"])
                    cursor.execute("DELETE FROM equipment WHERE id = ?", (real_id,))
                conn.commit()
                st.toast("Запись успешно удалена! 🗑️", icon="✅")
            except Exception as e:
                st.error(f"Ошибка при удалении записи: {e}")
            finally:
                conn.close()
            # REMOVED: st.rerun() has been removed from here. 
            # Streamlit will now refresh the UI cleanly without warnings.

        # --- ШАГ 2: ОБРАБОТКА ИЗМЕНЕНИЯ ЯЧЕЕК ---
        elif editor_state.get("edited_rows"):
            changed_rows = []
            for row_idx, updated_columns in editor_state["edited_rows"].items():
                real_id = filtered_df.iloc[row_idx]["id"]
                row_to_edit = full_df[full_df["id"] == real_id].copy()
                
                for col_name, new_value in updated_columns.items():
                    row_to_edit[col_name] = new_value
                changed_rows.append(row_to_edit)

            if changed_rows:
                try:
                    df_to_update = pd.concat(changed_rows, ignore_index=True)
                    db.update_equipment(df_to_update)
                except Exception as e:
                    st.error(f"Ошибка фонового сохранения: {e}")
                    
def create_excel_template():
    """Автоматически создает пустой файл-шаблон со столбцами одинаковой ширины на Рабочем столе."""
    try:
        # Находим путь к рабочему столу на любом компьютере (Windows/Mac/Linux)
        desktop_path = Path(os.path.expanduser("~")) / "Desktop"
        
        # Если папка "Desktop" называется на русском "Рабочий стол"
        if not desktop_path.exists():
            desktop_path = Path(os.path.expanduser("~")) / "Рабочий стол"
            
        file_path = desktop_path / "shablon_tech.xlsx"
        
        # Структура колонок под вашу латинскую шапку
        columns = ["code", "bort", "type", "model", "serial", "engine_model", "engine_number", "year"]
        df_template = pd.DataFrame(columns=columns)
        
        # ИСПОЛЬЗУЕМ ExcelWriter для настройки стилей openpyxl
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df_template.to_excel(writer, index=False, sheet_name='Техника')
            
            # Получаем объект листа для управления шириной
            worksheet = writer.sheets['Техника']
            
            # Проходим по всем колонкам и задаем им фиксированную одинаковую ширину
            for col in worksheet.columns:
                col_letter = col[0].column_letter # Получаем букву колонки (A, B, C...)
                worksheet.column_dimensions[col_letter].width = 22 # Задаем ширину 22 единицы

        st.toast("Шаблон с ровными столбцами создан на Рабочем столе! 📑", icon="💾")
        
    except Exception as e:
        st.error(f"Не удалось создать файл на рабочем столе: {e}")


def process_and_save_excel(file_source):
    """Читает Excel с вашей латинской шапкой, сохраняет живые данные из БД и обновляет остальное."""
    try:
        df_raw = pd.read_excel(file_source)
        
        column_mapping = {
            "bort": "eq_board",
            "type": "eq_type",
            "model": "eq_model",
            "serial": "eq_serial",
            "year": "eq_year",
            "engine_model": "eq_engine",
            "engine_number": "eq_engine_number",
            "code": "eq_code"
        }
        
        df_mapped = df_raw.rename(columns=column_mapping)

        # Text cleaning step (same as before)
        def clean_generic_text(val):
            if pd.isna(val): return ''
            s = str(val).strip()
            return s[:-2] if s.endswith('.0') else s

        if 'eq_board' in df_mapped.columns:
            df_mapped['eq_board'] = df_mapped['eq_board'].apply(clean_generic_text)
        else:
            df_mapped['eq_board'] = 'Не указан'

        for col in ['eq_model', 'eq_type', 'eq_serial', 'eq_engine', 'eq_engine_number', 'eq_code']:
            if col in df_mapped.columns:
                df_mapped[col] = df_mapped[col].apply(clean_generic_text)
            else:
                df_mapped[col] = '' if col != 'eq_type' else 'Другое'
        
        if 'eq_year' in df_mapped.columns:
            df_mapped['eq_year'] = pd.to_numeric(df_mapped['eq_year'], errors='coerce').fillna(2026).astype(int)
        else:
            df_mapped['eq_year'] = 2026

        # --- SMART MERGE PROTECTION BLOCK ---
        # Fetch the live fleet currently saved inside your db
        df_existing = db.load_equipment()
        
        # Initialize default columns
        df_mapped['eq_last_hours'] = datetime.date.today().strftime('%Y-%m-%d')
        df_mapped['eq_hours'] = 0
        df_mapped['eq_status'] = "В работе"

        # Map live data back onto your spreadsheet entries based on the unique combination keys
        if not df_existing.empty:
            for idx, row in df_mapped.iterrows():
                # Look for a precise match in the live database file
                match = df_existing[
                    (df_existing['eq_board'] == row['eq_board']) & 
                    (df_existing['eq_model'] == row['eq_model'])
                ]
                if not match.empty:
                    # If found, keep the live numbers so they aren't reset to 0!
                    df_mapped.at[idx, 'eq_last_hours'] = match.iloc[0]['eq_last_hours']
                    df_mapped.at[idx, 'eq_hours'] = match.iloc[0]['eq_hours']
                    df_mapped.at[idx, 'eq_status'] = match.iloc[0]['eq_status']
        # -------------------------------------
        
        imported = db.import_equipment_dataframe(df_mapped)
        st.success(f"Парк техники успешно синхронизирован! Обработано строк: {imported} 📊", icon="✅")
        st.rerun()
        
    except Exception as e:
        st.error(f"Ошибка при обработке Excel: {e}")

                
# Настройка страницы
st.set_page_config(page_title="http://localhost:8501", layout="wide", page_icon="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")

def load_external_css(file_path):
    """Функция проверки существования стилей по указанному пути"""
    try:
        with open(file_path, "r", encoding="utf-8") as file_stream:
            css_rules = file_stream.read()
            st.markdown(
                f"<style>{css_rules}</style>",
                unsafe_allow_html=True,
            )
    except FileNotFoundError:
        st.error(f"CSS File not found at: {file_path}")

# Загрузка стилей внешнего вида приложения
load_external_css(".streamlit/style.css")

# Загрузка или создание БД
db.init_db()

# Инициализация роли по умолчанию (Гость)
if "role" not in st.session_state:
    st.session_state.role = "guest"

# Задание вида значка приложения для ролей
gear_class = "icon-admin" if st.session_state.role == "admin" else "icon-guest"
db_class = "db-icon-base db-online"

current_date = datetime.date.today().strftime('%d.%m.%Y')
current_time = datetime.datetime.now().strftime("%H:%M")

# Имитация данных о погоде (в будущем можно автоматизировать через API)
weather_icon = ":material/sunny:"  # Иконка переменной облачности
weather_temp = "+16°C"

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
)
st.caption(base_meta, unsafe_allow_html=True)

# Рендерим HTML-логотип
st.markdown(f"""
    <div class="header-wrapper">
        <svg class="{gear_class}" width="34" height="34" viewBox="0 0 24 24" xmlns="http://w3.org">
            <path d="M19.43 12.98c.04-.32.07-.64.07-.98s-.03-.66-.07-.98l2.11-1.65c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.3-.61-.22l-2.49 1c-.52-.4-1.08-.73-1.69-.98l-.38-2.65C14.46 2.18 14.25 2 14 2h-4c-.25 0-.46.18-.49.42l-.38 2.65c-.61.25-1.17.59-1.69.98l-2.49-1c-.23-.09-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64l2.11 1.65c-.04.32-.07.65-.07.98s.03.66.07.98l-2.11 1.65c-.19.15-.24.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1c.52.4 1.08.73 1.69.98l.38 2.65c.03.24.24.42.49.42h4c.25 0 .46-.18.49-.42l.38-2.65c.61-.25 1.17-.59 1.69-.98l2.49 1c.23.09.49 0 .61-.22l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.65zM12 15.5c-1.93 0-3.5-1.57-3.5-3.5s1.57-3.5 3.5-3.5 3.5 1.57 3.5 3.5-1.57 3.5-3.5 3.5z"/>
        </svg>
        <h1 style="margin:0; padding:0; font-size:40px; font-weight:800; color:#140A9A; margin-left:10px; display:inline-block; vertical-align:middle;">WORKSHOP</h1>
    </div>
""", unsafe_allow_html=True)

equipment_config = {
    "id": None, # Скрываем ID от пользователя
    "eq_board": st.column_config.TextColumn("Бортовой номер", width="small"),
    "eq_type": st.column_config.SelectboxColumn("Тип", options=FLEET_TYPES, required=True, width="medium"),
    "eq_model": st.column_config.TextColumn("Модель", width="medium"),
    "eq_serial": st.column_config.TextColumn("Серийный номер (VIN)", width="medium"),        
    "eq_year": st.column_config.DateColumn("Год производства", format="YYYY", width="small"),
    "eq_engine": st.column_config.TextColumn("ДВС", width="medium"),
    "eq_engine_number": st.column_config.TextColumn("Номер двигателя", width="medium"),
    "eq_code": st.column_config.TextColumn("Код", width="small"),
    "eq_last_hours": st.column_config.DateColumn("Последняя дата показаний м/ч", format="DD.MM.YYYY", width="medium"),
    "eq_hours": st.column_config.NumberColumn("Моточасы", format="%d", width="small"),
    "eq_status": st.column_config.SelectboxColumn("Статус", options=FLEET_STATUSES, width="medium")
}

# ГЛАВНЫЕ ВКЛАДКИ
tab_titles = ["ТЕХНИКА", "РАБОТЫ", "ИНСТРУМЕНТЫ", "ДОКУМЕНТЫ", "НАСТРОЙКИ"]
tab_equipment, tab_maintenance, tab_tools, tab_docs, tab_settings = st.tabs(tab_titles)

# ВКЛАДКА ТЕХНИКА
with tab_equipment:
    
    # --- PRE-PREPARE EXCEL DOWNLOAD BUFFER ---
    # We load data early so the download button inside the admin expander has access to it
    df_equipment = db.load_equipment()
    
    # Normalize types for UI components
    df_equipment['eq_type'] = df_equipment['eq_type'].astype(str).str.strip()
    df_equipment['eq_year'] = pd.to_datetime(df_equipment['eq_year'].astype(str) + '-01-01', errors='coerce')
    df_equipment['eq_status'] = df_equipment['eq_status'].astype(str).str.strip()
    df_equipment['eq_last_hours'] = pd.to_datetime(df_equipment['eq_last_hours'], errors='coerce')

    # Prepare buffered memory data for the download tool
    import io
    df_export = df_equipment.copy()
    if 'id' in df_export.columns:
        df_export = df_export.drop(columns=['id'])
    if 'eq_year' in df_export.columns:
        df_export['eq_year'] = pd.to_datetime(df_export['eq_year']).dt.year.fillna('')
    if 'eq_last_hours' in df_export.columns:
        df_export['eq_last_hours'] = pd.to_datetime(df_export['eq_last_hours']).dt.strftime('%d.%m.%Y').fillna('')

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Актуальный парк')
        worksheet = writer.sheets['Актуальный парк']
        for col_idx in range(1, len(df_export.columns) + 1):
            from openpyxl.utils import get_column_letter
            worksheet.column_dimensions[get_column_letter(col_idx)].width = 20
    # ------------------------------------------

    # --- БЛОК АДМИНИСТРАТОРА: Форма добавления и импорта техники ---
    if st.session_state.role == "admin":
        with st.expander("Добавить машину"):
            sub_tab_manual, sub_tab_import = st.tabs(["📝 Ручной ввод", "📂 Импорт из Excel"])
            
            with sub_tab_manual:
                with st.form("add_equipment_form", clear_on_submit=False):
                    col1, col2, col3, col4, col5, col6 = st.columns(6)
                    with col1:
                        form_eq_board = st.text_input("Бортовой номер *")
                        form_eq_model = st.text_input("Модель *")              
                    with col2:
                        form_eq_type = st.selectbox("Тип", FLEET_TYPES)
                        form_eq_serial = st.text_input("Серийный номер")
                    with col3:
                        form_eq_year = st.number_input("Год производства", min_value=1980, max_value=2030, value=2026)
                        form_eq_code = st.text_input("Код")                    
                    with col4:
                        form_eq_engine = st.text_input("ДВС")     
                        form_eq_engine_number = st.text_input("Номер ДВС")
                    with col5:
                        form_eq_last_hours = st.date_input("Последняя дата показаний м/ч", value=datetime.date.today(), format="DD.MM.YYYY")
                        form_eq_hours = st.number_input("Моточасы", min_value=0, value=0)    
                    with col6:
                        form_eq_status = st.selectbox("Статус", FLEET_STATUSES)

                    submitted = st.form_submit_button("Сохранить новую единицу")
                    
                    if submitted:
                        if not form_eq_board or not form_eq_model:
                            st.error("Бортовой номер и Модель являются обязательными полями!")
                        else:
                            try:
                                str_last_hours = form_eq_last_hours.strftime('%Y-%m-%d')
                                db.add_equipment(
                                    form_eq_board, form_eq_type, form_eq_model, form_eq_serial, int(form_eq_year),
                                    form_eq_engine, form_eq_engine_number, form_eq_code, str_last_hours, int(form_eq_hours), form_eq_status
                                )
                                st.success("Машина успешно добавлена!", icon="✅")
                                st.rerun() 
                            except Exception as e:
                                st.error(f"Error saving to database: {e}")
                            
            with sub_tab_import:
                st.markdown("#####  Подготовка данных")
                st.caption("Если у вас еще нет файла, нажмите кнопку ниже. Программа создаст пустой шаблон со всеми необходимыми колонками прямо на вашем Рабочем столе.")
                
                if st.button("Создать шаблон Excel на рабочем столе", type="secondary"):
                    create_excel_template()
                
                st.divider()
                
                st.markdown("##### Загрузка, Синхронизация и Экспорт")
                
                # --- DOWNLOAD BUTTON RELOCATED HERE ---
                st.download_button(
                    label=" Скачать текущую актуальную базу в Excel (XLSX)",
                    data=buffer.getvalue(),
                    file_name=f"fleet_export_{datetime.date.today().strftime('%Y-%m-%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="secondary"
                )
                st.caption("Используйте кнопку выше, чтобы выгрузить текущие записи из программы.")
                st.write("")
                
                st.divider()
                
                
                # File uploader interface right next to it
                uploaded_file = st.file_uploader("Загрузить заполненный файл XLSX для обновления/импорта:", type=["xlsx"], key="excel_uploader")
                if uploaded_file is not None:
                    if st.button("Импортировать загруженный файл", type="primary"):
                        process_and_save_excel(uploaded_file)

    # --- FILTER INTERFACE BLOCK ---
    st.caption("Поиск техники")
    f_col1, f_col2, f_col3 = st.columns(3)

    with f_col1:
        search_query = st.text_input("Поиск по всем параметрам:", placeholder="Введите текст...", key="filter_search")
    with f_col2:
        type_options = ["Все"] + FLEET_TYPES
        selected_type = st.selectbox("Фильтр по типу:", type_options, index=0, key="filter_type")
    with f_col3:
        status_options = ["Все"] + FLEET_STATUSES
        selected_status = st.selectbox("Фильтр по статусу:", status_options, index=0, key="filter_status")

    # Global search execution
    if search_query:
        q = search_query.strip().lower()
        df_searchable = df_equipment.copy()
        df_searchable['year_str'] = df_searchable['eq_year'].dt.year.fillna('').astype(str)
        df_searchable['hours_str'] = df_searchable['eq_hours'].fillna(0).astype(int).astype(str)
        
        search_columns = [
            'eq_board', 'eq_type', 'eq_model', 'eq_serial', 
            'eq_engine', 'eq_engine_number', 'eq_code', 'eq_status',
            'year_str', 'hours_str'
        ]
        global_match = df_searchable[search_columns].apply(lambda row: q in ' '.join([str(x) for x in row]).lower(), axis=1)
        df_equipment = df_equipment[global_match]
            
    if selected_type != "Все":
        df_equipment = df_equipment[df_equipment['eq_type'] == selected_type]
    if selected_status != "Все":
        df_equipment = df_equipment[df_equipment['eq_status'] == selected_status]

    # --- MAIN TABLE RENDERING GRID ---
    st.caption("Список техники")
    
    if df_equipment.empty:
        st.info("Техника с такими параметрами не найдена. Попробуйте сбросить фильтры.")
    else:
        if st.session_state.role == "admin":
            st.data_editor(
                df_equipment, 
                column_config=equipment_config, 
                use_container_width=True,
                hide_index=True,
                on_change=auto_save_equipment,
                key="equipment_editor",
                height="content",
                num_rows="dynamic"
            )
        else:
            st.dataframe(
                df_equipment, 
                column_config=equipment_config, 
                use_container_width=True,
                height="content",
                hide_index=True
            )



# ВКЛАДКА НАСТРОЙКИ
with tab_settings:
    dash_col1, dash_col2, dash_col3 = st.columns([3.5, 4.7, 1.8])
    
    with dash_col1:
        st.write("Настройки приложения")

        
    with dash_col3:
        st.write("") 
        if st.session_state.role == "admin":
            if st.button("Завершить сеанс", type="primary", width="stretch"):
                st.session_state.role = "guest"
                st.rerun()
        else:
            password = st.text_input("admin", type="password", placeholder=" ", label_visibility="collapsed")
            if password:
                if password.strip() == st.secrets["credentials"]["admin_password"]:
                    st.session_state.role = "admin"
                    st.rerun()
                else:
                    st.error("Invalid passkey")