from openpyxl.utils import get_column_letter
import database.db_manager as db
from pathlib import Path
import streamlit as st
import pandas as pd
import datetime
import logging
import time
import os
import io


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== CONSTANTS ====================

FLEET_TYPES = [
    "Самосвал",
    "Гусеничный экскаватор", 
    "Фронтальный погрузчик", 
    "Гусеничный бульдозер",
    "Колесный бульдозер",
    "Автогрейдер",
    "Вилочный погрузчик",    
    "Телескоп",    
    "Колесный экскаватор",
    "Шинный погрузчик"
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
        
def app_header():
    """Render application header with metadata, retaining exact CSS styles and matching line to app width."""
    # Задание вида значка приложения для ролей на основе ваших оригинальных CSS классов
    gear_class = "icon-admin" if st.session_state.role == "admin" else "icon-guest"
    
    months_ru = {
        1: "января", 2: "февраля", 3: "марта", 4: "апреля",
        5: "мая", 6: "июня", 7: "июля", 8: "августа",
        9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
    }
    today = datetime.date.today()
    # Собираем строку: День + Месяц из словаря + Год + г.
    current_date = f"{today.day} {months_ru[today.month]} {today.year} г."
    current_time = datetime.datetime.now().strftime("%H:%M")

    # Имитация данных о погоде (без изменений)
    weather_icon = ":material/sunny:"
    weather_temp = "+16°C"
    
    # Display database statistics
    stats = db.get_equipment_statistics()

    # Информационная строка под логотипом (оригинальный st.caption)
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
    
    # Отрисовка названия с вашей структурой `.header-wrapper` и линией под размер контента
    st.markdown(f"""
        <style>
        .header-container-underlined {{
            /* 🚨 ИСПРАВЛЕНИЕ: Убраны все отрицательные отступы. Линия теперь строго под размер приложения */
            width: 100% !important;
            box-sizing: border-box;
            
            /* Тонкая синяя полоса строго под названием */
            border-bottom: 3px solid #140A9A; 
            padding-bottom: 8px;      /* Зазор от слова WORKSHOP до синей линии */
            margin-bottom: 25px;       /* Расстояние от синей линии вниз до ваших вкладок */
        }}
        
        .header-logo-text {{
            margin: 0; 
            padding: 0; 
            font-size: 38px; 
            font-weight: 800; 
            color: #140A9A !important; 
            line-height: 1;
        }}
        </style>

        <!-- Обертка для разделительной линии, которая подстраивается под ширину контента -->
        <div class="header-container-underlined">
            <!-- Ваша оригинальная структура связки значка и названия из style.css -->
            <div class="header-wrapper">
                <svg class="{gear_class}" width="34" height="34" viewBox="0 0 24 24" xmlns="http://w3.org">
                    <path d="M19.43 12.98c.04-.32.07-.64.07-.98s-.03-.66-.07-.98l2.11-1.65c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.3-.61-.22l-2.49 1c-.52-.4-1.08-.73-1.69-.98l-.38-2.65C14.46 2.18 14.25 2 14 2h-4c-.25 0-.46.18-.49.42l-.38 2.65c-.61.25-1.17.59-1.69.98l-2.49-1c-.23-.09-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64l2.11 1.65c-.04.32-.07.65-.07.98s.03.66.07.98l-2.11 1.65c-.19.15-.24.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1c.52.4 1.08.73 1.69.98l.38 2.65c.03.24.24.42.49.42h4c.25 0 .46-.18.49-.42l.38-2.65c.61-.25 1.17-.59 1.69-.98l2.49 1c.23.09.49 0 .61-.22l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.65zM12 15.5c-1.93 0-3.5-1.57-3.5-3.5s1.57-3.5 3.5-3.5 3.5 1.57 3.5 3.5-1.57 3.5-3.5 3.5z"/>
                </svg>
                <h1 class="header-logo-text">WORKSHOP</h1>
            </div>
        </div>
    """, unsafe_allow_html=True)
                   
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






def manual_add_form(df_equipment: pd.DataFrame):
    """Отрисовка формы ручного добавления техники с адаптивным скрытием уведомлений."""
    
    #  CSS СТИЛИ ДЛЯ АНИМАЦИИ ИСЧЕЗНОВЕНИЯ УВЕДОМЛЕНИЙ ПОРЯДОК РЯДОМ С КНОПКОЙ
    st.markdown(
        """
        <style>
        @keyframes fadeOutNotification {
            0% { opacity: 1; transform: translateY(0); }
            85% { opacity: 1; transform: translateY(0); }
            100% { opacity: 0; transform: translateY(-5px); visibility: hidden; }
        }
        .self-destruct-success {
            color: #2e7d32;
            font-weight: bold;
            margin-top: 10px;
            animation: fadeOutNotification 3.0s forwards;
        }
        .self-destruct-error {
            color: #d32f2f;
            font-weight: bold;
            margin-top: 10px;
            animation: fadeOutNotification 3.5s forwards;
        }
        </style>
        """, 
        unsafe_allow_html=True
    )

    # Инициализация флага успешного сохранения в памяти сессии
    if "show_fade_success" not in st.session_state:
        st.session_state["show_fade_success"] = False

    #  ИСПРАВЛЕНИЕ: Используем clear_on_submit=st.session_state["show_fade_success"], 
    # но управляем им правильно, чтобы не ломать кэш виджетов при повторных кликах после ошибок.
    with st.form("add_equipment_form", clear_on_submit=st.session_state["show_fade_success"]):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            eq_board = st.text_input("Бортовой номер *", key="add_eq_board").strip()
            eq_model = st.text_input("Модель *", key="add_eq_model").strip()
        with col2:
            eq_type = st.selectbox("Тип", FLEET_TYPES, key="add_eq_type")
            eq_serial = st.text_input("Серийный номер", key="add_eq_serial").strip()
        with col3:
            eq_year = st.text_input("Год производства", placeholder="например: 2020", key="add_eq_year").strip()
            eq_code = st.text_input("Код", key="add_eq_code").strip()                    
        with col4:
            eq_engine = st.text_input("ДВС", key="add_eq_current_engine").strip()     
            eq_engine_number = st.text_input("Номер двигателя", key="add_eq_engine_num").strip()
            
        st.write(" ")
        
        # Строка разметки для кнопки и статуса в один ряд
        btn_col, status_col = st.columns([1, 3])
        
        with btn_col:
            submitted = st.form_submit_button("Сохранить", width=250)
            
        status_placeholder = status_col.empty()
        
        # Если прошлая итерация скрипта завершилась успехом, показываем красивый текст
        if st.session_state["show_fade_success"]:
            status_placeholder.markdown('<div class="self-destruct-success">Машина успешно добавлена!</div>', unsafe_allow_html=True)
            st.session_state["show_fade_success"] = False 

        if submitted:
            # Сразу же очищаем старые сообщения об ошибках
            status_placeholder.empty()
            
            with status_placeholder.container():
                if not eq_board or not eq_model:
                    status_placeholder.markdown('<div class="self-destruct-error">Заполните обязательные поля (Бортовой номер и Модель)!</div>', unsafe_allow_html=True)
                else:
                    is_duplicate = False
                    
                    # Сканируем базу данных на дубликаты
                    if not df_equipment.empty:
                        match_board = df_equipment['eq_board'].astype(str).str.lower() == eq_board.lower()
                        match_model = df_equipment['eq_model'].astype(str).str.lower() == eq_model.lower()
                        exact_duplicate = match_board & match_model
                        
                        if exact_duplicate.any():
                            matched_row = df_equipment[exact_duplicate].iloc[0]
                            existing_type = matched_row.get('eq_type', '')
                            
                            status_placeholder.markdown(
                                f'<div class="self-destruct-error">Ошибка: Бортовой номер {eq_board} с моделью {eq_model} уже существует ({existing_type})!</div>', 
                                unsafe_allow_html=True
                            )
                            is_duplicate = True

                    # Если дубликатов нет, выполняем сохранение
                    if not is_duplicate:
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
                            
                            # Переключаем флаг успеха и взводим автоматическую очистку для следующего рендеринга
                            st.session_state["show_fade_success"] = True
                            
                            #  РЕШЕНИЕ: Вместо ручной перезаписи 'st.session_state', мы просто вызываем st.rerun().
                            # Так как флаг "show_fade_success" теперь равен True, Streamlit при перезапуске 
                            # увидит clear_on_submit=True, сам очистит форму и отобразит анимацию успеха.
                            st.rerun() 
                            
                        except Exception as e:
                            status_placeholder.markdown(f'<div class="self-destruct-error"> Ошибка при сохранении: {e}</div>', unsafe_allow_html=True)




def reset_update_modal_filters():
    st.session_state["m_up_q"] = ""
    st.session_state["m_up_t"] = "Все"
    st.session_state["m_up_reset_counter"] = st.session_state.get("m_up_reset_counter", 0) + 1

@st.dialog("📝 Редактировать существующую технику")
def manual_update_modal(df_equipment: pd.DataFrame):
    """Окно изменения с мгновенным сообщением и авто-обновлением таблицы на фоне."""
    if "m_up_q" not in st.session_state: st.session_state["m_up_q"] = ""
    if "m_up_t" not in st.session_state: st.session_state["m_up_t"] = "Все"
    if "m_up_reset_counter" not in st.session_state: st.session_state["m_up_reset_counter"] = 0

    count = st.session_state["m_up_reset_counter"]
    
    col_src, col_type = st.columns(2)
    with col_src:
        lookup_query = st.text_input("Бортовой номер техники", placeholder="Введите бортовой номер...", key=f"m_up_board_input_{count}").strip().lower()
    with col_type:
        type_options = ["Все"] + FLEET_TYPES
        selected_type = st.selectbox("Тип техники", type_options, key=f"m_up_type_select_{count}")

    btn_find_col, btn_reset_col = st.columns(2)
    with btn_find_col:
        trigger_find = st.button("🔍 Найти", type="primary", use_container_width=True, key="m_up_find_action_btn")
    with btn_reset_col:
        has_search = bool(st.session_state["m_up_q"] or st.session_state["m_up_t"] != "Все" or lookup_query or selected_type != "Все")
        st.button("🔄 Сбросить", disabled=not has_search, use_container_width=True, key="m_up_reset_action_btn", on_click=reset_update_modal_filters)

    if trigger_find:
        st.session_state["m_up_q"] = lookup_query
        st.session_state["m_up_t"] = selected_type

    active_search = st.session_state["m_up_q"]
    active_type = st.session_state["m_up_t"]

    if not active_search and active_type == "Все":
        st.info("Введите бортовой номер или выберите тип техники и нажмите 'Найти'.")
        return

    filtered = df_equipment.copy()
    if active_search:
        mask = filtered['eq_board'].astype(str).str.lower().str.contains(active_search, na=False)
        filtered = filtered[mask]
    if active_type != "Все":
        filtered = filtered[filtered['eq_type'] == active_type]

    if filtered.empty:
        st.error("Техника с такими параметрами не найдена.")
        return

    filtered['display_label'] = filtered['eq_board'].astype(str) + " | " + filtered['eq_type'].astype(str) + " | " + filtered['eq_model'].astype(str)
    selected_label = st.selectbox("Найдено совпадений. Выберите нужную цель:", filtered['display_label'].tolist(), key=f"modal_update_target_{count}")
    
    matched_rows = filtered[filtered['display_label'] == selected_label]
    if matched_rows.empty:
        st.error("Ошибка при выборе машины.")
        return
        
    current_eq = matched_rows.iloc[0]
    equipment_id = int(current_eq['id'])
    
    try: type_index = FLEET_TYPES.index(str(current_eq.get('eq_type', '')).strip())
    except ValueError: type_index = 0

    with st.form(f"modal_update_execution_form_{equipment_id}_{count}", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            eq_board = st.text_input("Бортовой номер *", value=str(current_eq.get('eq_board', '')), key=f"m_up_board_{equipment_id}_{count}").strip()
            eq_model = st.text_input("Модель *", value=str(current_eq.get('eq_model', '')), key=f"m_up_model_{equipment_id}_{count}").strip()
            eq_type = st.selectbox("Тип", FLEET_TYPES, index=type_index, key=f"m_up_type_{equipment_id}_{count}")
            eq_serial = st.text_input("Серийный номер", value=get_clean_db_value(current_eq, 'eq_serial'), key=f"m_up_serial_{equipment_id}_{count}").strip()
        with col2:
            eq_year = st.text_input("Год производства", value=get_clean_db_value(current_eq, 'eq_year'), key=f"m_up_year_{equipment_id}_{count}").strip()
            eq_code = st.text_input("Код", value=get_clean_db_value(current_eq, 'eq_code'), key=f"m_up_code_{equipment_id}_{count}").strip()
            eq_engine = st.text_input("ДВС", value=get_clean_db_value(current_eq, 'eq_engine'), key=f"m_up_engine_{equipment_id}_{count}").strip()
            eq_engine_number = st.text_input("Номер двигателя", value=get_clean_db_value(current_eq, 'eq_engine_number'), key=f"m_up_engine_num_{equipment_id}_{count}").strip()

        st.write(" ")
        submitted = st.form_submit_button("Обновить данные", use_container_width=True)
            
        status_placeholder = st.empty()

        if submitted:
            status_placeholder.empty()
            if not eq_board or not eq_model:
                status_placeholder.markdown('<div class="var-destruct-error">❌ Бортовой номер и Модель обязательны!</div>', unsafe_allow_html=True)
            else:
                is_duplicate = False
                if not df_equipment.empty:
                    match_board = df_equipment['eq_board'].astype(str).str.lower() == eq_board.lower()
                    match_model = df_equipment['eq_model'].astype(str).str.lower() == eq_model.lower()
                    match_type = df_equipment['eq_type'].astype(str).str.lower() == eq_type.lower()
                    duplicate_mask = match_board & match_model & match_type & (df_equipment['id'].astype(int) != equipment_id)
                    
                    if duplicate_mask.any():
                        status_placeholder.markdown(f'<div class="self-destruct-error">❌ Ошибка: В базе уже существует точно такая же техника!</div>', unsafe_allow_html=True)
                        is_duplicate = True

                if not is_duplicate:
                    try:
                        db.update_equipment(equipment_id=equipment_id, eq_board=eq_board, eq_type=eq_type, eq_model=eq_model, eq_serial=eq_serial, eq_year=eq_year, eq_engine=eq_engine, eq_engine_number=eq_engine_number, eq_code=eq_code)
                        
                        # 1. Выводим текст успеха под кнопкой
                        status_placeholder.markdown('<div class="self-destruct-success">✅ Данные техники успешно обновлены в базе!</div>', unsafe_allow_html=True)
                        
                        # Сбрасываем кэш
                        st.session_state["m_up_q"] = ""
                        st.session_state["m_up_t"] = "Все"
                        st.session_state["m_up_reset_counter"] += 1
                        
                        # 2. 🚨 МИКРО-ТАЙМАУТ: Ждем 1.2 секунды
                        time.sleep(1.2)
                        
                        # 3. Перезапускаем страницу — таблица на фоне обновится, а окно закроется
                        st.rerun() 
                    except Exception as e:
                        status_placeholder.markdown(f'<div class="self-destruct-error">❌ Ошибка: {e}</div>', unsafe_allow_html=True)















def reset_delete_modal_filters():
    st.session_state["m_del_q"] = ""
    st.session_state["m_del_t"] = "Все"
    st.session_state["m_del_reset_counter"] = st.session_state.get("m_del_reset_counter", 0) + 1

@st.dialog("❌ Безвозвратное удаление техники")
def manual_delete_modal(df_equipment: pd.DataFrame):
    """Окно удаления техники со мгновенным сообщением и авто-обновлением таблицы на фоне."""
    if "m_del_q" not in st.session_state: st.session_state["m_del_q"] = ""
    if "m_del_t" not in st.session_state: st.session_state["m_del_t"] = "Все"
    if "m_del_reset_counter" not in st.session_state: st.session_state["m_del_reset_counter"] = 0

    count = st.session_state["m_del_reset_counter"]

    col_src, col_type = st.columns(2)
    with col_src:
        lookup_query = st.text_input("Бортовой номер техники", placeholder="Введите бортовой номер...", key=f"m_del_board_input_{count}").strip().lower()
    with col_type:
        type_options = ["Все"] + FLEET_TYPES
        selected_type = st.selectbox("Тип техники", type_options, key=f"m_del_type_select_{count}")

    btn_find_col, btn_reset_col = st.columns(2)
    with btn_find_col:
        trigger_find = st.button("🔍 Найти", type="primary", use_container_width=True, key="m_del_find_action_btn")
    with btn_reset_col:
        has_search = bool(st.session_state["m_del_q"] or st.session_state["m_del_t"] != "Все" or lookup_query or selected_type != "Все")
        st.button("🔄 Сбросить", disabled=not has_search, use_container_width=True, key="m_del_reset_action_btn", on_click=reset_delete_modal_filters)

    if trigger_find:
        st.session_state["m_del_q"] = lookup_query
        st.session_state["m_del_t"] = selected_type

    active_search = st.session_state["m_del_q"]
    active_type = st.session_state["m_del_t"]

    if not active_search and active_type == "Все":
        st.info("Введите бортовой номер или выберите тип техники и нажмите 'Найти'.")
        return

    filtered = df_equipment.copy()
    if active_search:
        mask = filtered['eq_board'].astype(str).str.lower().str.contains(active_search, na=False)
        filtered = filtered[mask]
    if active_type != "Все":
        filtered = filtered[filtered['eq_type'] == active_type]

    if filtered.empty:
        st.error("Техника с такими параметрами не найдена.")
        return

    filtered['display_label'] = filtered['eq_board'].astype(str) + " | " + filtered['eq_type'].astype(str) + " | " + filtered['eq_model'].astype(str)
    selected_label = st.selectbox("Выберите точную машину для УДАЛЕНИЯ:", filtered['display_label'].tolist(), key=f"modal_delete_target_{count}")
    
    matched_rows = filtered[filtered['display_label'] == selected_label]
    if matched_rows.empty:
        st.error("Ошибка при выборе машины.")
        return
        
    current_eq = matched_rows.iloc[0]
    equipment_id = int(current_eq['id'])
    
    st.markdown(" ")
    st.markdown(
        f"""
        <div style='background-color: #ffebee; border-left: 5px solid #d32f2f; padding: 12px; margin-bottom: 15px; border-radius: 4px;'>
            <span style='color: #c62828; font-weight: bold;'>⚠️ Внимание!</span> 
            <span style='color: #c62828;'>Вы собираетесь навсегда удалить объект:</span><br>
            <strong>{selected_label}</strong>
        </div>
        """, 
        unsafe_allow_html=True
    )

    with st.form(f"modal_delete_execution_form_{equipment_id}_{count}", clear_on_submit=True):
        confirm_delete = st.checkbox("Я подтверждаю, что хочу удалить эту единицу из ERP системы")
        submitted = st.form_submit_button("Удалить технику из базы", type="primary", use_container_width=True)
        
        status_placeholder = st.empty()
        
        if submitted:
            if not confirm_delete:
                status_placeholder.markdown('<div class="self-destruct-error">❌ Необходимо поставить галочку подтверждения операции!</div>', unsafe_allow_html=True)
            else:
                try:
                    db.delete_equipment(equipment_id=equipment_id)
                    # 1. Выводим текст успеха строго под кнопкой мгновенно
                    status_placeholder.markdown('<div class="self-destruct-success">🛑 Единица техники успешно удалена из системы!</div>', unsafe_allow_html=True)
                    
                    # Сбрасываем фильтры поиска внутри окна, чтобы оно открывалось чистым
                    st.session_state["m_del_q"] = ""
                    st.session_state["m_del_t"] = "Все"
                    st.session_state["m_del_reset_counter"] += 1
                    
                    # 2. 🚨 МИКРО-ТАЙМАУТ: Замораживаем скрипт на 1.2 секунды, чтобы юзер успел прочесть текст
                    time.sleep(1.2)
                    
                    # 3. Перезапускаем страницу — таблица на фоне обновится, а открытое окно закроется
                    st.rerun()
                except Exception as e:
                    status_placeholder.markdown(f'<div class="self-destruct-error">❌ Ошибка: {e}</div>', unsafe_allow_html=True)














                    
                    

def import_form():
    """Render Excel import form."""
    uploaded_file = st.file_uploader(
        "Загрузить файл XLSX для обновления/импорта:", 
        type=["xlsx"], 
        key="excel_uploader"
    )
    if uploaded_file is not None:
        if st.button("Импортировать", type="primary", width='stretch'):
            process_and_save_excel(uploaded_file)
            
def get_clean_db_value(row_data, field_key: str) -> str:
    """Safely extracts a database field value and avoids printing text like 'None' or 'NaN'."""
    val = row_data.get(field_key)
    if pd.isna(val) or val is None or str(val).strip().lower() == "none":
        return ""
    return str(val)

def export_forms(export_buffer: io.BytesIO):
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
 

def equipment_tab():
    """Render equipment management tab."""
    # 1. Загружаем сырые данные из базы один раз
    df_raw = db.load_equipment()
    
    if not df_raw.empty:
        df_raw['eq_type'] = df_raw['eq_type'].astype(str).str.strip()

    # Оставляем только импорт/экспорт (если админ хочет скачать файл, вы можете разместить это внизу страницы)
    export_buffer = prepare_export_dataframe(df_raw)
    
    if df_raw.empty:
        st.info("База данных пуста. Добавьте технику.")
        # Если база пуста, показываем админу кнопку добавления прямо на экране
        if st.session_state.role == "admin":
            if st.button("➕ Добавить первую машину", type="primary"):
                manual_add_modal(df_raw)
        return
    
    # 2. Передаем сырые данные в фильтры. 
    # Внутри этой функции отрисуются и инпуты поиска, и кнопки Добавить/Изменить/Удалить!
    filtered_data = equipment_filters(df_raw)
    
    # 3. Выводим отфильтрованный результат в итоговую таблицу ниже управления
    equipment_table(filtered_data)

    



# FIX: Change the header line to accept BOTH arguments
def admin_panel(export_buffer: io.BytesIO, df_equipment: pd.DataFrame):
    """Render admin panel with add, import, export functionality."""
    with st.expander("Редактировать список техники", expanded=False):
        tab1, tab2, tab3, tab4 = st.tabs(["Добавить технику", "Изменить данные", "Удалить единицу", "Загрузить или скачать список"])
        
        with tab1:
            if st.button("➕ Добавить новую единицу", type="primary"):
                
            # manual_add_form(df_equipment)
                manual_add_modal(df_equipment)
        with tab2:
            manual_update_form(df_equipment)            
        with tab3:
            manual_delete_form(df_equipment)
        with tab4:
            with st.container(border=True):
                import_form()
            with st.container(border=True):
                export_forms(export_buffer)


# Global clear callback function
def clear_search_filters():
    """Safely clear input caches in memory before page rendering."""
    st.session_state["filter_search"] = ""
    st.session_state["filter_type"] = "Все"
    # Clear the form-specific locked values as well
    if "submitted_search" in st.session_state:
        st.session_state["submitted_search"] = ""
    if "submitted_type" in st.session_state:
        st.session_state["submitted_type"] = "Все"


def equipment_filters(df_equipment: pd.DataFrame) -> pd.DataFrame:
    """Отрендеренная панель поиска и управления с идеальным расположением кнопок в ряд."""
    st.caption("Поиск и управление техникой")
    
    # Инициализация состояний, если их нет
    if "submitted_search" not in st.session_state:
        st.session_state["submitted_search"] = ""
    if "submitted_type" not in st.session_state:
        st.session_state["submitted_type"] = "Все"

    # РЯД 1: Поля ввода (Без st.form, чтобы не было подсказок "Press Enter")
    col1, col2 = st.columns(2)
    with col1:
        search_query = st.text_input(
            "Поиск", 
            value=st.session_state["submitted_search"],
            placeholder="Бортовой номер, модель...", 
            key="filter_search"
        )
    with col2:
        type_options = ["Все"] + FLEET_TYPES
        try:
            type_idx = type_options.index(st.session_state["submitted_type"])
        except ValueError:
            type_idx = 0
        selected_type = st.selectbox("Тип техники", type_options, index=type_idx, key="filter_type")
        
    st.write(" ") # Небольшой зазор перед кнопками

    # 🚨 РЕШЕНИЕ ПРОБЛЕМЫ 2: Единый ряд из кнопок. 
    # Если админ: Найти (1) | Сбросить (1) | Добавить (1) | Изменить (1) | Удалить (1)
    # Задаем сетку из 5 равных колонок
    act_col1, act_col2, act_col3, act_col4, act_col5 = st.columns(5)
    
    with act_col1:
        # Кнопка НАЙТИ теперь стоит на первом месте слева
        if st.button("🔍 Найти", type="primary", width='stretch', key="main_search_submit_btn"):
            st.session_state["submitted_search"] = search_query
            st.session_state["submitted_type"] = selected_type
            st.rerun()
            
    with act_col2:
        # Кнопка СБРОСИТЬ фильтры стоит сразу же справа от нее
        has_active_filters = bool(st.session_state["submitted_search"] or st.session_state["submitted_type"] != "Все")
        st.button(
            "🔄 Сбросить", 
            disabled=not has_active_filters, 
            width='stretch',
            on_click=clear_search_filters,
            key="main_search_reset_btn"
        )

    # Код кнопок управления внутри вашей функции equipment_filters
    if st.session_state.get("role") == "admin":
        with act_col3:
            if st.button("➕ Добавить", width='stretch', key="panel_add_btn"):
                manual_add_modal(df_equipment)
                
        with act_col4:
            if st.button("📝 Изменить", width='stretch', key="panel_edit_btn"):
                # 🚨 ПРЕВЕНТИВНЫЙ СБРОС: Стираем флаг успеха из памяти перед открытием окна!
                st.session_state["show_update_success"] = False
                
                # Очищаем старый кэш поиска, как делали ранее
                st.session_state["m_up_q"] = ""
                st.session_state["m_up_t"] = "Все"
                st.session_state["m_up_reset_counter"] = st.session_state.get("m_up_reset_counter", 0) + 1
                
                # Теперь безопасно открываем окно изменения
                manual_update_modal(df_equipment)
                
        with act_col5:
            if st.button("❌ Удалить", width='stretch', key="panel_delete_btn"):
                # 🚨 Сначала очищаем старый кэш в памяти
                st.session_state["m_del_q"] = ""
                st.session_state["m_del_t"] = "Все"
                st.session_state["m_del_reset_counter"] = st.session_state.get("m_del_reset_counter", 0) + 1
                # Открываем окно
                manual_delete_modal(df_equipment)

    st.write("---")
    
    # Применение подтвержденной фильтрации к таблице
    filtered_df = df_equipment.copy()
    confirm_q = st.session_state["submitted_search"]
    confirm_type = st.session_state["submitted_type"]

    if confirm_q:
        q = confirm_q.strip().lower()
        mask = (
            filtered_df['eq_board'].astype(str).str.lower().str.contains(q, na=False) |
            filtered_df['eq_model'].astype(str).str.lower().str.contains(q, na=False) |
            filtered_df['eq_serial'].astype(str).str.lower().str.contains(q, na=False)
        )
        filtered_df = filtered_df[mask]
    
    if confirm_type != "Все":
        filtered_df = filtered_df[filtered_df['eq_type'] == confirm_type]
        
    return filtered_df.reset_index(drop=True)


def equipment_table(df_to_display: pd.DataFrame):
    """Отрисовка таблицы техники в режиме чтения без использования data_editor."""
    st.caption("Список техники")
    
    if df_to_display.empty:
        st.info("Техника с такими параметрами не найдена. Попробуйте изменить фильтры.")
        return
        
    # Настройка отображения колонок (все поля ввода заблокированы для редактирования)
    column_config = {
        "eq_board": st.column_config.TextColumn("Бортовой номер"),
        "eq_type": st.column_config.TextColumn("Тип"),
        "eq_model": st.column_config.TextColumn("Модель"),
        "eq_serial": st.column_config.TextColumn("Серийный номер"),
        "eq_year": st.column_config.TextColumn("Год производства"),
        "eq_engine": st.column_config.TextColumn("ДВС"),
        "eq_engine_number": st.column_config.TextColumn("Номер двигателя"),
        "eq_code": st.column_config.TextColumn("Код"),
    }
    
    # Извлекаем только нужные для отображения колонки (без системного ID)
    display_df = df_to_display[DISPLAY_COLUMNS].copy()
    
    # Рендерим стабильный фрейм данных, который гарантированно не ломает интерфейс
    st.dataframe(
        display_df, 
        column_config=column_config, 
        use_container_width=True,
        hide_index=True
    )



@st.dialog("➕ Добавить новую технику в базу")
def manual_add_modal(df_equipment: pd.DataFrame):
    """Render equipment addition form inside an isolated modal pop-up window with composite validation."""
    
    if "show_fade_success" not in st.session_state:
        st.session_state["show_fade_success"] = False

    with st.form("modal_add_equipment_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        
        with col1:
            eq_board = st.text_input("Бортовой номер *", key="add_eq_board").strip()
            eq_model = st.text_input("Модель *", key="add_eq_model").strip()
            eq_type = st.selectbox("Тип", FLEET_TYPES, key="add_eq_type")
            eq_serial = st.text_input("Серийный номер", key="add_eq_serial").strip()
        with col2:
            eq_year = st.text_input("Год производства", placeholder="например: 2020", key="add_eq_year").strip()
            eq_code = st.text_input("Код", key="add_eq_code").strip()                    
            eq_engine = st.text_input("ДВС", key="add_eq_current_engine").strip()     
            eq_engine_number = st.text_input("Номер двигателя", key="add_eq_engine_num").strip()
            
        st.write(" ")
        
        # Кнопка сохранения на полную ширину
        submitted = st.form_submit_button("Сохранить машину", use_container_width=True)
            
        # Слот для статуса строго ПОД кнопкой сохранения
        status_placeholder = st.empty()

        if submitted:
            status_placeholder.empty()
            
            with status_placeholder.container():
                if not eq_board or not eq_model:
                    status_placeholder.markdown('<div class="self-destruct-error">❌ Заполните обязательные поля!</div>', unsafe_allow_html=True)
                else:
                    is_duplicate = False
                    
                    # 🚨 УПРАВЛЕНИЕ ОШИБКОЙ ДУБЛИКАТОВ: Строгая композитная проверка по 3 параметрам
                    if not df_equipment.empty:
                        match_board = df_equipment['eq_board'].astype(str).str.lower() == eq_board.lower()
                        match_model = df_equipment['eq_model'].astype(str).str.lower() == eq_model.lower()
                        match_type = df_equipment['eq_type'].astype(str).str.lower() == eq_type.lower() # ➕ Добавили тип!
                        
                        # Точный дубликат признаётся ТОЛЬКО если совпали Бортовой И Модель И Тип одновременно
                        exact_duplicate = match_board & match_model & match_type
                        
                        if exact_duplicate.any():
                            status_placeholder.markdown(
                                f'<div class="self-destruct-error">❌ Ошибка: В базе уже существует **{eq_type}** с бортовым **{eq_board}** и моделью **{eq_model}**!</div>', 
                                unsafe_allow_html=True
                            )
                            is_duplicate = True

                    # Если строгий дубликат не найден — выполняем физическую запись в БД
                    if not is_duplicate:
                        try:
                            db.add_equipment(
                                eq_board=eq_board, eq_type=eq_type, eq_model=eq_model,
                                eq_serial=eq_serial, eq_year=eq_year, eq_engine=eq_engine,
                                eq_engine_number=eq_engine_number, eq_code=eq_code
                            )
                            
                            # Выводим текст успеха мгновенно под кнопкой
                            status_placeholder.markdown('<div class="self-destruct-success">✅ Машина успешно добавлена в базу!</div>', unsafe_allow_html=True)
                            
                            # Выдерживаем задержку, чтобы оператор прочитал надпись
                            time.sleep(1.2)
                            
                            # Перезапускаем страницу — таблица на фоне обновится, а окно закроется сама
                            st.rerun() 
                            
                        except Exception as e:
                            status_placeholder.markdown(f'<div class="self-destruct-error">❌ Ошибка: {e}</div>', unsafe_allow_html=True)





def settings_tab():
    """Render settings and authentication tab."""
    col1, _, col3 = st.columns([3.5, 6, 1.8])
    
    with col1:
        st.write("Настройки приложения")
           
    with col3:
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
    
    # Create header
    app_header()
    
    # Create tabs
    main_tabs = st.tabs(["ТЕХНИКА", "РАБОТЫ", "ИНСТРУМЕНТЫ", "ДОКУМЕНТЫ", "НАСТРОЙКИ"])
        
    with main_tabs[0]:
        equipment_tab()
        
    with main_tabs[1]:
        st.info("Раздел в разработке")
        
    with main_tabs[2]:
        st.info("Раздел в разработке")
        
    with main_tabs[3]:
        st.info("Раздел в разработке")
        
    with main_tabs[4]:
        settings_tab()



if __name__ == "__main__":
    main()