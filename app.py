import database.db_manager as db
import streamlit as st
import pandas as pd
import datetime
import sqlite3
import time


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
    """Тихо сохраняет изменения из таблицы прямо в базу данных SQLite в бэкграунде."""
    if "equipment_editor" in st.session_state:
        editor_state = st.session_state["equipment_editor"]
        
        # Проверяем, были ли реальные изменения строк
        if editor_state.get("edited_rows"):
            current_df = db.load_equipment()
            
            for row_idx, updated_columns in editor_state["edited_rows"].items():
                row_id = current_df.iloc[row_idx]["id"]
                for col_name, new_value in updated_columns.items():
                    
                    # 1. Обработка года производства
                    if col_name == "eq_year" and new_value:
                        try:
                            new_value = pd.to_datetime(new_value).year
                        except:
                            new_value = 2026
                            
                    # 2. ИСПРАВЛЕНИЕ: Обработка даты моточасов перед записью в SQLite
                    elif col_name == "eq_last_hours" and new_value:
                        try:
                            # Переводим в чистую строковую дату формата ГГГГ-ММ-ДД
                            new_value = pd.to_datetime(new_value).strftime('%Y-%m-%d')
                        except:
                            new_value = None
                            
                    current_df.loc[current_df["id"] == row_id, col_name] = new_value

            try:
                # Физическая запись на диск в файл fleet.db
                db.update_equipment(current_df)
            except Exception as e:
                st.error(f"Ошибка фонового сохранения: {e}")
                
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
    "eq_board": st.column_config.TextColumn("Бортовой номер"),
    "eq_type": st.column_config.SelectboxColumn("Тип", options=FLEET_TYPES, required=True),
    "eq_model": st.column_config.TextColumn("Модель"),
    "eq_serial": st.column_config.TextColumn("Серийный номер (VIN)"),        
    "eq_year": st.column_config.DateColumn("Год производства", format="YYYY"),
    "eq_engine": st.column_config.TextColumn("ДВС"),
    "eq_engine_number": st.column_config.TextColumn("Номер двигателя"),
    "eq_code": st.column_config.TextColumn("Код"),
    "eq_last_hours": st.column_config.DateColumn("Последняя дата показаний м/ч", format="DD.MM.YYYY"),
    "eq_hours": st.column_config.NumberColumn("Моточасы", format="%d"),
    "eq_status": st.column_config.SelectboxColumn("Статус", options=FLEET_STATUSES)
}

# ГЛАВНЫЕ ВКЛАДКИ
tab_titles = ["ТЕХНИКА", "РАБОТЫ", "ИНСТРУМЕНТЫ", "ДОКУМЕНТЫ", "НАСТРОЙКИ"]
tab_equipment, tab_maintenance, tab_tools, tab_docs, tab_settings = st.tabs(tab_titles)

# ВКЛАДКА ТЕХНИКА
with tab_equipment:
    
    # --- БЛОК АДМИНИСТРАТОРА: Форма добавления техники ---
    if st.session_state.role == "admin":
        with st.expander("Добавить машину"):
            with st.form("add_equipment_form", clear_on_submit=True):
                            
                col1, col2 = st.columns(2)
                with col1:
                    form_eq_board = st.text_input("Бортовой номер *")
                    form_eq_type = st.selectbox("Тип", FLEET_TYPES)
                    form_eq_model = st.text_input("Модель *")
                    form_eq_serial = st.text_input("Серийный номер")
                    form_eq_year = st.number_input("Год производства", min_value=1980, max_value=2030, value=2026)
                    form_eq_code = st.text_input("Код")

                with col2:
                    form_eq_engine = st.text_input("ДВС")
                    form_eq_engine_number = st.text_input("Номер ДВС")
                    form_eq_last_hours = st.date_input("Последняя дата показаний м/ч", value=datetime.date.today(), format="DD.MM.YYYY")
                    form_eq_hours = st.number_input("Моточасы", min_value=0, value=0)
                    form_eq_status = st.selectbox("Статус", FLEET_STATUSES)

                submitted = st.form_submit_button("Сохранить новую единицу")
                
                if submitted:
                    if not form_eq_board or not form_eq_model:
                        st.error("Бортовой номер и Модель являются обязательными полями!")
                    else:
                        try:
                            # Конвертируем дату из календаря формы в строку для SQLite
                            str_last_hours = form_eq_last_hours.strftime('%Y-%m-%d')
                            
                            db.add_equipment(
                                form_eq_board, form_eq_type, form_eq_model, form_eq_serial, int(form_eq_year),
                                form_eq_engine, form_eq_engine_number, form_eq_code, form_eq_last_hours, int(form_eq_hours), form_eq_status
                            )
                            st.toast("Машина успешно добавлена!", icon="✅")
                            st.rerun() 
                        except Exception as e:
                            st.error(f"Error saving to database: {e}")

    # --- ОБЩИЙ БЛОК: Отображение данных ---
    st.caption("Список техники")
    
    # Загружаем данные ОДИН раз (убран лишний дубликат вызова функции)
    df_equipment = db.load_equipment()
    
    # Подготавливаем типы данных перед передачей в интерфейс
    df_equipment['eq_type'] = df_equipment['eq_type'].astype(str).str.strip()
    df_equipment['eq_year'] = pd.to_datetime(df_equipment['eq_year'].astype(str) + '-01-01', errors='coerce')
    df_equipment['eq_status'] = df_equipment['eq_status'].astype(str).str.strip()
    df_equipment['eq_last_hours'] = pd.to_datetime(df_equipment['eq_last_hours'], errors='coerce')

    if st.session_state.role == "admin":
        # Убран старый блок с кнопкой ручного сохранения и баннером успеха.
        # Теперь таблица полностью автономна. Автосохранение срабатывает на лету.
        st.data_editor(
            df_equipment, 
            column_config=equipment_config, 
            use_container_width=True,
            hide_index=True,
            on_change=auto_save_equipment,
            key="equipment_editor"
        )
                
    else:
        # Гость видит обычную таблицу ТОЛЬКО ДЛЯ ЧТЕНИЯ
        st.dataframe(
            df_equipment, 
            column_config=equipment_config, 
            use_container_width=True,
            hide_index=True
        )



# # ВКЛАДКА РАБОТЫ
# with tab_maintenance:
#     st.subheader("Operation Logs")
    
#     # Gather live machines to load select boxes
#     raw_machines = run_query("SELECT name FROM equipment")
#     machine_names = [m[0] for m in raw_machines]
    
#     if st.session_state.role == "admin" and machine_names:
#         with st.form("hours_form", clear_on_submit=True):
#             st.markdown("**Update Running Metrics**")
#             target_unit = st.selectbox("Target Equipment Profile", machine_names)
#             added_runtime = st.number_input("Add Shift Motohours Run Today", min_value=0, max_value=24, step=1)
            
#             if st.form_submit_button("Commit Runtime Logs"):
#                 run_query("UPDATE equipment SET motohours = motohours + ? WHERE name = ?", (added_runtime, target_unit))
#                 st.success(f"Log stored: Updated +{added_runtime} runtime hours for {target_unit}.")
#                 st.rerun()
#     elif not machine_names:
#         st.warning("No equipment registered in system inventory data files yet.")
#     else:
#         st.info("Log tracking metrics write-forms are locked. Log in via Dashboard tab to make entries.")


# # ВКЛАДКА ИНСТРУМЕНТ
# with tab_tools:
#     st.subheader("Spare Parts Database")

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