from openpyxl.utils import get_column_letter
import database.db_manager as db
from pathlib import Path
from bs4 import BeautifulSoup
import streamlit as st
import pandas as pd
import threading
import datetime
import requests
import logging
import time
import os
import io


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== CONSTANTS ====================

FLEET_TYPES = [
    "Автогрейдер",
    "Вилочный погрузчик",
    "Гусеничный бульдозер",
    "Гусеничный экскаватор",
    "Колесный бульдозер",
    "Колесный экскаватор",
    "Самосвал",
    "Телескопический погрузчик",
    "Фронтальный погрузчик",
    "Шинный манипулятор"
]





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
    """Отображение оригинальной шапки приложения WORKSHOP с идеальной иконкой шестеренки."""
    gear_class = "icon-admin" if st.session_state.get("role") == "admin" else "icon-guest"
    
    months_ru = {
        1: "января", 2: "февраля", 3: "марта", 4: "апреля",
        5: "мая", 6: "июня", 7: "июля", 8: "августа",
        9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
    }
    today = datetime.date.today()
    current_date = f"{today.day} {months_ru[today.month]} {today.year} г."
    current_time = datetime.datetime.now().strftime("%H:%M")
    
    try:
        stats = db.get_equipment_statistics()
        total_equipment = stats.get('total', 0)
    except Exception:
        total_equipment = 0

    # Информационная строка под логотипом
    divider = "|"
    base_meta = (
        f":material/calendar_month: {current_date}"
        f"&emsp;{divider}&emsp;"
        f":material/schedule: {current_time}"
        f"&emsp;{divider}&emsp;"
        f":material/satellite_alt: Соединение установлено :green[:material/database:]"
        f"&emsp;{divider}&emsp;"
        f":yellow[:material/front_loader:] Всего техники: **{total_equipment}**"
    )
    st.caption(base_meta, unsafe_allow_html=True)
    
    # Отрисовка названия со старой структурой .header-wrapper и линией
    st.markdown(f"""
        <style>
        .header-container-underlined {{
            width: 100% !important;
            box-sizing: border-box;
            border-bottom: 3px solid #140A9A; 
            padding-bottom: 0px;      
            margin-bottom: 15px;       
        }}
        
        .header-logo-text {{
            margin: 0; 
            padding: 0; 
            font-size: 48px; 
            font-weight: 600; 
            color: #140A9A !important; 
            line-height: 1;
        }}
        </style>

        <div class="header-container-underlined">
            <div class="header-wrapper">
                <svg class="{gear_class}" width="34" height="34" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M19.43 12.98c.04-.32.07-.64.07-.98s-.03-.66-.07-.98l2.11-1.65c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.3-.61-.22l-2.49 1c-.52-.4-1.08-.73-1.69-.98l-.38-2.65C14.46 2.18 14.25 2 14 2h-4c-.25 0-.46.18-.49.42l-.38 2.65c-.61.25-1.17.59-1.69.98l-2.49-1c-.23-.09-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64l2.11 1.65c-.04.32-.07.65-.07.98s.03.66.07.98l-2.11 1.65c-.19.15-.24.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1c.52.4 1.08.73 1.69.98l.38 2.65c.03.24.24.42.49.42h4c.25 0 .46-.18.49-.42l.38-2.65c.61-.25 1.17-.59 1.69-.98l2.49 1c.23.09.49 0 .61-.22l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.65zM12 15.5c-1.93 0-3.5-1.57-3.5-3.5s1.57-3.5 3.5-3.5 3.5 1.57 3.5 3.5-1.57 3.5-3.5 3.5z"/>
                </svg>
                <h1 class="header-logo-text">MECHANIK</h1>
            </div>
        </div>
    """, unsafe_allow_html=True)
    








def reset_update_modal_filters():
    """Сброс фильтров поиска внутри модального окна редактирования."""
    st.session_state["m_up_q"] = ""
    st.session_state["m_up_t"] = "Все"
    st.session_state["m_up_reset_counter"] = (
        st.session_state.get("m_up_reset_counter", 0) + 1
    )


@st.dialog(":material/edit: Редактировать существующую технику", width="large")
def manual_update_modal(df_equipment: pd.DataFrame):
    """Окно изменения с мгновенным сообщением и авто-обновлением таблицы на фоне."""
    if "m_up_q" not in st.session_state:
        st.session_state["m_up_q"] = ""
    if "m_up_t" not in st.session_state:
        st.session_state["m_up_t"] = "Все"
    if "m_up_reset_counter" not in st.session_state:
        st.session_state["m_up_reset_counter"] = 0

    count = st.session_state["m_up_reset_counter"]

    col_src, col_type = st.columns(2)
    with col_src:
        lookup_query = (
            st.text_input(
                "Бортовой номер техники",
                placeholder="Введите бортовой номер...",
                key=f"m_up_board_input_{count}",
            )
            .strip()
            .lower()
        )
    with col_type:
        type_options = ["Все"] + FLEET_TYPES
        selected_type = st.selectbox(
            "Тип техники", type_options, key=f"m_up_type_select_{count}"
        )

    btn_find_col, btn_reset_col = st.columns(2)
    with btn_find_col:
        trigger_find = st.button(
            "🔍 Найти",
            type="primary",
            use_container_width=True,
            key="m_up_find_action_btn",
        )
    with btn_reset_col:
        has_search = bool(
            st.session_state["m_up_q"]
            or st.session_state["m_up_t"] != "Все"
            or lookup_query
            or selected_type != "Все"
        )
        st.button(
            "🔄 Сбросить",
            disabled=not has_search,
            use_container_width=True,
            key="m_up_reset_action_btn",
            on_click=reset_update_modal_filters,
        )

    if trigger_find:
        st.session_state["m_up_q"] = lookup_query
        st.session_state["m_up_t"] = selected_type

    active_search = st.session_state["m_up_q"]
    active_type = st.session_state["m_up_t"]

    if not active_search and active_type == "Все":
        st.info(
            "Введите бортовой номер или выберите тип техники и нажмите 'Найти'."
        )
        return

    filtered = df_equipment.copy()
    if active_search:
        mask = (
            filtered["eq_board"]
            .astype(str)
            .str.lower()
            .str.contains(active_search, na=False)
        )
        filtered = filtered[mask]
    if active_type != "Все":
        filtered = filtered[filtered["eq_type"] == active_type]

    if filtered.empty:
        st.error("Техника с такими параметрами не найдена.")
        return

    filtered["display_label"] = (
        filtered["eq_board"].astype(str)
        + " | "
        + filtered["eq_type"].astype(str)
        + " | "
        + filtered["eq_model"].astype(str)
    )
    selected_label = st.selectbox(
        "Найдено совпадений. Выберите нужную цель:",
        filtered["display_label"].tolist(),
        key=f"modal_update_target_{count}",
    )

    matched_rows = filtered[filtered["display_label"] == selected_label]
    if matched_rows.empty:
        st.error("Ошибка при выборе машины.")
        return

    # Железно извлекаем первую найденную строку
    current_eq = matched_rows.iloc[0]
    equipment_id = int(current_eq["id"])

    # Читаем тип техники из базы данных для точной синхронизации
    db_type = str(current_eq.get("eq_type", "")).strip()

    # СТРОГОЕ ИСПРАВЛЕНИЕ: Защита списка от сброса на дефолтный Автогрейдер
    local_fleet_types = list(FLEET_TYPES)
    
    # Если в БД лежит старое название, которого больше нет в коде,
    # мы гарантированно добавляем его в локальный список, чтобы не было ошибки длины length
    if db_type and (db_type not in local_fleet_types):
        local_fleet_types.append(db_type)

    # Безопасный расчет индекса: если что-то пойдет не так, индекс железно встанет на 0
    try:
        type_index = local_fleet_types.index(db_type)
    except (ValueError, IndexError):
        type_index = 0

    # Вспомогательная функция очистки вывода для полей ввода формы
    def clean_val(field_name):
        val = current_eq.get(field_name, "")
        if pd.isna(val) or str(val).strip().lower() in ["none", "nan"]:
            return ""
        return str(val).strip()

    # Форма редактирования данных
    with st.form(
        key=f"modal_update_execution_form_{equipment_id}_{count}",
        clear_on_submit=False,
    ):
        col1, col2 = st.columns(2)
        with col1:
            eq_board = st.text_input(
                "Бортовой номер *",
                value=clean_val("eq_board"),
                key=f"m_up_board_{equipment_id}_{count}",
            ).strip()
            eq_type = st.selectbox(
                "Тип",
                local_fleet_types,
                index=int(type_index),
                key=f"m_up_type_{equipment_id}_{count}",
            )
            eq_model = st.text_input(
                "Модель *",
                value=clean_val("eq_model"),
                key=f"m_up_model_{equipment_id}_{count}",
            ).strip()
            eq_serial = st.text_input(
                "Серийный номер",
                value=clean_val("eq_serial"),
                key=f"m_up_serial_{equipment_id}_{count}",
            ).strip()
        with col2:
            eq_year = st.text_input(
                "Год производства",
                value=clean_val("eq_year"),
                key=f"m_up_year_{equipment_id}_{count}",
            ).strip()
            eq_engine = st.text_input(
                "ДВС",
                value=clean_val("eq_engine"),
                key=f"m_up_engine_{equipment_id}_{count}",
            ).strip()
            eq_engine_number = st.text_input(
                "Номер двигателя",
                value=clean_val("eq_engine_number"),
                key=f"m_up_engine_num_{equipment_id}_{count}",
            ).strip()
            eq_code = st.text_input(
                "Код",
                value=clean_val("eq_code"),
                key=f"m_up_code_{equipment_id}_{count}",
            ).strip()

        st.write(" ")
        submitted = st.form_submit_button(
            "Обновить данные", use_container_width=True
        )

        status_placeholder = st.empty()

        if submitted:
            status_placeholder.empty()
            if not eq_board or not eq_model:
                status_placeholder.markdown(
                    '<div class="var-destruct-error">❌ Бортовой номер и Модель обязательны!</div>',
                    unsafe_allow_html=True,
                )
            else:
                is_duplicate = False
                if not df_equipment.empty:
                    match_board = (
                        df_equipment["eq_board"].astype(str).str.lower()
                        == eq_board.lower()
                    )
                    match_model = (
                        df_equipment["eq_model"].astype(str).str.lower()
                        == eq_model.lower()
                    )
                    match_type = (
                        df_equipment["eq_type"].astype(str).str.lower()
                        == eq_type.lower()
                    )
                    duplicate_mask = (
                        match_board
                        & match_model
                        & match_type
                        & (df_equipment["id"].astype(int) != equipment_id)
                    )

                    if duplicate_mask.any():
                        status_placeholder.markdown(
                            f'<div class="self-destruct-error">❌ Ошибка: В базе уже существует точно такая же техника!</div>',
                            unsafe_allow_html=True,
                        )
                        is_duplicate = True

                if not is_duplicate:
                    try:
                        db.update_equipment(
                            equipment_id=equipment_id,
                            eq_board=eq_board,
                            eq_type=eq_type,
                            eq_model=eq_model,
                            eq_serial=eq_serial,
                            eq_year=eq_year,
                            eq_engine=eq_engine,
                            eq_engine_number=eq_engine_number,
                            eq_code=eq_code,
                        )

                        status_placeholder.markdown(
                            '<div class="self-destruct-success">✅ Данные техники успешно обновлены в базе!</div>',
                            unsafe_allow_html=True,
                        )

                        st.session_state["m_up_q"] = ""
                        st.session_state["m_up_t"] = "Все"
                        st.session_state["m_up_reset_counter"] += 1

                        time.sleep(1.2)
                        st.rerun()
                    except Exception as e:
                        status_placeholder.markdown(
                            f'<div class="self-destruct-error">❌ Ошибка: {e}</div>',
                            unsafe_allow_html=True,
                        )


def reset_delete_modal_filters():
    """Сброс фильтров поиска внутри модального окна удаления."""
    st.session_state["m_del_q"] = ""
    st.session_state["m_del_t"] = "Все"
    st.session_state["m_del_reset_counter"] = (
        st.session_state.get("m_del_reset_counter", 0) + 1
    )


@st.dialog("Удаление техники из базы", width="large")
def manual_delete_modal(df_equipment: pd.DataFrame):
    """Окно удаления техники со мгновенным сообщением и авто-обновлением таблицы на фоне."""
    if "m_del_q" not in st.session_state:
        st.session_state["m_del_q"] = ""
    if "m_del_t" not in st.session_state:
        st.session_state["m_del_t"] = "Все"
    if "m_del_reset_counter" not in st.session_state:
        st.session_state["m_del_reset_counter"] = 0

    count = st.session_state["m_del_reset_counter"]

    col_src, col_type = st.columns(2)
    with col_src:
        lookup_query = (
            st.text_input(
                "Бортовой номер техники",
                placeholder="Введите бортовой номер...",
                key=f"m_del_board_input_{count}",
            )
            .strip()
            .lower()
        )
    with col_type:
        type_options = ["Все"] + FLEET_TYPES
        selected_type = st.selectbox(
            "Тип техники", type_options, key=f"m_del_type_select_{count}"
        )

    btn_find_col, btn_reset_col = st.columns(2)
    with btn_find_col:
        trigger_find = st.button(
            "🔍 Найти",
            type="primary",
            use_container_width=True,
            key="m_del_find_action_btn",
        )
    with btn_reset_col:
        has_search = bool(
            st.session_state["m_del_q"]
            or st.session_state["m_del_t"] != "Все"
            or lookup_query
            or selected_type != "Все"
        )
        st.button(
            "🔄 Сбросить",
            disabled=not has_search,
            use_container_width=True,
            key="m_del_reset_action_btn",
            on_click=reset_delete_modal_filters,
        )

    if trigger_find:
        st.session_state["m_del_q"] = lookup_query
        st.session_state["m_del_t"] = selected_type

    active_search = st.session_state["m_del_q"]
    active_type = st.session_state["m_del_t"]

    if not active_search and active_type == "Все":
        st.info(
            "Введите бортовой номер или выберите тип техники и нажмите 'Найти'."
        )
        return

    filtered = df_equipment.copy()
    if active_search:
        mask = (
            filtered["eq_board"]
            .astype(str)
            .str.lower()
            .str.contains(active_search, na=False)
        )
        filtered = filtered[mask]
    if active_type != "Все":
        filtered = filtered[filtered["eq_type"] == active_type]

    if filtered.empty:
        st.error("Техника с такими параметрами не найдена.")
        return

    filtered["display_label"] = (
        filtered["eq_board"].astype(str)
        + " | "
        + filtered["eq_type"].astype(str)
        + " | "
        + filtered["eq_model"].astype(str)
    )
    selected_label = st.selectbox(
        "Выберите точную машину для УДАЛЕНИЯ:",
        filtered["display_label"].tolist(),
        key=f"modal_delete_target_{count}",
    )

    matched_rows = filtered[filtered["display_label"] == selected_label]
    if matched_rows.empty:
        st.error("Ошибка при выборе машины.")
        return

    # Безопасное извлечение первой строки через iloc[0]
    current_eq = matched_rows.iloc[0]
    equipment_id = int(current_eq["id"])

    st.markdown(" ")
    st.markdown(
        f"""
        <div style='background-color: #ffebee; border-left: 5px solid #d32f2f; padding: 12px; margin-bottom: 15px; border-radius: 4px;'>
            <span style='color: #c62828; font-weight: bold;'>⚠️ Внимание!</span> 
            <span style='color: #c62828;'>Вы собираетесь навсегда удалить объект:</span><br>
            <strong>{selected_label}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form(
        f"modal_delete_execution_form_{equipment_id}_{count}",
        clear_on_submit=True,
    ):
        confirm_delete = st.checkbox(
            "Я подтверждаю, что хочу удалить эту единицу из ERP системы"
        )
        submitted = st.form_submit_button(
            "Удалить технику из базы", type="primary", use_container_width=True
        )

        status_placeholder = st.empty()

        if submitted:
            if not confirm_delete:
                status_placeholder.markdown(
                    '<div class="self-destruct-error">❌ Необходимо поставить галочку подтверждения операции!</div>',
                    unsafe_allow_html=True,
                )
            else:
                try:
                    # Вызываем функцию удаления из db_manager
                    db.delete_equipment(equipment_id=equipment_id)

                    # Выводим статус успеха
                    status_placeholder.markdown(
                        '<div class="self-destruct-success">🛑 Единица техники успешно удалена из системы!</div>',
                        unsafe_allow_html=True,
                    )

                    # Сбрасываем фильтры
                    st.session_state["m_del_q"] = ""
                    st.session_state["m_del_t"] = "Все"
                    st.session_state["m_del_reset_counter"] += 1

                    # Микро-таймаут и перезапуск
                    time.sleep(1.2)
                    st.rerun()
                except Exception as e:
                    status_placeholder.markdown(
                        f'<div class="self-destruct-error">❌ Ошибка: {e}</div>',
                        unsafe_allow_html=True,
                    )
           

@st.dialog(":material/add_2: Добавить новую технику в базу", width="large")
def manual_add_modal(df_equipment: pd.DataFrame):
    """Форма добавления техники внутри модального окна с композитной проверкой дубликатов."""

    with st.form("modal_add_equipment_form", clear_on_submit=False):
        st.markdown(
            """
            <style>
            /* Скрывает текст подсказки в самом низу формы */
            .stForm [data-testid="caption"],
            .stForm [data-testid="stCaptionContainer"],
            [data-testid="stFormSubmitButton"] + div,
            form div:last-child {
                display: none !important;
                height: 0px !important;
                margin: 0 !important;
                padding: 0 !important;
                visibility: hidden !important;
                font-size: 0px !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        
        col1, col2 = st.columns(2)

        with col1:
            eq_board = st.text_input(
                "Бортовой номер *", key="add_eq_board"
            ).strip()
            eq_type = st.selectbox("Тип", FLEET_TYPES, key="add_eq_type")
            eq_model = st.text_input("Модель *", key="add_eq_model").strip()
            eq_serial = st.text_input(
                "Серийный номер", key="add_eq_serial"
            ).strip()
        with col2:
            eq_year = st.text_input(
                "Год производства",
                placeholder="например: 2020",
                key="add_eq_year",
            ).strip()
            # ПОРЯДОК ИЗМЕНЕН: ДВС и Номер двигателя подняты вверх, а Код опущен в самый конец
            eq_engine = st.text_input("ДВС", key="add_eq_current_engine").strip()
            eq_engine_number = st.text_input(
                "Номер двигателя", key="add_eq_engine_num"
            ).strip()
            eq_code = st.text_input("Код", key="add_eq_code").strip()

        st.write(" ")
        submitted = st.form_submit_button(
            "Сохранить машину", use_container_width=True
        )
        status_placeholder = st.empty()

        if submitted:
            status_placeholder.empty()

            with status_placeholder.container():
                if not eq_board or not eq_model:
                    status_placeholder.markdown(
                        '<div class="self-destruct-error">❌ Заполните обязательные поля!</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    is_duplicate = False

                    if not df_equipment.empty:
                        # Проверяем ОДНОВРЕМЕННОЕ совпадение Борта, Модели и Типа техники
                        match_board = (
                            df_equipment["eq_board"].astype(str).str.lower()
                            == eq_board.lower()
                        )
                        match_model = (
                            df_equipment["eq_model"].astype(str).str.lower()
                            == eq_model.lower()
                        )
                        match_type = (
                            df_equipment["eq_type"].astype(str).str.lower()
                            == eq_type.lower()
                        )

                        exact_duplicate = match_board & match_model & match_type

                        if exact_duplicate.any():
                            status_placeholder.markdown(
                                f'<div class="self-destruct-error">❌ Ошибка: В базе уже существует **{eq_type}** с бортовым **{eq_board}** и моделью **{eq_model}**!</div>',
                                unsafe_allow_html=True,
                            )
                            is_duplicate = True

                    if not is_duplicate:
                        try:
                            # Передаем аргументы в функцию добавления
                            # Названия аргументов должны строго совпадать с аргументами в db_manager
                            db.add_equipment(
                                eq_board=eq_board,
                                eq_type=eq_type,
                                eq_model=eq_model,
                                eq_serial=eq_serial,
                                eq_year=eq_year,
                                eq_engine=eq_engine,
                                eq_engine_number=eq_engine_number,
                                eq_code=eq_code,
                            )

                            status_placeholder.markdown(
                                '<div class="self-destruct-success">✅ Машина успешно добавлена в базу!</div>',
                                unsafe_allow_html=True,
                            )
                            time.sleep(1.2)
                            st.rerun()

                        except Exception as e:
                            status_placeholder.markdown(
                                f'<div class="self-destruct-error">❌ Ошибка сохранения: {e}</div>',
                                unsafe_allow_html=True,
                            )
                            
                            
# --- ВКЛАДКА ТЕХНИКА ---

def equipment_tab():
    """Отображение вкладки управления техникой"""
    # Загружаем сырые данные из базы данных 
    df_raw = db.load_equipment()
    
    # Выводим панель фильтрации техники
    filtered_data = equipment_filters(df_raw)
    
   
    equipment_table_info(filtered_data)
        

        

        


        
        
def equipment_filters(df_equipment: pd.DataFrame) -> pd.DataFrame:
    """Панель поиска и управления с широким полем ключевых слов на первом месте,

    точечным бортовым номером на втором и без лишних подсказок.
    """


    # Инициализация состояний сессии
    if "submitted_search" not in st.session_state:
        st.session_state["submitted_search"] = ""
    if "submitted_board" not in st.session_state:
        st.session_state["submitted_board"] = ""
    if "submitted_type" not in st.session_state:
        st.session_state["submitted_type"] = "Все"
    if "submitted_model" not in st.session_state:
        st.session_state["submitted_model"] = "Все"
        
    st.write("Поиск по технике")
    
    # РЯД 1: Расширенная первая колонка [2, 1, 1, 1] для идеального баланса ширины полей
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

    with col1:
        # Широкое поле ключевых слов на первом месте, убран placeholder
        search_query = st.text_input(
            "Ключевые слова",
            value=st.session_state["submitted_search"],
            key="filter_search",
        ).strip()

    with col2:
        # Бортовой номер перенесен во вторую колонку, убран placeholder
        board_query = st.text_input(
            "Бортовой номер",
            value=st.session_state["submitted_board"],
            key="filter_board",
        ).strip()

    with col3:
        type_options = ["Все"] + FLEET_TYPES
        try:
            type_idx = type_options.index(st.session_state["submitted_type"])
        except ValueError:
            type_idx = 0
        selected_type = st.selectbox(
            "Тип техники", type_options, index=type_idx, key="filter_type"
        )

    with col4:
        # Предварительная фильтрация базы НА ЛЕТУ для выпадающего списка моделей
        pre_filtered = df_equipment.copy()

        # Сначала по борту
        if board_query:
            pre_filtered = pre_filtered[
                pre_filtered["eq_board"].astype(str).str.lower()
                == board_query.lower()
            ]

        # Затем по ключевым словам
        if search_query:
            q = search_query.lower()
            mask = (
                pre_filtered["eq_model"].astype(str).str.lower().str.contains(q, na=False)
                | pre_filtered["eq_serial"].astype(str).str.lower().str.contains(q, na=False)
                | pre_filtered["eq_engine"].astype(str).str.lower().str.contains(q, na=False)
            )
            pre_filtered = pre_filtered[mask]

        # Затем по типу
        if selected_type != "Все":
            pre_filtered = pre_filtered[pre_filtered["eq_type"] == selected_type]

        # Формируем чистый список уникальных моделей
        available_models = (
            pre_filtered["eq_model"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
        )
        available_models = sorted([m for m in available_models if m != ""])
        model_options = ["Все"] + available_models

        try:
            model_idx = model_options.index(st.session_state["submitted_model"])
        except ValueError:
            model_idx = 0

        selected_model = st.selectbox(
            "Модель техники", model_options, index=model_idx, key="filter_model"
        )

    

    act_col1, act_col2, _, _, _ = st.columns(5)

    with act_col1:
        if st.button(
            ":material/search: Показать",
            type="primary",
            use_container_width=True,
            key="main_search_submit_btn",
        ):
            st.session_state["submitted_search"] = search_query
            st.session_state["submitted_board"] = board_query
            st.session_state["submitted_type"] = selected_type
            st.session_state["submitted_model"] = selected_model
            st.rerun()

    with act_col2:
        has_active_filters = bool(
            st.session_state["submitted_search"]
            or st.session_state["submitted_board"]
            or st.session_state["submitted_type"] != "Все"
            or st.session_state["submitted_model"] != "Все"
        )
        st.button(
            ":material/refresh: Сбросить",
            disabled=not has_active_filters,
            use_container_width=True,
            on_click=clear_search_filters,
            key="main_search_reset_btn",
        )


    

    st.write("Список техники")

    # 3. ИТОГОВАЯ ФИЛЬТРАЦИЯ ДЛЯ ТАБЛИЦЫ
    filtered_df = df_equipment.copy()
    confirm_q = st.session_state["submitted_search"]
    confirm_board = st.session_state["submitted_board"]
    confirm_type = st.session_state["submitted_type"]
    confirm_model = st.session_state["submitted_model"]

    # Точечный поиск по борту
    if confirm_board:
        filtered_df = filtered_df[
            filtered_df["eq_board"].astype(str).str.lower() == confirm_board.lower()
        ]

    # Поиск по ключевым словам по остальным колонкам
    if confirm_q:
        q = confirm_q.strip().lower()
        mask = (
            filtered_df["eq_model"].astype(str).str.lower().str.contains(q, na=False)
            | filtered_df["eq_board"].astype(str).str.lower().str.contains(q, na=False)
            | filtered_df["eq_serial"].astype(str).str.lower().str.contains(q, na=False)
            | filtered_df["eq_year"].astype(str).str.lower().str.contains(q, na=False)
            | filtered_df["eq_engine"].astype(str).str.lower().str.contains(q, na=False)
            | filtered_df["eq_engine_number"].astype(str).str.lower().str.contains(q, na=False)
            | filtered_df["eq_code"].astype(str).str.lower().str.contains(q, na=False)
        )
        filtered_df = filtered_df[mask]

    if confirm_type != "Все":
        filtered_df = filtered_df[filtered_df["eq_type"] == confirm_type]

    if confirm_model != "Все":
        filtered_df = filtered_df[filtered_df["eq_model"] == confirm_model]

    return filtered_df.reset_index(drop=True)


# Global clear callback function
def clear_search_filters():
    """Safely clear input caches in memory before page rendering."""
    # 1. Сбрасываем визуальные состояния виджетов ввода
    st.session_state["filter_search"] = ""
    st.session_state["filter_board"] = ""
    st.session_state["filter_type"] = "Все"
    st.session_state["filter_model"] = "Все"

    # 2. Сбрасываем зафиксированные подтвержденные фильтры
    if "submitted_search" in st.session_state:
        st.session_state["submitted_search"] = ""
    if "submitted_board" in st.session_state:
        st.session_state["submitted_board"] = ""
    if "submitted_type" in st.session_state:
        st.session_state["submitted_type"] = "Все"
    if "submitted_model" in st.session_state:
        st.session_state["submitted_model"] = "Все" 


def equipment_table_info(df_to_display: pd.DataFrame):
    """Отрисовка таблицы техники в режиме чтения без использования data_editor."""
    # Is_admin flag для оптимизации разметки
    
    is_admin = st.session_state.get("role") == "admin"
        # Сетка колонок для кнопок в ряд
    if is_admin:
       act_col1, act_col2, act_col3  = st.columns(3)
    
    # Кнопки управления для Администратора
    if is_admin:
        with act_col1:
            if st.button(
                ":material/add: Добавить",
                use_container_width=True,
                key="panel_add_btn",
            ):
                manual_add_modal(df_to_display)
        with act_col2:
            if st.button(
                ":material/edit: Изменить",
                use_container_width=True,
                key="panel_edit_btn",
            ):
                st.session_state["show_update_success"] = False
                st.session_state["m_up_q"] = ""
                st.session_state["m_up_t"] = "Все"
                st.session_state["m_up_reset_counter"] = (
                    st.session_state.get("m_up_reset_counter", 0) + 1
                )
                manual_update_modal(df_to_display)
        with act_col3:
            if st.button(
                ":material/delete_forever: Удалить",
                use_container_width=True,
                key="panel_delete_btn",
            ):
                st.session_state["m_del_q"] = ""
                st.session_state["m_del_t"] = "Все"
                st.session_state["m_del_reset_counter"] = (
                    st.session_state.get("m_del_reset_counter", 0) + 1
                )
                manual_delete_modal(df_to_display)
            
            st.write("")
    
    
    if df_to_display.empty:
        st.info("Техника с такими параметрами не найдена. Попробуйте изменить фильтры.")
        return
        
    # Настройка отображения колонок (все поля ввода заблокированы для редактирования)
    column_config = {
        "eq_board": st.column_config.TextColumn("Бортовой номер", width=70),
        "eq_type": st.column_config.TextColumn("Тип"),
        "eq_model": st.column_config.TextColumn("Модель"),
        "eq_serial": st.column_config.TextColumn("Серийный номер"),
        "eq_year": st.column_config.TextColumn("Год производства"),
        "eq_engine": st.column_config.TextColumn("ДВС"),
        "eq_engine_number": st.column_config.TextColumn("Номер двигателя"),
        "eq_code": st.column_config.TextColumn("Код"),
    }

    # Display columns (without ID)
    display_columns = ["eq_board", "eq_type", "eq_model", "eq_serial", "eq_year", "eq_engine", "eq_engine_number", "eq_code"]
    
    # Извлекаем только нужные для отображения колонки (без системного ID)
    display_df = df_to_display[display_columns].copy()
    
    # СОРТИРОВКА: по типу техники (по алфавиту) и по бортовому номеру
    display_df = display_df.sort_values(
        by=["eq_type", "eq_board"], 
        ascending=[True, True]
    )
    
    # Рендерим стабильный фрейм данных, который гарантированно не ломает интерфейс
    st.dataframe(
        display_df, 
        column_config=column_config, 
        use_container_width=True,
        hide_index=True,
        height="content"
    )
    
def equipment_table_operational(df_to_display: pd.DataFrame):
    """Отрисовка таблицы техники в режиме чтения без использования data_editor."""
    st.caption("Список техники")
    
    if df_to_display.empty:
        st.info("Техника с такими параметрами не найдена. Попробуйте изменить фильтры.")
        return
        
    # Настройка отображения колонок (все поля ввода заблокированы для редактирования)
    column_config = {
        "eq_board": st.column_config.TextColumn("Бортовой номер", width=70),
        "eq_type": st.column_config.TextColumn("Тип"),
        "eq_model": st.column_config.TextColumn("Модель"),
        "eq_serial": st.column_config.TextColumn("Серийный номер")
    }

    # Display columns (without ID)
    display_columns = ["eq_board", "eq_type", "eq_model", "eq_serial"]
    
    # Извлекаем только нужные для отображения колонки (без системного ID)
    display_df = df_to_display[display_columns].copy()
    
    # СОРТИРОВКА: по типу техники (по алфавиту) и по бортовому номеру
    display_df = display_df.sort_values(
        by=["eq_type", "eq_board"], 
        ascending=[True, True]
    )
    
    # Рендерим стабильный фрейм данных, который гарантированно не ломает интерфейс
    st.dataframe(
        display_df, 
        column_config=column_config, 
        use_container_width=True,
        hide_index=True,
        height="content"
    )

def import_export_tab():
    """Скачивание и загрузка фалой эксель с техникой"""
    # Генерируем пустой xlsx-шаблон в памяти
    blank_eq_file = db.generate_equipment_blank_template()
    
    export_current_date = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    
    # Кнопка скачивания бланка техники
    st.download_button(
        label=":material/download: Скачать Шаблон_Список_техники.xlsx",
        data=blank_eq_file,
        file_name="Шаблон_Список_техники.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True, 
        key="settings_download_eq_template_btn"
    )
    
    # Инициализируем состояние видимости загрузчика, если его еще нет
    if "show_uploader" not in st.session_state:
        st.session_state.show_uploader = False

    # 2. КНОПКА-ПЕРЕКЛЮЧАТЕЛЬ ДЛЯ ИМПОРТА
    if st.button(
        label=":material/upload: Импортировать Список техники (.xlsx)", 
        use_container_width=True,
        key="settings_trigger_upload_btn"
    ):
        # Меняем состояние на противоположное при клике
        st.session_state.show_uploader = not st.session_state.show_uploader

    # Если кнопка была нажата, ровно под ней открывается поле для выбора файла
    if st.session_state.show_uploader:
        uploaded_file = st.file_uploader(
            label="Выберите заполненный файл шаблона:",
            type=["xlsx"],
            accept_multiple_files=False,
            key="settings_upload_eq_file"
        )

        if uploaded_file is not None:
            success, message = db.import_equipment_from_excel(uploaded_file)
            if success:
                st.success(message)
                # Скрываем загрузчик после успешного импорта
                st.session_state.show_uploader = False
                st.rerun()
            else:
                st.error(message)


    # 3. Кнопка экспорта текущей базы данных
    exported_eq_file = db.export_equipment_to_excel()
    st.download_button(
        label=":material/upload_file: Выгрузить список техники (.xlsx)",
        data=exported_eq_file,
        file_name=f"Список_техники_{export_current_date}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key="settings_export_eq_btn",
    )

# --- ВКЛАДКА НАСТРОЙКА ---

def settings_tab():
    """Render settings and authentication tab with document templates."""
    st.write("")
    col1, col2 = st.columns([4, 2]) # Возвращаем ваши исходные пропорции колонок
    
    with col1:    
        import_export_tab()
        
           
    with col2:
        if st.session_state.role == "admin":
            if st.button("Завершить сеанс", type="primary", use_container_width=True):
                st.session_state.role = "guest"
                st.rerun()
        else:
            password = st.text_input(
                "Пароль", 
                # type="password", 
                placeholder="Введите пароль", 
                label_visibility="collapsed",
                width="stretch"
            )
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



# --- ГЛАВНАЯ ФУНКЦИЯ ---

def main():
    """Main application entry point."""
    # Page configuration
    st.set_page_config(page_title="MECHANIK", layout="wide", page_icon=":material/construction:")
    
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