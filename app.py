import streamlit as st
import pandas as pd
import datetime
import sqlite3
import database.db_manager as db

# Настройка страницы
st.set_page_config(page_title="/", layout="wide", page_icon="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")

def load_external_css(file_path):
    """Reads external styles and safely injects them."""
    try:
        with open(file_path, "r", encoding="utf-8") as file_stream:
            css_rules = file_stream.read()
            st.markdown(
                f"<style>{css_rules}</style>",
                unsafe_allow_html=True,
            )
    except FileNotFoundError:
        st.error(f"CSS File not found at: {file_path}")

load_external_css(".streamlit/style.css")

# Загрузка или создание БД
db.init_db()

# Инициализация роли по умолчанию (Гость)
if "role" not in st.session_state:
    st.session_state.role = "guest"

# Подставляем класс: icon-admin (Komatsu Blue + Yellow Glow) или icon-guest (Muted Gray)
gear_class = "icon-admin" if st.session_state.role == "admin" else "icon-guest"

# Рендерим HTML-логотип
st.markdown(f"""
    <div class="header-wrapper">
        <svg class="{gear_class}" width="34" height="34" viewBox="0 0 24 24" xmlns="http://w3.org">
            <path d="M19.43 12.98c.04-.32.07-.64.07-.98s-.03-.66-.07-.98l2.11-1.65c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.3-.61-.22l-2.49 1c-.52-.4-1.08-.73-1.69-.98l-.38-2.65C14.46 2.18 14.25 2 14 2h-4c-.25 0-.46.18-.49.42l-.38 2.65c-.61.25-1.17.59-1.69.98l-2.49-1c-.23-.09-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64l2.11 1.65c-.04.32-.07.65-.07.98s.03.66.07.98l-2.11 1.65c-.19.15-.24.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1c.52.4 1.08.73 1.69.98l.38 2.65c.03.24.24.42.49.42h4c.25 0 .46-.18.49-.42l.38-2.65c.61-.25 1.17-.59 1.69-.98l2.49 1c.23.09.49 0 .61-.22l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.65zM12 15.5c-1.93 0-3.5-1.57-3.5-3.5s1.57-3.5 3.5-3.5 3.5 1.57 3.5 3.5-1.57 3.5-3.5 3.5z"/>
        </svg>
        <h1 style="margin:0; padding:0; font-size:40px; font-weight:800; color:#140A9A; margin-left:10px; display:inline-block; vertical-align:middle;">IT НАРЯДКА</h1>
    </div>
""", unsafe_allow_html=True)


current_date = datetime.date.today().strftime('%d.%m.%Y')
current_time = datetime.datetime.now().strftime("%H:%M")
current_role = st.session_state.get("role", "guest")

# Информационная строка под логотипом

col_date, col_time, col_role, _ ,_ = st.columns([1.5, 1.5, 3, 6, 6])
with col_date:
    st.caption(f"Дата : {current_date}")
with col_time:
    st.caption(f"Время : {current_time}")
with col_role:
    if "fleet_duck.db":
        # st.caption(f"Пользователь: {current_role}")
        st.caption(f"Подключение к БД установлено")

    

# ГЛАВНЫЕ ВКЛАДКИ
tab_titles = ["ТЕХНИКА", "РАБОТЫ", "ИНСТРУМЕНТЫ", "ДОКУМЕНТЫ", "НАСТРОЙКИ"]
tab_equipment, tab_maintenance, tab_tools, tab_docs, tab_settings = st.tabs(tab_titles)



# ВКЛАДКА ТЕХНИКА
with tab_equipment:
    equipment_config = {
        "id": None,
        "board": st.column_config.TextColumn("Бортовой номер"),
        "type": st.column_config.TextColumn("Тип"),
        "model": st.column_config.TextColumn("Модель"),
        "serial": st.column_config.TextColumn("Серийный номер (VIN)"),        
        "year": st.column_config.NumberColumn("Год производства", format="%Y"),
        "engine": st.column_config.TextColumn("ДВС"),
        "engine_number": st.column_config.TextColumn("Номер двигателя"),
        "code": st.column_config.TextColumn("Код"),
        "last_hours": st.column_config.TextColumn("Последняя дата показаний м/ч"),
        "hours": st.column_config.NumberColumn("Моточасы", format="%d"),
        "status": st.column_config.TextColumn("Статус")
    }

    st.write("Список техники")

    # ==============================================================================
    # 1. ПАНЕЛЬ АДМИНИСТРАТОРА (ДОБАВЛЕНИЕ) — Только для Admin
    # ==============================================================================
    if st.session_state.get("role") == "admin":
        with st.expander(
            "Добавить технику", expanded=False
        ):
            with st.form("admin_hardware_form", clear_on_submit=True):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    eq_board = st.text_input(
                        "Бортовой номер *", placeholder="38"
                    )
                    eq_type = st.selectbox(
                        "Тип техники",
                        [
                            "Самосвал",
                            "Экскаватор",
                            "Бульдозер",
                            "Грейдер",
                            "Погрузчик",
                        ],
                    )
                with col2:
                    eq_model = st.text_input(
                        "Модель *", placeholder="HD785-7"
                    )
                    eq_serial = st.text_input("Серийный номер", placeholder="32816")
                with col3:
                    eq_year = st.number_input(
                        "Год выпуска",
                        min_value=1980,
                        max_value=2030,
                        value=2024,
                    )
                    eq_engine = st.text_input(
                        "Модель ДВС", placeholder="SAA12V140E-3"
                    )
                with col4:
                    eq_engine_num = st.text_input(
                        "Номер ДВС", placeholder="511502"
                    )
                    eq_code = st.text_input("Код", placeholder="0000642C")

                sub_col1, sub_col2 = st.columns(2)
                with sub_col1:
                    eq_hours = st.number_input(
                        "Стартовые моточасы", min_value=0, step=1
                    )
                with sub_col2:
                    eq_status = st.selectbox(
                        "Текущий статус", ["В работе", "В ремонте", "В резерве"]
                    )

                submit_btn = st.form_submit_button("Зарегистрировать технику")

                if submit_btn:
                    if not eq_board or not eq_model:
                        st.error("Заполните обязательные поля (*)!")
                    else:
                        try:
                            today_str = (
                                datetime.date.today().strftime("%d.%m.%Y")
                            )
                            run_query(
                                """
                                INSERT INTO equipment (board, type, model, serial, year, engine, engine_number, code, last_hours, hours, status) 
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                                (
                                    eq_board,
                                    eq_type,
                                    eq_model,
                                    eq_serial,
                                    eq_year,
                                    eq_engine,
                                    eq_engine_num,
                                    eq_code,
                                    today_str,
                                    eq_hours,
                                    eq_status,
                                ),
                            )
                            st.success("Техника добавлена!")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Бортовой номер уже существует!")

    # ==============================================================================
    # 2. ПОЛУЧЕНИЕ ДАННЫХ ИЗ БД (Общее для всех режимов)
    # ==============================================================================
    try:
        raw_data = get_data("SELECT id, board, type, model, serial, year, engine, engine_number, code, last_hours, hours, status FROM equipment")
        df_eq = pd.DataFrame(raw_data)
    except Exception as e:
        df_eq = pd.DataFrame()

    # 🔥 ЗАЩИТА ОТ КРАША: Если DataFrame пустой или база еще не создана,
    # мы принудительно создаем пустую таблицу с правильными именами колонок
    if df_eq.empty:
        df_eq = pd.DataFrame(columns=[
            "id", "board", "type", "model", "serial", "year", 
            "engine", "engine_number", "code", "last_hours", "hours", "status"
        ])


    # ==============================================================================
    # 4. ОБЩИЙ ПОИСК / ФИЛЬТРАЦИЯ (Видят ВСЕ пользователи)
    # ==============================================================================
    st.markdown("##### Поиск техники")
    f_col1, f_col2, f_col3, f_col4 = st.columns(4)

    with f_col1:
        filter_board = st.text_input("Бортовой номер", placeholder="Все")
    with f_col2:
        filter_type = st.text_input("Тип", placeholder="Все")
    with f_col3:
        filter_model = st.text_input("Модель", placeholder="Все")
    with f_col4:
        filter_status = st.text_input("Статус", placeholder="Все")

    # Применение фильтров к данным перед выводом на экран
    df_filtered = df_eq.copy()

    if filter_board:
        df_filtered = df_filtered[
            df_filtered["board"].astype(str).str.contains(filter_board)
        ]
    if filter_type:
        df_filtered = df_filtered[
            df_filtered["type"].str.contains(filter_type, case=False)
        ]
    if filter_model:
        df_filtered = df_filtered[
            df_filtered["model"].str.contains(filter_model, case=False)
        ]
    if filter_status:
        df_filtered = df_filtered[
            df_filtered["status"].str.contains(filter_status, case=False)
        ]

    st.markdown("---")

    # ==============================================================================
    # 5. ИТОГОВАЯ ТАБЛИЦА (Видят ВСЕ пользователи)
    # ==============================================================================
    st.markdown("##### Список техники")

    if not df_filtered.empty:
        st.dataframe(
            df_filtered,
            column_config=equipment_config,
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("Техника по указанным критериям фильтрации не найдена.")



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


# ВКЛАДКА ИНСТРУМЕНТ
with tab_tools:
    st.subheader("Spare Parts Database")

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